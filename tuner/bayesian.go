package tuner

import (
	"math"
	"math/rand"
	"sort"
)

// bayesianOptimizer performs BatchSize tuning using Gaussian Process-based Bayesian Optimization.
type bayesianOptimizer struct {
	minBatchSize int
	maxBatchSize int
	maxIter      int
	iteration    int
	bestY        float64
	bestX        float64

	// Objective weights: objective = wThroughput*throughput - wLatency*latency
	wThroughput float64
	wLatency    float64

	lengthScale float64
	noiseVar    float64
	rng         *rand.Rand
}

// NewBayesianOptimizer creates a Bayesian Optimizer with the given bounds and settings.
func NewBayesianOptimizer(minBatchSize, maxBatchSize, maxIter int) Tuner {
	return &bayesianOptimizer{
		minBatchSize: minBatchSize,
		maxBatchSize: maxBatchSize,
		maxIter:      maxIter,
		wThroughput:  1.0,
		wLatency:     1.0,
		lengthScale:  500.0,
		noiseVar:     1e-3,
		rng:          rand.New(rand.NewSource(42)),
	}
}

func (bo *bayesianOptimizer) Name() string {
	return "bayesian"
}

func (bo *bayesianOptimizer) Reset() {
	bo.iteration = 0
	bo.bestY = math.Inf(-1)
	bo.bestX = 0
}

// NextBatchSize returns the next BatchSize to explore using Bayesian Optimization.
// Uses Gaussian Process regression with RBF kernel and Expected Improvement acquisition.
func (bo *bayesianOptimizer) NextBatchSize(observations []Observation) (int, bool) {
	if bo.iteration >= bo.maxIter {
		return 0, false
	}
	bo.iteration++

	// Compute normalization factors from all observations
	maxT, maxL := normFactors(observations)

	// Initial exploration: random samples for the first 3 iterations
	if len(observations) < 3 {
		bo.bestY = math.Inf(-1)
		bo.bestX = 0
		for _, o := range observations {
			obj := bo.objective(o.Throughput, o.Latency, maxT, maxL)
			if obj > bo.bestY {
				bo.bestY = obj
				bo.bestX = float64(o.BatchSize)
			}
		}
		return bo.randomSample(), true
	}

	// Build training data
	n := len(observations)
	X := make([]float64, n)
	Y := make([]float64, n)
	for i, o := range observations {
		X[i] = float64(o.BatchSize)
		Y[i] = bo.objective(o.Throughput, o.Latency, maxT, maxL)
		if Y[i] > bo.bestY {
			bo.bestY = Y[i]
			bo.bestX = X[i]
		}
	}

	// GP hyperparameters
	length := bo.lengthScale
	sigmaN2 := bo.noiseVar
	sigmaF2 := variance(Y)

	if sigmaF2 < 1e-6 {
		sigmaF2 = 1.0
	}

	// Build kernel matrix K + sigma_n^2 * I
	K := make([]float64, n*n)
	for i := 0; i < n; i++ {
		for j := 0; j < n; j++ {
			K[i*n+j] = sigmaF2 * rbfKernel(X[i], X[j], length)
			if i == j {
				K[i*n+j] += sigmaN2
			}
		}
	}

	// Cholesky decomposition: K = L * L^T
	L := cholesky(K, n)

	// Solve for alpha: L * L^T * alpha = Y
	alpha := solveCholesky(L, Y, n)

	// Find the BatchSize that maximizes Expected Improvement
	candidates := bo.generateCandidates(X)
	bestEI := math.Inf(-1)
	bestNext := float64(bo.randomSample())

	for _, xStar := range candidates {
		ei := expectedImprovement(xStar, X, Y, L, alpha, bo.bestY, length, sigmaF2, n)
		if ei > bestEI {
			bestEI = ei
			bestNext = xStar
		}
	}

	// Clamp and convert to int
	next := clampInt(bestNext, bo.minBatchSize, bo.maxBatchSize)
	return next, true
}

// objective computes the normalized scalar objective from throughput and latency.
func (bo *bayesianOptimizer) objective(throughput, latency, maxT, maxL float64) float64 {
	return bo.wThroughput*throughput/maxT - bo.wLatency*latency/maxL
}

// normFactors extracts normalization factors from observations.
func normFactors(observations []Observation) (maxT, maxL float64) {
	maxT, maxL = 1.0, 1.0
	for _, o := range observations {
		if o.Throughput > maxT {
			maxT = o.Throughput
		}
		if o.Latency > maxL {
			maxL = o.Latency
		}
	}
	return maxT, maxL
}

// randomSample returns a random BatchSize within bounds.
func (bo *bayesianOptimizer) randomSample() int {
	lo := bo.minBatchSize
	hi := bo.maxBatchSize
	return lo + bo.rng.Intn(hi-lo+1)
}

// generateCandidates produces candidate points for EI optimization.
// Uses a mix of random candidates and grid points.
func (bo *bayesianOptimizer) generateCandidates(X []float64) []float64 {
	nCandidates := 500
	candidates := make([]float64, 0, nCandidates)

	// Grid-based candidates
	step := float64(bo.maxBatchSize-bo.minBatchSize) / 99.0
	for i := 0; i < 100; i++ {
		candidates = append(candidates, float64(bo.minBatchSize)+float64(i)*step)
	}

	// Random candidates
	nRandom := nCandidates - 100
	for i := 0; i < nRandom; i++ {
		c := float64(bo.randomSample())
		// Also interpolate between current observations for denser sampling
		sort.Float64s(X)
		if len(X) >= 2 {
			idx := bo.rng.Intn(len(X) - 1)
			c = X[idx] + bo.rng.Float64()*(X[idx+1]-X[idx])
		}
		c = clamp(c, float64(bo.minBatchSize), float64(bo.maxBatchSize))
		candidates = append(candidates, c)
	}

	return candidates
}

// --- Gaussian Process Kernels & Prediction ---

// rbfKernel computes the Radial Basis Function (squared exponential) kernel.
func rbfKernel(x1, x2, length float64) float64 {
	d := (x1 - x2) / length
	return math.Exp(-0.5 * d * d)
}

func variance(values []float64) float64 {
	if len(values) < 2 {
		return 1.0
	}
	mean := 0.0
	for _, v := range values {
		mean += v
	}
	mean /= float64(len(values))
	v := 0.0
	for _, val := range values {
		d := val - mean
		v += d * d
	}
	return v / float64(len(values)-1)
}

// expectedImprovement computes EI(x*) = (y_best - mu*) * Phi(Z) + sigma* * phi(Z).
func expectedImprovement(xStar float64, X, Y, L, alpha []float64, yBest, length, sigmaF2 float64, n int) float64 {
	mu, sigma2 := gpPredict(xStar, X, L, alpha, length, sigmaF2, n)
	sigma := math.Sqrt(math.Max(sigma2, 0))

	diff := yBest - mu
	if sigma < 1e-9 {
		if diff > 0 {
			return diff
		}
		return 0
	}

	Z := diff / sigma
	ei := diff*cdfNorm(Z) + sigma*pdfNorm(Z)
	return ei
}

// gpPredict computes the GP posterior mean and variance at xStar.
func gpPredict(xStar float64, X, L, alpha []float64, length, sigmaF2 float64, n int) (float64, float64) {
	// Compute K* (kernel between training points and xStar)
	kStar := make([]float64, n)
	for i := 0; i < n; i++ {
		kStar[i] = sigmaF2 * rbfKernel(X[i], xStar, length)
	}

	// Mean: mu* = K*^T * alpha
	mu := 0.0
	for i := 0; i < n; i++ {
		mu += kStar[i] * alpha[i]
	}

	// Variance: sigma*^2 = K** - v^T * v,  where v = L^{-1} * K*
	v := forwardSubstitution(L, kStar, n)

	vTv := 0.0
	for i := 0; i < n; i++ {
		vTv += v[i] * v[i]
	}

	kStarStar := sigmaF2 // RBF(x*, x*) = 1, so K** = sigmaF2
	sigma2 := kStarStar - vTv

	return mu, sigma2
}

// --- Linear Algebra (Cholesky decomposition, forward/back substitution) ---

// cholesky performs in-place Cholesky decomposition of an n×n positive definite matrix A.
// Returns the lower triangular matrix L such that A = L * L^T.
// Fatal if the matrix is not positive definite; falls back to adding jitter.
func cholesky(A []float64, n int) []float64 {
	L := make([]float64, n*n)
	copy(L, A)

	for attempt := 0; attempt < 10; attempt++ {
		ok := true
		for j := 0; j < n; j++ {
			// Diagonal element
			sum := 0.0
			for k := 0; k < j; k++ {
				sum += L[j*n+k] * L[j*n+k]
			}
			diag := L[j*n+j] - sum
			if diag <= 0 {
				ok = false
			}
			L[j*n+j] = math.Sqrt(math.Max(diag, 0))

			// Off-diagonal elements
			for i := j + 1; i < n; i++ {
				sum = 0.0
				for k := 0; k < j; k++ {
					sum += L[i*n+k] * L[j*n+k]
				}
				if ok {
					L[i*n+j] = (L[i*n+j] - sum) / L[j*n+j]
				}
			}
		}

		if ok {
			return L
		}

		// Add jitter and retry
		copy(L, A)
		jitter := 1e-4 * math.Pow(10, float64(attempt))
		for i := 0; i < n; i++ {
			L[i*n+i] += jitter
		}
	}

	return L
}

// solveCholesky solves L * L^T * x = b for x, given the lower triangular L.
func solveCholesky(L []float64, b []float64, n int) []float64 {
	// Forward solve: L * y = b
	y := forwardSubstitution(L, b, n)
	// Backward solve: L^T * x = y
	return backSubstitution(L, y, n)
}

// forwardSubstitution solves L * x = b where L is lower triangular.
func forwardSubstitution(L []float64, b []float64, n int) []float64 {
	x := make([]float64, n)
	for i := 0; i < n; i++ {
		sum := 0.0
		for j := 0; j < i; j++ {
			sum += L[i*n+j] * x[j]
		}
		x[i] = (b[i] - sum) / L[i*n+i]
	}
	return x
}

// backSubstitution solves U * x = b where U = L^T (upper triangular).
func backSubstitution(L []float64, b []float64, n int) []float64 {
	x := make([]float64, n)
	for i := n - 1; i >= 0; i-- {
		sum := 0.0
		for j := i + 1; j < n; j++ {
			sum += L[j*n+i] * x[j] // L^T[i,j] = L[j,i]
		}
		x[i] = (b[i] - sum) / L[i*n+i]
	}
	return x
}

// --- Probability Distributions ---

// pdfNorm computes the standard normal probability density function.
func pdfNorm(x float64) float64 {
	return math.Exp(-0.5*x*x) / math.Sqrt(2.0*math.Pi)
}

// cdfNorm computes the standard normal cumulative distribution function.
// Uses the error function: Phi(x) = 0.5 * (1 + erf(x / sqrt(2))).
func cdfNorm(x float64) float64 {
	return 0.5 * (1.0 + math.Erf(x/math.Sqrt2))
}

// --- Utility Functions ---

func clamp(x, lo, hi float64) float64 {
	if x < lo {
		return lo
	}
	if x > hi {
		return hi
	}
	return x
}

func clampInt(x float64, lo, hi int) int {
	xi := int(math.Round(x))
	if xi < lo {
		return lo
	}
	if xi > hi {
		return hi
	}
	return xi
}
