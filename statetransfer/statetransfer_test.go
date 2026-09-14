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
	"testing"
	"time"

	"github.com/hyperledger-labs/mirbft/log"
	pb "github.com/hyperledger-labs/mirbft/protobufs"
)

// Shorten the fetch schedule for the duration of a test.
func shortenFetchSchedule() func() {
	saved := [3]time.Duration{entryFetchInterval, maxEntryFetchDelay, startDelay}
	entryFetchInterval = 1 * time.Millisecond
	maxEntryFetchDelay = 2 * time.Millisecond
	startDelay = 0
	return func() {
		entryFetchInterval, maxEntryFetchDelay, startDelay = saved[0], saved[1], saved[2]
	}
}

func waitFor(t *testing.T, cond func() bool, timeout time.Duration, msg string) {
	t.Helper()
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		if cond() {
			return
		}
		time.Sleep(500 * time.Microsecond)
	}
	t.Fatal(msg)
}

// A fetch with no sources must fail gracefully instead of panicking on sources[0]
// and must not register the SN as in-flight.
func TestFetchMissingEntryNoSources(t *testing.T) {
	defer func() {
		if r := recover(); r != nil {
			t.Errorf("FetchMissingEntry panicked: %v", r)
		}
	}()
	FetchMissingEntry(1, nil)
	fetchMu.Lock()
	_, registered := missingEntries[1]
	fetchMu.Unlock()
	if registered {
		t.Error("SN must not be registered as in-flight without sources")
	}
}

// While a fetch is in flight for an SN, a second fetch for the same SN must be a no-op
// (no second registration, i.e. no goroutine multiplication), and once the running fetch
// gives up, the SN must be released so a later catch-up can restart it.
func TestFetchMissingEntryDedupeAndRelease(t *testing.T) {
	restore := shortenFetchSchedule()
	defer restore()

	// No faster way than letting a real fetch loop exhaust its (few, short) attempts.
	go FetchMissingEntry(42, []int32{0, 1})

	// Wait until the first fetch registers itself.
	waitFor(t, func() bool {
		fetchMu.Lock()
		defer fetchMu.Unlock()
		_, ok := missingEntries[42]
		return ok
	}, 1*time.Second, "first fetch did not register itself")

	// Record the registered entry, then trigger a second (duplicate) fetch.
	fetchMu.Lock()
	first := missingEntries[42]
	fetchMu.Unlock()
	FetchMissingEntry(42, []int32{0, 1})

	// The duplicate must not have replaced the registration.
	fetchMu.Lock()
	_, stillThere := missingEntries[42]
	same := missingEntries[42] == first
	fetchMu.Unlock()
	if !stillThere || !same {
		t.Error("duplicate fetch must reuse the in-flight registration")
	}

	// After the fetch gives up (entry never appears in the log), the SN must be released.
	waitFor(t, func() bool {
		fetchMu.Lock()
		defer fetchMu.Unlock()
		_, ok := missingEntries[42]
		return !ok
	}, 2*time.Second, "in-flight marker was not released after give-up")

	// A fetch after the release may register again (restartability).
	// (Run it in a goroutine, as the catch-up path does — a synchronous call
	// would run the whole fetch loop to exhaustion before returning.)
	go FetchMissingEntry(42, []int32{0})
	waitFor(t, func() bool {
		fetchMu.Lock()
		defer fetchMu.Unlock()
		_, ok := missingEntries[42]
		return ok
	}, 1*time.Second, "fetch after give-up must be able to register again")

	// Quiesce the restarted fetch before the test returns: it reads the backoff knobs
	// (entryFetchInterval etc.) that the next test must rewrite.
	waitFor(t, func() bool {
		fetchMu.Lock()
		defer fetchMu.Unlock()
		_, ok := missingEntries[42]
		return !ok
	}, 2*time.Second, "restarted fetch did not finish")
}

// A response for an SN with no in-flight fetch (already obtained or never requested)
// must be ignored without invoking the orderer handler.
func TestProcessResponseWithoutEntry(t *testing.T) {
	called := false
	savedHandler := OrdererEntryHandler
	OrdererEntryHandler = func(*log.Entry) { called = true }
	defer func() { OrdererEntryHandler = savedHandler }()

	if err := processResponse(&pb.MissingEntry{Sn: 99}); err != nil {
		t.Errorf("unexpected error: %v", err)
	}
	if called {
		t.Error("handler must not be called for a response without in-flight entry")
	}
}

// A valid response for a registered SN deletes the registration and delivers the
// entry to the orderer handler.
func TestProcessResponseWithEntry(t *testing.T) {
	restore := shortenFetchSchedule()
	defer restore()

	received := make(chan *log.Entry, 1)
	savedHandler := OrdererEntryHandler
	OrdererEntryHandler = func(e *log.Entry) { received <- e }
	defer func() { OrdererEntryHandler = savedHandler }()

	// Register as FetchMissingEntry would. (No fetch loop may be running for this SN.)
	fetchMu.Lock()
	missingEntries[77] = &missingEntry{Sn: 77}
	fetchMu.Unlock()

	if err := processResponse(&pb.MissingEntry{Sn: 77, Digest: []byte("d")}); err != nil {
		t.Errorf("unexpected error: %v", err)
	}

	select {
	case e := <-received:
		if e.Sn != 77 {
			t.Errorf("handler received wrong SN: %d", e.Sn)
		}
	case <-time.After(1 * time.Second):
		t.Fatal("handler was not called for a valid response")
	}

	fetchMu.Lock()
	_, stillThere := missingEntries[77]
	fetchMu.Unlock()
	if stillThere {
		t.Error("registration must be deleted on successful response")
	}
}
