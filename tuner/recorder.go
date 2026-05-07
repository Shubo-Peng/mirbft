package tuner

import (
	"fmt"
	"os"
)

// Recorder persists tuning observations for post-hoc analysis.
type Recorder struct {
	filepath string
	file     *os.File
	header   bool
}

// NewRecorder creates a recorder that writes CSV to filepath.
func NewRecorder(filepath string) (*Recorder, error) {
	f, err := os.Create(filepath)
	if err != nil {
		return nil, fmt.Errorf("cannot create recorder file %s: %w", filepath, err)
	}
	return &Recorder{filepath: filepath, file: f}, nil
}

// Record writes a single observation as a CSV row.
func (r *Recorder) Record(obs Observation) error {
	if !r.header {
		r.file.WriteString("batch_size,throughput,latency,timestamp\n")
		r.header = true
	}
	_, err := fmt.Fprintf(r.file, "%d,%.2f,%.4f,%d\n",
		obs.BatchSize, obs.Throughput, obs.Latency, obs.Timestamp)
	return err
}

// Close flushes and closes the file.
func (r *Recorder) Close() error {
	return r.file.Close()
}
