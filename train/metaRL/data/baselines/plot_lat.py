import matplotlib.pyplot as plt
import numpy as np

# 横轴 workload（单位 kreq/s）
x_labels = [40, 80, 160]
x = np.arange(1, len(x_labels)+1)  # [1, 2, 3, 4, 5]

static_vals = [2.55, 15.65, 25.03]
rule_vals = [9.28, 14.45, 2.24]
rl_vals = [0.76, 0.53, 0.30]

methods = ['Static Parameter', 'Rule-based', 'ORCA']
bar_width = 0.25

plt.figure(figsize=(12, 12))
ax = plt.gca()

# 添加背景阶梯（淡橙色矩形），并保存第一个用于图例
# background_bars = []
# for xi, workload in zip(x, x_labels):
#     bar = ax.bar(xi, workload, width=1.0, color='orange', alpha=0.3, zorder=0)
#     if not background_bars:
#         background_bars = bar  # 保存第一个 bar 对象用于图例

# 画每个方法的柱子（覆盖在背景上）
for i, (vals, label) in enumerate(zip([static_vals, rule_vals, rl_vals], methods)):
    bar_pos = x + (i - 1) * bar_width
    bars = plt.bar(bar_pos, vals, width=bar_width, label=label, zorder=2)
    
    # 加数值标签
    for bar in bars:
        height = bar.get_height()
        # plt.text(bar.get_x() + bar.get_width()/2, height+0.1, f'{(height)}', 
        #          ha='center', va='bottom', fontsize=15)

plt.tick_params(axis='x', labelsize=40)  # 改变x轴刻度文字大小
plt.tick_params(axis='y', labelsize=40)  # 改变y轴刻度文字大小

# 设置坐标轴
plt.xticks(x, [str(l) for l in x_labels])
plt.xlabel('Workload (ktps)', fontsize=50)
plt.ylabel('Latency (s)', fontsize=50)

# 添加图例（包括背景）
handles, labels = ax.get_legend_handles_labels()
# handles.insert(0, background_bars[0])  # 插入背景 bar
# labels.insert(0, 'Workload (kreq/s)')   # 对应标签
plt.legend(handles, labels, fontsize=33)

plt.grid(axis='y', linestyle='--', alpha=0.5, zorder=1)
plt.tight_layout()
plt.savefig("latency_baselines_12nodes_LAN.pdf", dpi=1600)
plt.show()
