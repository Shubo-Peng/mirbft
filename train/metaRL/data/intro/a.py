import sys
import pandas as pd
import numpy as np
import random

def generate_data(A, B, batchsize, n=120, max_attempts=1000):
    Δ = A / 10
    narrow_range = (B - batchsize / 10, B + batchsize / 10)
    wide_range = (B - batchsize, B + batchsize)

    narrow_count = int(n * 0.95)
    wide_count = n - narrow_count

    for attempt in range(max_attempts):
        # latency: 全部在 [A - Δ, A + Δ]
        latency_vals = np.random.uniform(A - Δ, A + Δ, n)

        # throughput: 95% 窄范围，5% 广范围（不重复）
        narrow_vals = np.random.uniform(*narrow_range, narrow_count)
        wide_vals = []

        while len(wide_vals) < wide_count:
            val = np.random.uniform(*wide_range)
            if val < narrow_range[0] or val > narrow_range[1]:
                wide_vals.append(val)

        throughput_vals = np.concatenate([narrow_vals, wide_vals])
        np.random.shuffle(throughput_vals)
        throughput_vals = [int(round(x)) for x in throughput_vals]

        avg_latency = np.mean(latency_vals)
        avg_throughput = np.mean(throughput_vals)

        if 0.95 * A <= avg_latency <= 1.05 * A and 0.95 * B <= avg_throughput <= 1.05 * B:
            return list(zip(latency_vals, throughput_vals))

    raise ValueError(f"Failed to generate valid data after {max_attempts} attempts.")

def main(csv_path, output_path):
    df = pd.read_csv(csv_path)
    target_values = [30000, 40000, 60000]
    all_data = []

    for target in target_values:
        matched_rows = df[df["target-throughput"] == target]
        if matched_rows.empty:
            print(f"[Warning] No data found for target-throughput = {target}")
            continue

        row = matched_rows.iloc[-1]
        A = row["latency-avg-trunc"]
        B = row["throughput-trunc"]
        batchsize = row["batchsize"]

        print(f"Generating data for target-throughput {target}...")
        samples = generate_data(A, B, batchsize)
        all_data.extend(samples)

    with open(output_path, "w") as f:
        for latency, throughput in all_data:
            f.write(f"{throughput}\n")

    print(f"Generated {len(all_data)} rows to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python a.py data.csv data.txt")
        sys.exit(1)

    csv_path = sys.argv[1]
    output_path = sys.argv[2]
    main(csv_path, output_path)
