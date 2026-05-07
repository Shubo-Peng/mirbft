import pandas as pd
import matplotlib.pyplot as plt

# 文件路径
file1 = "12nodes.csv"
file2 = "12nodes-straggler.csv"

# 读取 CSV 数据
df1 = pd.read_csv(file1)
df2 = pd.read_csv(file2)

# 提取横轴 epoch 和纵轴 throughput-trunc
epochs1 = df1['epoch']
throughput1 = df1['throughput-trunc'] / 1000

epochs2 = df2['epoch']
throughput2 = df2['throughput-trunc'] / 1000

# 创建折线图
plt.figure(figsize=(10, 6))
plt.plot(epochs1, throughput1, marker='o', label='12nodes', color='blue')
plt.plot(epochs2, throughput2, marker='s', label='12nodes-straggler', color='orange')

plt.tick_params(axis='x', labelsize=20)  # 改变x轴刻度文字大小
plt.tick_params(axis='y', labelsize=20)  # 改变y轴刻度文字大小

# 设置图表属性
plt.xlabel('Epoch', fontsize=35)
plt.ylabel('Throughput (ktps)', fontsize=35)
# plt.title('Throughput vs Epoch', fontsize=16)
plt.grid(True, linestyle='--', alpha=0.5)
plt.legend(fontsize=20)
plt.tight_layout()
plt.savefig("motivation.png", dpi=300)
plt.show()
