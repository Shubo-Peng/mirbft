package tuner

import (
	"math"
	"math/rand"
)

// simulatedAnnealing performs BatchSize tuning using Simulated Annealing.
type simulatedAnnealing struct {
	minBatchSize int
	maxBatchSize int
	maxIter      int
	iteration    int

	// Temperature schedule
	initialTemp float64
	coolingRate float64

	// Objective weights
	wThroughput float64
	wLatency    float64

	// Current state
	currentBatchSize int
	currentObj       float64
	bestBatchSize    int
	bestObj          float64

	rng *rand.Rand
}

// NewSimulatedAnnealing creates a Simulated Annealing tuner.
func NewSimulatedAnnealing(minBatchSize, maxBatchSize, maxIter int) Tuner {
	return &simulatedAnnealing{
		minBatchSize: minBatchSize,
		maxBatchSize: maxBatchSize,
		maxIter:      maxIter,
		initialTemp:  1000.0,
		coolingRate:  0.9,
		wThroughput:  1.0,
		wLatency:     1.0,
		bestObj:      math.Inf(-1),
		rng:          rand.New(rand.NewSource(123)),
	}
}

func (sa *simulatedAnnealing) Name() string {
	return "sa"
}

func (sa *simulatedAnnealing) Reset() {
	sa.iteration = 0
	sa.currentBatchSize = 0
	sa.currentObj = math.Inf(-1)
	sa.bestBatchSize = 0
	sa.bestObj = math.Inf(-1)
}

// NextBatchSize implements Simulated Annealing to find the optimal BatchSize.
// Uses a deferred-observation model: after observing the result of the previous proposal,
// if the new point is worse than the best known, we roll back to the best and explore from there.
func (sa *simulatedAnnealing) NextBatchSize(observations []Observation) (int, bool) {
	if sa.iteration >= sa.maxIter {
		return 0, false
	}
	sa.iteration++

	// First iteration: random start
	if sa.iteration == 1 {
		sa.currentBatchSize = sa.randomSample()
		return sa.currentBatchSize, true
	}

	// Compute normalization factors from all observations
	maxT, maxL := normFactors(observations)

	// Evaluate the most recent observation (result of our previous proposal)
	if len(observations) > 0 {
		last := observations[len(observations)-1]
		sa.currentObj = sa.objective(last.Throughput, last.Latency, maxT, maxL)

		if sa.currentObj > sa.bestObj {
			// Improvement: accept the new point, update best
			sa.bestObj = sa.currentObj
			sa.bestBatchSize = last.BatchSize
		} else {
			// Worse: roll back to the best known BatchSize
			sa.currentBatchSize = sa.bestBatchSize
		}
	}

	// Generate a neighbor from the current (which may have been rolled back to best)
	neighbor := sa.generateNeighbor(sa.currentBatchSize)
	sa.currentBatchSize = neighbor
	return neighbor, true
}

func (sa *simulatedAnnealing) objective(throughput, latency, maxT, maxL float64) float64 {
	return sa.wThroughput*throughput/maxT - sa.wLatency*latency/maxL
}

// generateNeighbor produces a neighboring BatchSize by adding scaled random perturbation.
// Perturbation scale decreases with temperature.
func (sa *simulatedAnnealing) generateNeighbor(current int) int {
	// Perturbation range proportional to remaining temperature fraction
	tempFraction := math.Pow(sa.coolingRate, float64(sa.iteration-1))
	rangeSize := float64(sa.maxBatchSize-sa.minBatchSize) * tempFraction * 0.3

	if rangeSize < 50 {
		rangeSize = 50
	}

	// Random step within the perturbation range
	delta := (sa.rng.Float64()*2 - 1) * rangeSize
	neighbor := float64(current) + delta
	return clampInt(neighbor, sa.minBatchSize, sa.maxBatchSize)
}

func (sa *simulatedAnnealing) randomSample() int {
	lo := sa.minBatchSize
	hi := sa.maxBatchSize
	return lo + sa.rng.Intn(hi-lo+1)
}
