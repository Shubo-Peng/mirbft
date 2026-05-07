import matplotlib.pyplot as plt
import numpy as np
import re

latency = []
throughput = []
response = []
tot = []
avgL = []
avgT = []
resRate = []
lines = 600

num_client = 4

filepath = "../state"

for i in range(num_client):
    filename = filepath + str(i) + ".txt"
    with open(filename, 'r') as file:
        tmp = 0
        for line in file:
            tmp += 1
        lines = min(lines, tmp)
print(lines)

for i in range(num_client):
    filename = filepath + str(i) + ".txt"
    with open(filename, 'r') as file:
        j = 0
        for line in file:
            j += 1
            if j > lines: break
            content = re.split(r'[ \t\n]+', line)[1:]
            # print(content)
            if len(latency) < j:
                if int(content[0]) > 0:
                    latency.append(int(content[0]) * int(content[1]))
                    tot.append(1)
                else:
                    # latency.append(0)
                    latency.append(int(content[0]) * int(content[1]))
                    tot.append(0)
                throughput.append(int(content[0]))
            else:
                if int(content[0]) > 0:
                    tot[j-1] += 1
                latency[j-1] += int(content[1]) * int(content[0])
                throughput[j-1] += int(content[0])

totalLatency = 0
for i in range(len(latency)):
    if tot[i] > 0:
        response.append(1)
        totalLatency += latency[i]
        latency[i] /= throughput[i]
    else:
        response.append(0)
        # if i == 0: latency[i] = 2000
        # else: latency[i] = latency[i-1]
        # latency[i] = latency[i-1]
    # latency[i] += (num_client-tot[i]) * 1000
    avgT.append(np.mean(throughput[max(0,i-60):i]))
    resRate.append(sum(response[max(0,i-60):i])/60)
for i in range(len(latency)):
    tmpL, tmpT = 0, 0
    for j in range(max(i-59,0), i+1):
        tmpL += latency[j] * throughput[j]
        tmpT += throughput[j]
    avgL.append(tmpL/tmpT)
print(totalLatency/sum(throughput), totalLatency, sum(throughput))
print(sum(throughput)/lines)
print(sum(response)/lines)

x = range(len(latency))[60:]
avgL = avgL[60:]
avgT = avgT[60:]
resRate = resRate[60:]
latency = latency[60:]
throughput = throughput[60:]

title_font = {
    'fontsize': 20,
    'fontweight': 'bold'
}

label_font = {
    'fontsize': 18,
    'fontweight': 'bold'
}

plt.figure(figsize=(22,15))
grid = plt.GridSpec(3, 1, wspace = 0.2, hspace = 0.5)

# plt.subplot(grid[0, 0])
# plt.plot(x, latency, marker='o', linestyle='-', color='b')
# plt.title('Latency', fontdict=title_font)
# plt.xlabel('Time', fontdict=label_font)
# plt.ylabel('Value', fontdict=label_font)
# plt.grid(True)
# plt.legend()

plt.subplot(grid[0, 0])
plt.plot(x, avgL, marker='^', linestyle='-', color='r')
plt.title('Average Latency', fontdict=title_font)
plt.xlabel('Time', fontdict=label_font)
plt.ylabel('Value', fontdict=label_font)
# plt.ylim(100,800)
plt.grid(True)
plt.legend()
ax = plt.gca()  # 获取当前轴
ax.xaxis.set_tick_params(labelsize=14)  # 设置X轴刻度大小
ax.yaxis.set_tick_params(labelsize=14)  # 设置Y轴刻度大小
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontweight('bold')  # 设置字体为加粗


# plt.subplot(grid[1, 0])
# plt.plot(x, throughput, marker='o', linestyle='-', color='b')
# plt.title('throughput', fontdict=title_font)
# plt.xlabel('Time', fontdict=label_font)
# plt.ylabel('Value', fontdict=label_font)
# plt.grid(True)
# plt.legend()

plt.subplot(grid[1, 0])
plt.plot(x, avgT, marker='^', linestyle='-', color='r')
plt.title('Average throughput', fontdict=title_font)
plt.xlabel('Time', fontdict=label_font)
plt.ylabel('Value', fontdict=label_font)
plt.ylim(0,5100)
plt.grid(True)
plt.legend()
ax = plt.gca()  # 获取当前轴
ax.xaxis.set_tick_params(labelsize=14)  # 设置X轴刻度大小
ax.yaxis.set_tick_params(labelsize=14)  # 设置Y轴刻度大小
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontweight('bold')  # 设置字体为加粗

plt.subplot(grid[2,0])
plt.plot(x, resRate, marker='.', linestyle='-', color='r')
plt.title('resRate', fontdict=title_font)
plt.xlabel('Time', fontdict=label_font)
plt.ylabel('Value', fontdict=label_font)
plt.ylim(0, 1)
plt.grid(True)
plt.legend()
ax = plt.gca()  # 获取当前轴
ax.xaxis.set_tick_params(labelsize=14)  # 设置X轴刻度大小
ax.yaxis.set_tick_params(labelsize=14)  # 设置Y轴刻度大小
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontweight('bold')  # 设置字体为加粗

plt.savefig('pef.eps', format='eps', dpi=1000)

# 展示图形
plt.show()