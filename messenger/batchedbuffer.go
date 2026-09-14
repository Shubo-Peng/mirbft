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

package messenger

import (
	"sync"

	proto "github.com/golang/protobuf/proto"
	pb "github.com/hyperledger-labs/mirbft/protobufs"
	logger "github.com/rs/zerolog/log"
)

// Hard bounds of the per-connection buffered outbound message queue.
// Variables (not constants) so tests can lower them; production code never changes them.
var (
	// Most protocol messages are a few hundred bytes, but pre-preprepares carry a whole
	// batch (up to a few MB), so a message-count bound alone would allow gigabytes in
	// flight. Byte accounting uses proto.Size(msg), i.e. the marshalled size.
	batchedConnectionMaxBufferedMsgs  = 1024
	batchedConnectionMaxBufferedBytes = 64 << 20 // 64 MiB per peer connection
)

// boundedMsgBuffer accumulates outbound ProtocolMessages between two batch
// transmissions. It is the admission-control point of the BatchedConnection: a
// stalled or slow peer must never translate into unbounded local retention or
// into blocked producers (blocking here would freeze the whole message pump,
// spreading one peer's failure to the entire node).
//
// When a bound would be exceeded, the NEWEST message is dropped (tail drop).
// Protocol traffic is re-requestable (missing-entry requests, view change
// catch-up, periodic retransmission), so shedding new work is safe, while
// dropping the oldest messages would break agreement rounds already in flight.
type boundedMsgBuffer struct {
	mu    sync.Mutex
	msgs  []*pb.ProtocolMessage
	bytes int

	// dropped counts messages shed since the last drain; dropWarned is true
	// once a warning has been logged for the current accumulation window.
	dropped    int
	dropWarned bool
}

func newBoundedMsgBuffer() *boundedMsgBuffer {
	return &boundedMsgBuffer{
		msgs: make([]*pb.ProtocolMessage, 0, 64),
	}
}

// add buffers msg unless a hard bound would be exceeded, in which case the
// message is dropped and counted. Never blocks. Returns whether msg was buffered.
func (b *boundedMsgBuffer) add(msg *pb.ProtocolMessage) bool {
	size := proto.Size(msg)

	b.mu.Lock()
	defer b.mu.Unlock()

	if len(b.msgs) >= batchedConnectionMaxBufferedMsgs || b.bytes+size > batchedConnectionMaxBufferedBytes {
		b.dropped++
		if !b.dropWarned {
			b.dropWarned = true
			logger.Warn().
				Int32("sn", msg.Sn).
				Int("bufferedMsgs", len(b.msgs)).
				Int("bufferedBytes", b.bytes).
				Msg("Batched connection buffer full: dropping message. Further drops in this batch window are counted silently.")
		}
		return false
	}

	b.msgs = append(b.msgs, msg)
	b.bytes += size
	return true
}

// drain returns all messages accumulated so far, resets the buffer, and reports
// how many messages were dropped since the previous drain. The returned slice
// does not share its backing array with the buffer.
func (b *boundedMsgBuffer) drain() ([]*pb.ProtocolMessage, int) {
	b.mu.Lock()
	defer b.mu.Unlock()

	msgs := b.msgs
	dropped := b.dropped
	b.msgs = make([]*pb.ProtocolMessage, 0, cap(msgs))
	b.bytes = 0
	b.dropped = 0
	b.dropWarned = false
	return msgs, dropped
}
