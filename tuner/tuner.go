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

package tuner

// Observation records the system metrics for a given BatchSize configuration.
type Observation struct {
	BatchSize  int
	Throughput float64
	Latency    float64
	Timestamp  int64
}

// Tuner is the abstract interface for parameter tuning algorithms.
type Tuner interface {
	// NextBatchSize returns the next BatchSize to explore, given all observations so far.
	// Returns (0, false) when the tuning process has finished.
	NextBatchSize(observations []Observation) (int, bool)

	// Name returns the algorithm name.
	Name() string

	// Reset resets internal state for a fresh tuning run.
	Reset()
}

// NewTuner creates a Tuner by name. Supported: "bayesian", "sa".
func NewTuner(name string, minBatchSize, maxBatchSize, maxIter int) Tuner {
	if minBatchSize <= 0 {
		minBatchSize = 100
	}
	if maxBatchSize <= 0 {
		maxBatchSize = 5000
	}
	if maxIter <= 0 {
		maxIter = 20
	}
	switch name {
	case "bayesian":
		return NewBayesianOptimizer(minBatchSize, maxBatchSize, maxIter)
	case "sa":
		return NewSimulatedAnnealing(minBatchSize, maxBatchSize, maxIter)
	default:
		return NewBayesianOptimizer(minBatchSize, maxBatchSize, maxIter)
	}
}
