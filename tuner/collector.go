package tuner

import (
	"time"

	"github.com/hyperledger-labs/mirbft/config"
)

// Collector gathers throughput and latency from the running system.
type Collector interface {
	// Collect returns the current throughput (req/s) and average latency (ms).
	Collect() (throughput float64, latency float64)

	// Reset resets internal counters. Call after each Collect to prepare for the next interval.
	Reset()
}

// DefaultCollector reads from config.CommittedRequests and config.TotalDelay.
type DefaultCollector struct {
	lastCommitted int64
	lastDelay     int64
	lastTime      int64 // nanosecond timestamp of last Reset
}

func NewDefaultCollector() *DefaultCollector {
	return &DefaultCollector{
		lastCommitted: config.CommittedRequests,
		lastDelay:     config.TotalDelay,
		lastTime:      time.Now().UnixNano(),
	}
}

func (c *DefaultCollector) Collect() (float64, float64) {
	now := time.Now().UnixNano()
	committed := config.CommittedRequests
	delay := config.TotalDelay

	deltaRequests := committed - c.lastCommitted
	deltaDelay := delay - c.lastDelay
	elapsedSec := float64(now-c.lastTime) / 1e9

	throughput := 0.0
	if elapsedSec > 0 {
		throughput = float64(deltaRequests) / elapsedSec
	}

	latency := 0.0
	if deltaRequests > 0 {
		// TotalDelay is in nanoseconds, convert to milliseconds
		latency = float64(deltaDelay) / 1e6 / float64(deltaRequests)
	}

	return throughput, latency
}

func (c *DefaultCollector) Reset() {
	c.lastCommitted = config.CommittedRequests
	c.lastDelay = config.TotalDelay
	c.lastTime = time.Now().UnixNano()
}
