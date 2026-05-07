import matplotlib.pyplot as plt
import numpy as np

# 横轴 workload（单位 kreq/s）
x_labels = [5, 60, 120]
x = np.arange(1, len(x_labels)+1)  # [1, 2, 3, 4, 5]

# 每种方法的 throughput（单位 ktps）
instance_2 = [4.989695375, 57.67008299, 49.9884424]
instance_8 = [4.993523923, 60.29018641, 120.5639867]
instance_12 = [4.991736165, 60.29479134, 120.906621]

methods = ['2 instances', '8 instances', '12 instance']
bar_width = 0.25

plt.figure(figsize=(10, 10))
ax = plt.gca()

# 添加背景阶梯（淡橙色矩形），并保存第一个用于图例
background_bars = []
for xi, workload in zip(x, x_labels):
    bar = ax.bar(xi, workload, width=1.0, color='orange', alpha=0.3, zorder=0)
    if not background_bars:
        background_bars = bar  # 保存第一个 bar 对象用于图例

# 画每个方法的柱子（覆盖在背景上）
for i, (vals, label) in enumerate(zip([instance_2, instance_8, instance_12], methods)):
    bar_pos = x + (i - 1) * bar_width
    bars = plt.bar(bar_pos, vals, width=bar_width, label=label, zorder=2)
    
    # 加数值标签
    for bar in bars:
        height = bar.get_height()
        # plt.text(bar.get_x() + bar.get_width()/2, height + 1, f'{int(np.round(height))}', 
        #          ha='center', va='bottom', fontsize=40)

plt.tick_params(axis='x', labelsize=35)  # 改变x轴刻度文字大小
plt.tick_params(axis='y', labelsize=35)  # 改变y轴刻度文字大小

# 设置坐标轴
plt.xticks(x, [str(l) for l in x_labels])
plt.xlabel('Workload (ktps)', fontsize=40)
plt.ylabel('Throughput (ktps)', fontsize=40)

# 添加图例（包括背景）
handles, labels = ax.get_legend_handles_labels()
handles.insert(0, background_bars[0])  # 插入背景 bar
labels.insert(0, 'Workload (ktps)')   # 对应标签
plt.legend(handles, labels, fontsize=30)

plt.grid(axis='y', linestyle='--', alpha=0.5, zorder=1)
plt.subplots_adjust(left=0.18, right=0.98, top=0.98, bottom=0.12)
# plt.tight_layout()
plt.savefig("throughput_intro.pdf", dpi=300)
plt.show()
