import matplotlib.pyplot as plt
import numpy as np
import re

num_clients_list = [4, 7, 10]
filepaths_tuning = [f"./tuning-{num_clients}-dyn/state" for num_clients in num_clients_list]
filepaths_default = [f"./default-{num_clients}-dyn/state" for num_clients in num_clients_list]

def process_files(filepath1, filepath2, num_client):
    latency1, latency2 = [], []
    throughput1, throughput2 = [], []
    response1, response2 = [], []
    tot1, tot2 = [], []
    avgL1, avgL2 = [], []
    avgT1, avgT2 = [], []
    resRate1, resRate2 = [], []
    lines = 10000

    for i in range(num_client):
        filename = filepath1 + str(i) + ".txt"
        with open(filename, 'r') as file:
            tmp = 0
            for line in file:
                tmp += 1
            lines = min(lines, tmp)
    for i in range(num_client):
        filename = filepath2 + str(i) + ".txt"
        with open(filename, 'r') as file:
            tmp = 0
            for line in file:
                tmp += 1
            lines = min(lines, tmp)
    print(lines)

    for i in range(num_client):
        filename = filepath1 + str(i) + ".txt"
        with open(filename, 'r') as file:
            j = 0
            for line in file:
                j += 1
                if j > lines: break
                content = re.split(r'[ \t\n]+', line)[1:]
                if len(latency1) < j:
                    if float(content[5]) > 0:
                        latency1.append(float(content[4]) * float(content[5]))
                        tot1.append(1)
                    else:
                        latency1.append(float(content[4]) * float(content[5]))
                        tot1.append(0)
                    throughput1.append(float(content[5]))
                else:
                    if float(content[5]) > 0:
                        tot1[j-1] += 1
                    latency1[j-1] += float(content[4]) * float(content[5])
                    throughput1[j-1] += float(content[5])
        filename = filepath2 + str(i) + ".txt"
        with open(filename, 'r') as file:
            j = 0
            for line in file:
                j += 1
                if j > lines: break
                content = re.split(r'[ \t\n]+', line)[1:]
                if len(latency2) < j:
                    if float(content[5]) > 0:
                        latency2.append(float(content[4]) * float(content[5]))
                        tot2.append(1)
                    else:
                        latency2.append(float(content[4]) * float(content[5]))
                        tot2.append(0)
                    throughput2.append(float(content[5]))
                else:
                    if float(content[5]) > 0:
                        tot2[j-1] += 1
                    latency2[j-1] += float(content[4]) * float(content[5])
                    throughput2[j-1] += float(content[5])

    totalLatency1, totalLatency2 = 0, 0
    for i in range(len(latency1)):
        if tot1[i] > 0:
            response1.append(1)
            totalLatency1 += latency1[i]
            latency1[i] /= throughput1[i]
        else:
            response1.append(0)
            if i == 0: latency1[i] = 2000
            else: latency1[i] = latency1[i-1]
        avgL1.append(np.mean(latency1[max(0,i-60):i]))
        avgT1.append(np.mean(throughput1[max(0,i-60):i]))
        resRate1.append(sum(response1[max(0,i-60):i])/60)
        if tot2[i] > 0:
            response2.append(1)
            totalLatency2 += latency2[i]
            latency2[i] /= throughput2[i]
        else:
            response2.append(0)
            if i == 0: latency2[i] = 2000
            else: latency2[i] = latency2[i-1]
        avgL2.append(np.mean(latency2[max(0,i-60):i]))
        avgT2.append(np.mean(throughput2[max(0,i-60):i]))
        resRate2.append(sum(response2[max(0,i-60):i])/60)
    x = range(len(latency1))[60:]
    avgL1 = avgL1[60:]
    avgT1 = avgT1[60:]
    resRate1 = resRate1[60:]
    avgL2 = avgL2[60:]
    avgT2 = avgT2[60:]
    resRate2 = resRate2[60:]
    return x, avgL1, avgL2, avgT1, avgT2, resRate1, resRate2

title_font = {
    'fontsize': 40,
    'fontweight': 'bold'
}

label_font = {
    'fontsize': 40,
    'fontweight': 'bold'
}

plt.figure(figsize=(22,15))
# plt.title(f'Average Latency over Time', fontdict=title_font)
# plt.xlabel('Time', fontdict=label_font)
grid = plt.GridSpec(3, 1, wspace=0.0, hspace=0.5)

for idx, num_client in enumerate(num_clients_list):
    filepath1 = filepaths_tuning[idx]
    filepath2 = filepaths_default[idx]
    x, avgL1, avgL2, avgT1, avgT2, resRate1, resRate2 = process_files(filepath1, filepath2, num_client)

    plt.subplot(grid[idx, 0])
    plt.plot(x, resRate1, marker='.', linestyle='-', color='r', label='PPO')
    plt.plot(x, resRate2, marker='.', linestyle='-', color='b', label='default')
    plt.title(f' Number of nodes: {num_client}', fontdict=title_font)
    if idx == 2:
        plt.xlabel('Time', fontdict=label_font)
    if idx == 1:
        plt.ylabel('Response Rate', fontdict=label_font)
    # plt.ylim(0,2300)
    # plt.ylim(600, 1100)
    plt.ylim(0,1)
    plt.grid(True)
    ax = plt.gca()
    ax.xaxis.set_tick_params(labelsize=30)
    ax.yaxis.set_tick_params(labelsize=30)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight('bold')

plt.figlegend(['PPO', 'default'], loc='upper right', fontsize='xx-large')
plt.savefig('pef-resRate.eps', format='eps', dpi=1000)
plt.show()
