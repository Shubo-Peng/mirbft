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
	"testing"
	"time"

	proto "github.com/golang/protobuf/proto"
	pb "github.com/hyperledger-labs/mirbft/protobufs"
)

// preprepareWithPayload returns a ProtocolMessage whose marshalled size is
// dominated by a payload of size n, mimicking the largest messages this buffer
// carries (full-batch pre-preprepares).
func preprepareWithPayload(n int) *pb.ProtocolMessage {
	return &pb.ProtocolMessage{
		Sn: 1,
		Msg: &pb.ProtocolMessage_Preprepare{Preprepare: &pb.PbftPreprepare{
			Batch: &pb.Batch{Requests: []*pb.ClientRequest{{Payload: make([]byte, n)}}},
		}},
	}
}

// The message-count bound drops the newest message once reached.
func TestBoundedMsgBufferCountBound(t *testing.T) {
	savedMsgs, savedBytes := batchedConnectionMaxBufferedMsgs, batchedConnectionMaxBufferedBytes
	batchedConnectionMaxBufferedMsgs = 4
	batchedConnectionMaxBufferedBytes = 1 << 30 // make the byte bound inert for this test
	defer func() {
		batchedConnectionMaxBufferedMsgs, batchedConnectionMaxBufferedBytes = savedMsgs, savedBytes
	}()

	b := newBoundedMsgBuffer()
	for i := 0; i < 4; i++ {
		if !b.add(&pb.ProtocolMessage{Sn: int32(i + 1)}) {
			t.Fatalf("message %d unexpectedly dropped", i+1)
		}
	}
	if b.add(&pb.ProtocolMessage{Sn: 5}) {
		t.Error("fifth message must exceed the message-count bound and be dropped")
	}

	msgs, dropped := b.drain()
	if len(msgs) != 4 || dropped != 1 {
		t.Errorf("drain() = (%d msgs, %d dropped), want (4, 1)", len(msgs), dropped)
	}
	if msgs[3].Sn != 4 {
		t.Errorf("tail drop must keep the oldest messages in order; last kept Sn = %d, want 4", msgs[3].Sn)
	}
}

// The byte bound drops the newest message once the accumulated marshalled size
// exceeds the budget.
func TestBoundedMsgBufferByteBound(t *testing.T) {
	savedMsgs, savedBytes := batchedConnectionMaxBufferedMsgs, batchedConnectionMaxBufferedBytes
	batchedConnectionMaxBufferedMsgs = 1024 // make the count bound inert for this test
	batchedConnectionMaxBufferedBytes = 1024
	defer func() {
		batchedConnectionMaxBufferedMsgs, batchedConnectionMaxBufferedBytes = savedMsgs, savedBytes
	}()

	payload := 400 // message size ≈ payload + wrapper overhead
	b := newBoundedMsgBuffer()
	msgSize := proto.Size(preprepareWithPayload(payload))

	accepted, total := 0, 0
	for i := 0; i < 16; i++ {
		if b.add(preprepareWithPayload(payload)) {
			accepted++
			total += msgSize
		}
	}

	if accepted*msgSize > 1024 {
		t.Fatalf("total accepted bytes %d exceeds the budget of %d", accepted*msgSize, 1024)
	}
	if accepted == 0 || accepted == 16 {
		t.Fatalf("accepted %d of 16 messages; want a partial acceptance given the byte budget", accepted)
	}

	_, dropped := b.drain()
	if want := 16 - accepted; dropped != want {
		t.Errorf("dropped = %d, want %d", dropped, want)
	}

	// After the drain the budget is reset.
	if !b.add(preprepareWithPayload(payload)) {
		t.Error("buffer must accept messages again after drain")
	}
}

// drain must hand off a slice that is isolated from the buffer's future writes,
// and must reset the drop counter.
func TestBoundedMsgBufferDrainIsolation(t *testing.T) {
	savedMsgs, savedBytes := batchedConnectionMaxBufferedMsgs, batchedConnectionMaxBufferedBytes
	batchedConnectionMaxBufferedMsgs = 1
	batchedConnectionMaxBufferedBytes = 1 << 30
	defer func() {
		batchedConnectionMaxBufferedMsgs, batchedConnectionMaxBufferedBytes = savedMsgs, savedBytes
	}()

	b := newBoundedMsgBuffer()
	b.add(&pb.ProtocolMessage{Sn: 1})
	b.add(&pb.ProtocolMessage{Sn: 2}) // dropped by the count bound

	handoff, dropped := b.drain()
	if dropped != 1 || len(handoff) != 1 || handoff[0].Sn != 1 {
		t.Fatalf("unexpected drain result: msgs=%v dropped=%d", handoff, dropped)
	}

	// Subsequent adds must not affect the handed-off slice's contents.
	b.add(&pb.ProtocolMessage{Sn: 3})
	handoff[0].Sn = 999 // handoff must be a separate backing array; write to it freely
	b.drain()

	if len(handoff) != 1 || handoff[0].Sn != 999 {
		t.Error("drained slice shares backing storage with the live buffer")
	}
}

// fakePeerConnection captures what the BatchedConnection hands to the underlying
// connection.
type fakePeerConnection struct {
	mu   sync.Mutex
	sent []*pb.ProtocolMessage
	prio []*pb.ProtocolMessage
}

func (f *fakePeerConnection) Send(msg *pb.ProtocolMessage) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.sent = append(f.sent, msg)
}

func (f *fakePeerConnection) SendPriority(msg *pb.ProtocolMessage) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.prio = append(f.prio, msg)
}

func (f *fakePeerConnection) Close() {}

func (f *fakePeerConnection) sentCount() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return len(f.sent)
}

// The BatchedConnection must wrap accumulated messages into multi-message
// batches, pass priority messages straight through, and stop sending after Close.
func TestBatchedConnectionBatching(t *testing.T) {
	fake := &fakePeerConnection{}
	bc := NewBatchedConnection(fake, 5*time.Millisecond)

	// Normal messages accumulate into one batch.
	bc.Send(&pb.ProtocolMessage{Sn: 1})
	bc.Send(&pb.ProtocolMessage{Sn: 2})

	waitForSend := func(deadline time.Duration, msg string) {
		t.Helper()
		limit := time.Now().Add(deadline)
		for fake.sentCount() == 0 && time.Now().Before(limit) {
			time.Sleep(time.Millisecond)
		}
		if fake.sentCount() == 0 {
			t.Fatal(msg)
		}
	}
	waitForSend(time.Second, "batch was never transmitted")

	fake.mu.Lock()
	multi, ok := fake.sent[0].Msg.(*pb.ProtocolMessage_Multi)
	fake.mu.Unlock()
	if !ok {
		t.Fatalf("transmitted message is not a multi-message batch: %T", fake.sent[0].Msg)
	}
	if len(multi.Multi.Msgs) != 2 {
		t.Errorf("batch contains %d messages, want 2", len(multi.Multi.Msgs))
	}

	// Priority messages bypass the buffer.
	prioMsg := &pb.ProtocolMessage{Sn: 9}
	bc.SendPriority(prioMsg)
	fake.mu.Lock()
	prioReceived := len(fake.prio) == 1 && fake.prio[0] == prioMsg
	fake.mu.Unlock()
	if !prioReceived {
		t.Error("SendPriority must be passed straight through to the connection")
	}

	// Close stops the sender: no further batches may be transmitted.
	bc.Close()
	fake.mu.Lock()
	before := len(fake.sent)
	fake.mu.Unlock()
	time.Sleep(30 * time.Millisecond)
	fake.mu.Lock()
	after := len(fake.sent)
	fake.mu.Unlock()
	if after != before {
		t.Errorf("sender transmitted %d more batches after Close", after-before)
	}

	// Close is idempotent (must not panic on double close).
	bc.Close()
}
