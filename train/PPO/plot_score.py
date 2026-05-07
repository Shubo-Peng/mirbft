import matplotlib.pyplot as plt
import numpy as np

# 假设这是你的数据列表
file = open("./scores.txt", 'r')
data = file.readlines()
scores = []
for line in data:
    score = line.split('score : ')[-1].split('\n')[0]
    scores.append(float(score))
# print(scores)

# 创建一个索引列表，与数据列表相对应
length = 120
x = list(range(length))
y_ori = []
y_avg = []
for i in range(length):
    # y.append(np.mean(scores[max(0,i-100):i]))
    y_ori.append(scores[i])
    y_avg.append(np.mean(scores[max(0,i-30):i]))

title_font = {
    'fontsize': 20,
    'fontweight': 'bold'
}

label_font = {
    'fontsize': 18,
    'fontweight': 'bold'
}

# 创建一个折线图
# plt.figure(figsize=(10, 5))  # 可以设置图形大小
plt.figure(figsize=(20,5))
grid = plt.GridSpec(1, 2, wspace = 0.2, hspace = 0.2)
plt.subplot(grid[0, 0])
plt.plot(x, y_ori, marker='o', linestyle='-', color='b')
plt.title('Score', fontdict=title_font)
plt.xlabel('Episode', fontdict=label_font)
plt.ylabel('Value', fontdict=label_font)
# 可以添加网格（可选）
plt.grid(True)
# 添加图例（可选）
plt.legend()

plt.subplot(grid[0, 1])
plt.plot(x, y_avg, marker='^', linestyle='-', color='r')
plt.title('Average Score', fontdict=title_font)
plt.xlabel('Episode', fontdict=label_font)
plt.ylabel('Value', fontdict=label_font)
# 可以添加网格（可选）
plt.grid(True)
# 添加图例（可选）
plt.legend()

plt.savefig('average_scores.eps', format='eps', dpi=1000)

# 展示图形
plt.show()