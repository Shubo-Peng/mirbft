// Copyright 2022 IBM Corp. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package statetransfer

import (
	"fmt"
	"math/rand"
	"sync"
	"time"

	"github.com/hyperledger-labs/mirbft/log"
	"github.com/hyperledger-labs/mirbft/membership"
	"github.com/hyperledger-labs/mirbft/messenger"
	pb "github.com/hyperledger-labs/mirbft/protobufs"
	logger "github.com/rs/zerolog/log"
)

// Defaults of the fetch policy. They are mutable only so tests can shorten the backoff
// schedule; production code never changes them.
var (
	startDelay         = 500 * time.Millisecond
	entryFetchInterval = 500 * time.Millisecond
	maxEntryFetchDelay = 5 * time.Second
	maxFetchAttempts   = 12
)

const (
	receivedEntriesBufferSize = 4096
)

type missingEntry struct {
	Sn int32
}

var (
	OrdererEntryHandler func(*log.Entry) = nil

	// missingEntries is the registry of in-flight fetch loops, guarded by fetchMu.
	// An SN is present exactly while a FetchMissingEntry loop for it is running:
	// it is registered before the first request is sent (so any response that may
	// arrive immediately can always find its entry) and released when the loop exits
	// (entry obtained or attempts exhausted). At most one in-flight loop per SN makes
	// the total number of fetch goroutines bounded by the segment length regardless of
	// how often catch-up is restarted.
	fetchMu         sync.Mutex
	missingEntries  = make(map[int32]*missingEntry)
	receivedEntries = make(chan *pb.MissingEntry, receivedEntriesBufferSize)
)

func Init() {
	go processMissingEntries()
}

func HandleMessage(msg *pb.ProtocolMessage) {
	switch m := msg.Msg.(type) {
	case *pb.ProtocolMessage_MissingEntryReq:
		handleRequest(m.MissingEntryReq, msg.SenderId)
	case *pb.ProtocolMessage_MissingEntry:
		receivedEntries <- m.MissingEntry
	}
}

func CatchUp(checkpoint *pb.StableCheckpoint) {
	// Give the protocol some time to acquire the entries normally.
	time.Sleep(startDelay)

	sources := make([]int32, 0, len(checkpoint.Proof))
	for peerID, _ := range checkpoint.Proof {
		sources = append(sources, peerID)
	}

	// Ask for each missing entry in parallel.
	// (At most one fetch loop per SN will actually run; see FetchMissingEntry.)
	for _, sn := range log.Missing(checkpoint.Sn) {
		go FetchMissingEntry(sn, sources)
	}
}

func FetchMissingEntry(sn int32, sources []int32) {

	if len(sources) == 0 {
		logger.Error().Int32("sn", sn).Msg("Cannot fetch missing entry: no sources.")
		return
	}

	// Register this fetch before sending the first request, so that a response arriving
	// immediately can always find its missingEntries entry (this also resolves the race
	// previously warned about in this file). If a fetch for the same SN is already
	// running, that loop covers the SN and this call is a no-op.
	fetchMu.Lock()
	if _, inFlight := missingEntries[sn]; inFlight {
		fetchMu.Unlock()
		return
	}
	missingEntries[sn] = &missingEntry{Sn: sn}
	fetchMu.Unlock()

	// Release the in-flight marker when this loop exits, regardless of the reason,
	// so that a later catch-up can restart the fetch.
	defer func() {
		fetchMu.Lock()
		delete(missingEntries, sn)
		fetchMu.Unlock()
	}()

	// Create a copy of the list of sources and randomize their order.
	// Seed per call (and per SN) to de-correlate concurrent calls.
	shuffledSources := make([]int32, len(sources), len(sources))
	copy(shuffledSources, sources)
	rand.Seed(time.Now().UnixNano() ^ int64(sn))
	rand.Shuffle(len(shuffledSources), func(i, j int) {
		shuffledSources[i], shuffledSources[j] = shuffledSources[j], shuffledSources[i]
	})

	logger.Info().
		Int32("sn", sn).
		Int("nSources", len(shuffledSources)).
		Int32("firstSource", shuffledSources[0]).
		Msg("Fetching missing entry.")

	// Create new request message
	msg := &pb.ProtocolMessage{
		SenderId: membership.OwnID,
		Sn:       sn,
		Msg: &pb.ProtocolMessage_MissingEntryReq{MissingEntryReq: &pb.MissingEntryRequest{
			Sn:             sn,
			PayloadRequest: true,
		}},
	}

	// Keep sending entry request messages until the entry appears in the log
	// or the bounded number of attempts is exhausted.
	// Delays between attempts follow a capped, jittered exponential backoff, and every
	// attempt asks the next source in the shuffled list. If all attempts fail, this loop
	// gives up and releases the SN, to be restarted by the next catch-up (e.g. at the
	// next view change) — the fetch loop must not become a permanent per-SN goroutine.
	delay := entryFetchInterval
	attempt := 0
	for log.GetEntry(sn) == nil && attempt < maxFetchAttempts {
		source := shuffledSources[attempt%len(shuffledSources)]

		logger.Debug().
			Int32("sn", sn).
			Int32("peerID", source).
			Msg("Requesting missing entry.")

		messenger.EnqueueMsg(msg, source)

		attempt++
		if log.GetEntry(sn) != nil {
			break
		}
		if attempt == maxFetchAttempts {
			break
		}

		// Sleep with capped exponential backoff and +/- 20% jitter to break synchronization
		// between concurrent fetchers.
		jittered := time.Duration(float64(delay) * (0.8 + 0.4*rand.Float64()))
		time.Sleep(jittered)
		if delay < maxEntryFetchDelay {
			delay *= 2
			if delay > maxEntryFetchDelay {
				delay = maxEntryFetchDelay
			}
		}
	}

	if log.GetEntry(sn) == nil {
		logger.Warn().
			Int32("sn", sn).
			Int("attempts", attempt).
			Msg("Giving up fetching missing entry for now; it will be retried on the next catch-up.")
	}
}

// Handles responses to missing entry requests.
// Loop exits when receivedEntries is closed (currently never).
func processMissingEntries() {
	for resp := range receivedEntries {
		if err := processResponse(resp); err != nil {
			logger.Error().Err(err).Int32("sn", resp.Sn).Msg("Invalid response to missing entry request.")
		}
	}
}

func processResponse(resp *pb.MissingEntry) error {

	fetchMu.Lock()
	me, ok := missingEntries[resp.Sn]
	if ok {
		// Clean up to prevent handling duplicate responses.
		// (The def-ranging FetchMissingEntry loop would remove it anyway on exit;
		// removing it here makes the in-flight state accurate immediately.)
		delete(missingEntries, resp.Sn)
	}
	fetchMu.Unlock()

	// If there is no missing entry corresponding to this response, we already obtained one earlier and ignore this one.
	if !ok {
		return nil
	}

	// Verify obtained response with respect to the corresponding checkpoint.
	if err := verifyResponse(resp, me); err != nil {
		return fmt.Errorf("Invalid response to missing entry request: %v", err)
	}

	// Create a new entry object
	entry := &log.Entry{
		Sn:        resp.Sn,
		Batch:     resp.Batch,
		Digest:    resp.Digest,
		Aborted:   resp.Aborted,
		Suspect:   resp.Suspect,
		ProposeTs: 0,
		CommitTs:  time.Now().UnixNano(),
	}

	logger.Info().Int32("sn", entry.Sn).Msg("Fetched missing entry.")

	// Process the new entry through the orderer instead of directly inserting it in the log.
	// This gives protocol executed by the orderer a chance to react to this event.
	OrdererEntryHandler(entry)
	return nil
}

func verifyResponse(resp *pb.MissingEntry, me *missingEntry) error {
	// TODO: This is a STUB. Implement proper checkpoint proofs and verify responses.

	return nil
}

func handleRequest(req *pb.MissingEntryRequest, senderID int32) {

	// In this simple implementation, we send the entry if we have it, otherwise we ignore the request.
	if entry := log.GetEntry(req.Sn); entry != nil {
		msg := &pb.ProtocolMessage{
			SenderId: membership.OwnID,
			Sn:       entry.Sn,
			Msg: &pb.ProtocolMessage_MissingEntry{MissingEntry: &pb.MissingEntry{
				Sn:      entry.Sn,
				Digest:  entry.Digest,
				Aborted: entry.Aborted,
				Suspect: entry.Suspect,
				Proof:   "Dummy Proof", // TODO: Use an actual proof.
			}},
		}

		// Only append batch data if payload is requested
		if req.PayloadRequest {
			msg.Msg.(*pb.ProtocolMessage_MissingEntry).MissingEntry.Batch = entry.Batch
		}

		logger.Info().Int32("sn", req.Sn).Int32("peerID", senderID).Msg("Sending missing entry.")
		messenger.EnqueueMsg(msg, senderID)
	} else {
		logger.Debug().Int32("sn", req.Sn).Int32("peerID", senderID).Msg("Ignoring missing entry request.")
	}
}
