#!/bin/bash
#
# sync-and-test.sh — Sync code to remote server, build, and run tuning experiments.
#
# Usage:
#   ./sync-and-test.sh [--build-only] [--run-only] [--algorithm bayesian|sa]
#
# Prerequisites:
#   - sshpass must be installed (sudo apt install sshpass)
#   - Password is read from doc/password.txt

set -euo pipefail

# --- Configuration ---
REMOTE_USER="ubuntu"
REMOTE_HOST="10.16.51.191"
REMOTE_PATH="/opt/gopath/src/github.com/hyperledger/mirbft"
PASSWORD_FILE="doc/password.txt"
EXPERIMENT_CONFIG="scripts/experiment-configuration/generate-local-config.sh"

# Tuning parameters (override via command line or environment)
ALGORITHM="${ALGORITHM:-bayesian}"
TUNE_INTERVAL_MS="${TUNE_INTERVAL_MS:-5000}"
WARM_UP_MS="${WARM_UP_MS:-2000}"
BATCH_SIZE_MIN="${BATCH_SIZE_MIN:-100}"
BATCH_SIZE_MAX="${BATCH_SIZE_MAX:-5000}"
TUNE_MAX_ITER="${TUNE_MAX_ITER:-20}"

# --- Parse arguments ---
BUILD_ONLY=false
RUN_ONLY=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --build-only) BUILD_ONLY=true; shift ;;
        --run-only)  RUN_ONLY=true;  shift ;;
        --algorithm) ALGORITHM="$2"; shift 2 ;;
        --tune-interval) TUNE_INTERVAL_MS="$2"; shift 2 ;;
        --max-iter) TUNE_MAX_ITER="$2"; shift 2 ;;
        --batch-min) BATCH_SIZE_MIN="$2"; shift 2 ;;
        --batch-max) BATCH_SIZE_MAX="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# --- Ensure password file exists ---
if [ ! -f "$PASSWORD_FILE" ]; then
    echo "ERROR: Password file not found: $PASSWORD_FILE"
    exit 1
fi
PASSWORD=$(cat "$PASSWORD_FILE")

# --- Helper functions ---
ssh_cmd() {
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        "${REMOTE_USER}@${REMOTE_HOST}" "$@"
}

rsync_cmd() {
    sshpass -p "$PASSWORD" rsync -avz --delete \
        -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
        "$@"
}

# --- Banner ---
echo "============================================"
echo "  mirbft Sync & Test Script"
echo "============================================"
echo "  Remote:  ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"
echo "  Algorithm: ${ALGORITHM}"
echo "  BatchSize range: [${BATCH_SIZE_MIN}, ${BATCH_SIZE_MAX}]"
echo "  Max iterations: ${TUNE_MAX_ITER}"
echo "  Tune interval: ${TUNE_INTERVAL_MS}ms"
echo "============================================"
echo ""

# --- Set up results directory ---
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RUN_NAME="tune-${ALGORITHM}-${TIMESTAMP}"
RESULTS_DIR="./test-results/${RUN_NAME}"
LOG_FILE="${RESULTS_DIR}/run.log"

mkdir -p "${RESULTS_DIR}/experiment-output"

echo "Results will be saved to: ${RESULTS_DIR}"
echo ""

# ===================================================================
# Step 1: Sync code to remote server
# ===================================================================
if ! $RUN_ONLY; then
    echo "[1/4] Syncing code to remote server..."

    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    cd "$SCRIPT_DIR"

    # Exclude patterns to avoid syncing unnecessary files
    rsync_cmd \
        --exclude '.git/' \
        --exclude 'deployment/deployment-data/' \
        --exclude '*.o' \
        --exclude '*.a' \
        --exclude '*.so' \
        --exclude '*.swp' \
        --exclude '*.swo' \
        --exclude '.DS_Store' \
        --exclude '__pycache__/' \
        --exclude '*.pyc' \
        ./ "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/"

    echo "  ✓ Sync complete."
else
    echo "[1/4] Skipping sync (--run-only)."
fi

# ===================================================================
# Step 2: Build on remote server
# ===================================================================
if ! $RUN_ONLY; then
    echo "[2/4] Building on remote server..."

    ssh_cmd "bash -l -c '
        export GO111MODULE=off
        export GOPATH=/opt/gopath
        cd ${REMOTE_PATH}
        go install ./... 2>&1
    '"

    echo "  ✓ Build complete."
else
    echo "[2/4] Skipping build (--run-only)."
fi

if $BUILD_ONLY; then
    echo ""
    echo "Build-only mode. Exiting."
    exit 0
fi

# ===================================================================
# Step 3: Generate experiment config with tuning enabled
# ===================================================================
echo "[3/5] Generating experiment configuration..."

ssh_cmd "bash -l -c '
    export GO111MODULE=off
    export GOPATH=/opt/gopath
    cd ${REMOTE_PATH}/deployment

    # Create a tuning-enabled config from the template
    mkdir -p /tmp/tune-exp/config

    # Generate standard config first
    bash scripts/experiment-configuration/generate-local-config.sh /tmp/tune-exp 2>&1

    # Patch the generated config to enable tuning
    for cfg in /tmp/tune-exp/config/config-*.yml; do
        sed -i \"s/^ExperimentMode:.*/ExperimentMode: true/\" \$cfg
        sed -i \"s/^TunerAlgorithm:.*/TunerAlgorithm: ${ALGORITHM}/\" \$cfg
        sed -i \"s/^TuneIntervalMs:.*/TuneIntervalMs: ${TUNE_INTERVAL_MS}/\" \$cfg
        sed -i \"s/^WarmUpMs:.*/WarmUpMs: ${WARM_UP_MS}/\" \$cfg
        sed -i \"s/^BatchSizeMin:.*/BatchSizeMin: ${BATCH_SIZE_MIN}/\" \$cfg
        sed -i \"s/^BatchSizeMax:.*/BatchSizeMax: ${BATCH_SIZE_MAX}/\" \$cfg
        sed -i \"s/^TuneMaxIter:.*/TuneMaxIter: ${TUNE_MAX_ITER}/\" \$cfg
        sed -i \"s|^TuneOutputDir:.*|TuneOutputDir: /tmp/tune-exp|\" \$cfg
    done

    echo \"Config generated in /tmp/tune-exp\"
    ls -la /tmp/tune-exp/config/
'"

echo "  ✓ Configuration generated."

# ===================================================================
# Step 4: Run the experiment
# ===================================================================
echo "[4/5] Running experiment (log: ${LOG_FILE})..."

# Capture start time
START_TIME=$(date +%s)

# Run the deployment, tee output to both terminal and log file
ssh_cmd "bash -l -c '
    export GO111MODULE=off
    export GOPATH=/opt/gopath
    cd ${REMOTE_PATH}/deployment

    cd /tmp/tune-exp
    bash ${REMOTE_PATH}/deployment/deploy.sh local new ${REMOTE_PATH}/deployment/scripts/experiment-configuration/generate-local-config.sh 2>&1
'" 2>&1 | tee "${LOG_FILE}"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "============================================"
echo "  Experiment Complete"
echo "============================================"
echo "  Duration: ${DURATION}s"
echo "  Log file: ${LOG_FILE}"
echo ""

# ===================================================================
# Step 5: Collect results
# ===================================================================
echo "[5/5] Collecting results..."

# Copy experiment output from remote
sshpass -p "$PASSWORD" rsync -avz \
    -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
    "${REMOTE_USER}@${REMOTE_HOST}:/tmp/tune-exp/experiment-output/" \
    "${RESULTS_DIR}/experiment-output/" 2>&1 || echo "  (No experiment-output directory found)"

# Copy tune CSV files from the experiment working directory
sshpass -p "$PASSWORD" rsync -avz \
    -e "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" \
    "${REMOTE_USER}@${REMOTE_HOST}:/tmp/tune-exp/tune-*.csv" \
    "${RESULTS_DIR}/" 2>&1 || echo "  (No tune CSV files found)"

echo ""
echo "============================================"
echo "  Results Summary"
echo "============================================"
echo "  Run: ${RUN_NAME}"
echo "  Path: ${RESULTS_DIR}/"
echo ""

echo "Directory structure:"
find "${RESULTS_DIR}" -type f | sed "s|${RESULTS_DIR}/|  |" | sort
echo ""

# Show tune CSV contents
shopt -s nullglob
for csv in "$RESULTS_DIR"/tune-*.csv; do
    echo "--- Tuning data: $(basename "$csv") ---"
    column -t -s ',' "$csv"
    echo ""
done

# Show result summary
if [ -f "${RESULTS_DIR}/experiment-output/result-summary.csv" ]; then
    echo "--- Result Summary ---"
    column -t -s ',' "${RESULTS_DIR}/experiment-output/result-summary.csv"
    echo ""
fi

echo ""
echo "============================================"
echo "  Done!"
echo "  Results: ${RESULTS_DIR}/"
echo "  Log:     ${RESULTS_DIR}/run.log"
echo "============================================"
