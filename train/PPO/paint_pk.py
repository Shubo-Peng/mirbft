import matplotlib.pyplot as plt
import numpy as np
from matplotlib import gridspec

# 数据
workloads = ['200', '2000', '20000']
x = np.arange(len(workloads))

static = [0.21, 2.01, 18.2]
ppo = [0.23, 2.15, 20.1]
maml_ppo = [0.22, 2.12, 20.3]

bar_width = 0.25

# 创建上下两个子图
fig = plt.figure(figsize=(9, 6))
gs = gridspec.GridSpec(2, 1, height_ratios=[1, 3], hspace=0.05)

# 上方子图：显示高区间
ax0 = plt.subplot(gs[0])
# 只绘制20000的数据（高区间部分）
ax0.bar(x[2] - bar_width, static[2], width=bar_width, color='gray')
ax0.bar(x[2], ppo[2], width=bar_width, color='orange')
ax0.bar(x[2] + bar_width, maml_ppo[2], width=bar_width, color='blue')

for i in range(2, len(x)):
    ax0.text(x[i] - bar_width, static[i] + 0.3, f"{static[i]:.2f}", ha='center', fontsize=10)
    ax0.text(x[i], ppo[i] + 0.3, f"{ppo[i]:.2f}", ha='center', fontsize=10)
    ax0.text(x[i] + bar_width, maml_ppo[i] + 0.3, f"{maml_ppo[i]:.2f}", ha='center', fontsize=10)

ax0.set_ylim(17, 22)  # 设置高区间范围
ax0.set_xlim(-0.5, len(workloads)-0.5)  # 保持x轴范围一致
ax0.spines['bottom'].set_visible(False)
plt.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)
ax0.set_yticks([18, 20, 22])
ax0.grid(axis='y')

# 下方子图：显示完整低区间
ax1 = plt.subplot(gs[1])
# 绘制所有数据（20000的柱子会延伸到高区间，但会被截断）
ax1.bar(x - bar_width, static, width=bar_width, label='Static', color='gray')
ax1.bar(x, ppo, width=bar_width, label='PPO', color='orange')
ax1.bar(x + bar_width, maml_ppo, width=bar_width, label='MAML-PPO', color='blue')

for i in range(len(x)-1):
    ax1.text(x[i] - bar_width, static[i] + 0.1, f"{static[i]:.2f}", ha='center', fontsize=10)
    ax1.text(x[i], ppo[i] + 0.1, f"{ppo[i]:.2f}", ha='center', fontsize=10)
    ax1.text(x[i] + bar_width, maml_ppo[i] + 0.1, f"{maml_ppo[i]:.2f}", ha='center', fontsize=10)

ax1.set_ylim(0, 3)  # 设置低区间范围
ax1.set_xlim(-0.5, len(workloads)-0.5)  # 保持x轴范围一致
ax1.set_xticks(x)
ax1.set_xticklabels(workloads)
ax1.set_ylabel('Peak Throughput (k)', fontsize=12)
ax1.grid(axis='y')
ax1.spines['top'].set_visible(False)

# 断轴效果（只断坐标轴，不断柱子）
d = .5  # 斜杠宽度
kwargs = dict(marker=[(-1, -d), (1, d)], markersize=12,
              linestyle="none", color='k', mec='k', mew=1, clip_on=False)
ax0.plot([0, 1], [0, 0], transform=ax0.transAxes, **kwargs)
ax1.plot([0, 1], [1, 1], transform=ax1.transAxes, **kwargs)

# 图例（只在下图显示）
ax1.legend(loc='upper left')
plt.xlabel('Workload', fontsize=12)
plt.tight_layout()
plt.savefig('Throughput2.png', format='png', dpi=1000)
plt.show()