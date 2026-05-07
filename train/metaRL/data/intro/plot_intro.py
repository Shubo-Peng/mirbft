import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 读取CSV数据
df = pd.read_csv("12nodes.csv")

# 提取必要字段（我们会用两次不同的过滤）
df_base = df[['nlr', 'target-throughput', 'throughput-trunc', 'latency-avg-trunc']]

# 获取 workload 横轴值
workloads = sorted(df_base['target-throughput'].unique())

# 公共函数：提取指定 nlr 值对应的数据矩阵
def get_grouped_values(df_subset, nlr_list, metric_name):
    values = []
    for w in workloads:
        row = []
        for n in nlr_list:
            v = df_subset[(df_subset['target-throughput'] == w) & (df_subset['nlr'] == n)][metric_name]
            row.append(v.values[0] if not v.empty else 0)
        values.append(row)
    return np.array(values).T  # 每行一个 nlr，列是 workload

# 绘图函数：带数值标签和保存为PNG
def plot_bar(data, nlr_list, ylabel, filename, title=""):
    bar_width = 0.8 / len(nlr_list)  # 自动适配柱子宽度
    x = np.arange(len(workloads))

    plt.figure(figsize=(10, 6))

    for i, row in enumerate(data):
        bar_pos = x + (i - (len(nlr_list)-1)/2) * bar_width
        bars = plt.bar(bar_pos, row, width=bar_width, label=f'{nlr_list[i]} instances')

        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2, height + 0.02 * max(row), f'{int(height)}',
                     ha='center', va='bottom', fontsize=8)

    plt.xticks(x, workloads)
    plt.xlabel('Workload')
    plt.ylabel(ylabel)
    # plt.title(title)
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close()
    print(f"图像已保存为: {filename}")

# === 图1：Throughput (nlr = 3, 4, 6, 8) ===
nlr_throughput = [3, 4, 6, 8]
df_tp = df_base[df_base['nlr'].isin(nlr_throughput)]
throughput_data = get_grouped_values(df_tp, nlr_throughput, 'throughput-trunc')

plot_bar(
    throughput_data,
    nlr_list=nlr_throughput,
    ylabel='Throughput',
    filename='throughput1.png'
)

# === 图2：Latency (nlr = 8, 10, 12) ===
nlr_latency = [1, 2, 3]
df_lat = df_base[df_base['nlr'].isin(nlr_latency)]
latency_data = get_grouped_values(df_lat, nlr_latency, 'latency-avg-trunc')

plot_bar(
    latency_data,
    nlr_list=nlr_latency,
    ylabel='Latency (ms)',
    filename='latency1.png'
)
