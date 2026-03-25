import matplotlib.pyplot as plt
import numpy as np

# 横轴 workload（单位 kreq/s）
x_labels = [32, 48, 64, 112]
x = np.arange(1, len(x_labels)+1)  # [1, 2, 3, 4, 5]

# 每种方法的 throughput（单位 ktps）
rule_vals = [23.13, 22.68, 16.34, 16.51]
rl_vals = [23.10, 23.22, 23.07, 23.25]

methods = ['Rule-based', 'ORCA']
bar_width = 0.25

plt.figure(figsize=(12, 12))
ax = plt.gca()

# 添加背景阶梯（淡橙色矩形），并保存第一个用于图例
# background_bars = []
# for xi, workload in zip(x, x_labels):
#     bar = ax.bar(xi, 30, width=1.0, color='orange', alpha=0.3, zorder=0)
#     if not background_bars:
#         background_bars = bar  # 保存第一个 bar 对象用于图例

# 画每个方法的柱子（覆盖在背景上）
for i, (vals, label) in enumerate(zip([rule_vals, rl_vals], methods)):
    bar_pos = x + (i - 1) * bar_width
    bars = plt.bar(bar_pos, vals, width=bar_width, label=label, zorder=2)
    
    # 加数值标签
    for bar in bars:
        height = bar.get_height()
        # plt.text(bar.get_x() + bar.get_width()/2, height + 1, f'{int(height)}', 
        #          ha='center', va='bottom', fontsize=20)

plt.tick_params(axis='x', labelsize=40)  # 改变x轴刻度文字大小
plt.tick_params(axis='y', labelsize=40)  # 改变y轴刻度文字大小

# 设置坐标轴
plt.xticks(x, [str(l) for l in x_labels])
plt.xlabel('epoch length (per leader)', fontsize=50)
plt.ylabel('Throughput (ktps)', fontsize=50)
plt.ylim(16, 24)

# 添加图例（包括背景）
handles, labels = ax.get_legend_handles_labels()
# handles.insert(0, background_bars[0])  # 插入背景 bar
# labels.insert(0, 'Workload (ktps)')   # 对应标签
plt.legend(handles, labels, fontsize=33)

plt.grid(axis='y', linestyle='--', alpha=0.5, zorder=1)
plt.tight_layout()
plt.savefig("throughput_baselines_fault.pdf", dpi=1600)
plt.show()
