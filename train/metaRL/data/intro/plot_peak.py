import pandas as pd
import matplotlib.pyplot as plt
import os

# 实验的 instance 数
instance_list = [1, 2, 4, 6, 8, 12]
throughputs = []

# 遍历每个文件，提取最后一行的 throughput-trunc
for instance in instance_list:
    filename = f'12nodes-{instance}instance.csv'
    if not os.path.exists(filename):
        print(f"文件不存在: {filename}")
        throughputs.append(None)
        continue

    df = pd.read_csv(filename)
    throughput = df['throughput-trunc'].iloc[-1]
    throughputs.append(throughput/1000)

# 画折线图
plt.figure(figsize=(8, 5))
plt.plot(instance_list, throughputs, marker='o', color='steelblue', linewidth=2)

plt.xlabel('Instance Number', size=20)
plt.ylabel('Peak Throughput (ktps)', size=20)
# plt.title('Peak Throughput vs Instance Count')
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.savefig("motivation.png", dpi=300)
plt.show()
