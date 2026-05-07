import matplotlib.pyplot as plt
import numpy as np
import re

requests = []
Rsizes = []
response = []
tot = []
avgL = []
avgT = []
resRate = []
lines = 1700

num_client = 4

filepath = "./pure RL/state"

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
            if len(requests) < j:
                if int(content[2]) > 0:
                    requests.append(int(content[2]))
                    tot.append(1)
                else:
                    # requests.append(0)
                    requests.append(int(content[2]))
                    tot.append(0)
                Rsizes.append(int(content[3])/1000)
            else:
                if int(content[0]) > 0:
                    tot[j-1] += 1
                requests[j-1] += int(content[2])
                Rsizes[j-1] += int(content[3])/1000

totalLatency = 0
for i in range(len(requests)):
    avgL.append(np.mean(requests[max(0,i-60):i]))
    avgT.append(np.mean(Rsizes[max(0,i-60):i]))
    resRate.append(sum(response[max(0,i-60):i])/60)
print(totalLatency/sum(Rsizes))
print(sum(Rsizes)/lines)
print(sum(response)/lines)

x = range(len(requests))[60:]
avgL = avgL[60:]
avgT = avgT[60:]
resRate = resRate[60:]
requests = requests[60:]
Rsizes = Rsizes[60:]

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
# plt.plot(x, requests, marker='o', linestyle='-', color='b')
# plt.title('requests', fontdict=title_font)
# plt.xlabel('Time', fontdict=label_font)
# plt.ylabel('Value', fontdict=label_font)
# plt.grid(True)
# plt.legend()

plt.subplot(grid[0, 0])
plt.plot(x, avgL, marker='^', linestyle='-', color='r')
plt.title('Average requests', fontdict=title_font)
plt.xlabel('Time', fontdict=label_font)
plt.ylabel('Value', fontdict=label_font)
# plt.ylim(0,2200)
plt.grid(True)
plt.legend()
ax = plt.gca()  # 获取当前轴
ax.xaxis.set_tick_params(labelsize=14)  # 设置X轴刻度大小
ax.yaxis.set_tick_params(labelsize=14)  # 设置Y轴刻度大小
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontweight('bold')  # 设置字体为加粗


# plt.subplot(grid[1, 0])
# plt.plot(x, Rsizes, marker='o', linestyle='-', color='b')
# plt.title('Rsizes', fontdict=title_font)
# plt.xlabel('Time', fontdict=label_font)
# plt.ylabel('Value', fontdict=label_font)
# plt.grid(True)
# plt.legend()

plt.subplot(grid[1, 0])
plt.plot(x, avgT, marker='^', linestyle='-', color='r')
plt.title('Average Rsizes', fontdict=title_font)
plt.xlabel('Time', fontdict=label_font)
plt.ylabel('Value', fontdict=label_font)
# plt.ylim(600,1100)
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