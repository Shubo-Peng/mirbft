import numpy as np
import matplotlib.pyplot as plt

def read_data(filename):
    throughput = []
    latency = []
    with open(filename, 'r') as file:
        for line in file:
            data = line.split()
            throughput.append(float(data[0]))
            latency.append(float(data[1]))
    return throughput, latency

def process_data(throughput, latency, group_size=30):
    avg_throughput = []
    avg_latency = []
    for i in range(0, len(throughput), group_size):
        avg_throughput.append(np.mean(throughput[i:i+group_size]))
        avg_latency.append(np.mean(latency[i:i+group_size]))
    return avg_throughput, avg_latency

def plot_graph(throughput, latency):
    fig, ax1 = plt.subplots(figsize=(12, 6))  # Adjusted figure size

    # Calculate x values for the middle of each interval
    x = np.arange(15, len(throughput) * 30, 30)
    
    ax1.set_xlabel('Number of Data Points')
    ax1.set_ylabel('Throughput')
    line1, = ax1.plot(x, throughput, color='tab:green', marker='o', label='Throughput')
    ax1.tick_params(axis='y')

    # Set x-axis ticks to start from 0
    ax1.set_xticks(np.arange(0, (len(throughput) + 1) * 30, 30))
    ax1.set_xticklabels(np.arange(0, (len(throughput) + 1) * 30, 30))
    ax1.set_xlim(0, max(x) + 15)  # Extend x-axis to show full last interval

    # Set y-axis to not start from 0
    ax1.set_ylim(min(throughput) * 0.9, max(throughput) * 1.1)

    ax2 = ax1.twinx()
    ax2.set_ylabel('Latency')
    line2, = ax2.plot(x, latency, color='tab:blue', marker='s', label='Latency')
    ax2.tick_params(axis='y')

    # Set y-axis to not start from 0
    ax2.set_ylim(min(latency) * 0.9, max(latency) * 1.1)

    # Add title
    title = plt.title('Throughput and Latency Over Time', pad=20)

    # Move legend to the right of the title
    legend = plt.legend([line1, line2], ['Throughput', 'Latency'], 
               loc='center left', bbox_to_anchor=(1, 1.15), ncol=2)

    plt.tight_layout()  # Adjust layout to accommodate the legend
    
    # Save the figure
    plt.savefig('throughput_latency_graph.png', dpi=300, bbox_inches='tight')
    print("Graph saved as 'throughput_latency_graph.png' in the current directory.")
    
    plt.show()

def main():
    filename = 'metrics.txt'
    throughput, latency = read_data(filename)
    avg_throughput, avg_latency = process_data(throughput, latency)
    plot_graph(avg_throughput, avg_latency)

if __name__ == "__main__":
    main()