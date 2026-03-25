import matplotlib.pyplot as plt
import numpy as np

# 横轴 workload（单位 kreq/s）
x_labels = [5, 60, 120]
x = np.arange(1, len(x_labels)+1)  # x = [1, 2, 3]

# 三种方法的 latency（单位 s）
static_vals = [0.52226335, 4.760545666, 14.86018116]
rule_vals   = [0.534658726, 0.569764678, 0.672406611]
rl_vals     = [0.777567664, 0.799113757, 0.923233954]

methods = ['2 instances', '8 instances', '12 instances']
bar_width = 0.25

# === 创建三段子图（断轴） ===
fig, (ax_high, ax_mid, ax_low) = plt.subplots(
    3, 1,
    figsize=(10, 10),
    sharex=True,
    gridspec_kw={'height_ratios': [0.6, 0.4, 1.2]},  # top : mid : bottom = 0.4 : 0.3 : 1
)

axes = [ax_low, ax_mid, ax_high]

# === 绘制三段柱状图 ===
for i, (vals, label) in enumerate(zip([static_vals, rule_vals, rl_vals], methods)):
    bar_pos = x + (i - 1) * bar_width
    for ax in axes:
        bars = ax.bar(bar_pos, vals, width=bar_width, label=label if ax == ax_high else "", zorder=2)
        # if ax == ax_low:
        #     for bar in bars:
        #         height = bar.get_height()
        #         ax.text(bar.get_x() + bar.get_width()/2, height + 0.05, f'{np.round(height, 3)}',
        #                 ha='center', va='bottom', fontsize=35)

# === 设置y轴范围、刻度，仅显示一个刻度值 ===
ax_low.set_ylim(0, 1.2)
ax_low.set_yticks([1])

ax_mid.set_ylim(4.5, 5.5)
ax_mid.set_yticks([5])
ax_mid.set_ylabel("Latency (s)", fontsize=40)

ax_high.set_ylim(14, 16)
ax_high.set_yticks([15])

ax_low.spines['top'].set_visible(False)
ax_mid.spines['top'].set_visible(False)
ax_mid.spines['bottom'].set_visible(False)
ax_high.spines['bottom'].set_visible(False)

# === 断轴符号（斜线） ===
def break_mark(ax1, ax2, axis='y', size=0.015):
    kwargs = dict(transform=ax1.transAxes, color='k', clip_on=False, linewidth=1)
    if axis == 'y':
        ax1.plot([-size, +size], [-size, +size], **kwargs)  # 左上
        ax1.plot([1 - size, 1 + size], [-size, +size], **kwargs)  # 右上
        kwargs['transform'] = ax2.transAxes
        ax2.plot([-size, +size], [1 - size, 1 + size], **kwargs)  # 左下
        ax2.plot([1 - size, 1 + size], [1 - size, 1 + size], **kwargs)  # 右下

break_mark(ax_high, ax_mid)
break_mark(ax_mid, ax_low)

# === x轴和图例设置 ===
plt.xticks(x, [str(l) for l in x_labels], fontsize=40)
ax_low.set_xlabel('Workload (ktps)', fontsize=40)
ax_low.tick_params(axis='x', labelsize=40)
for ax in axes:
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.tick_params(axis='y', labelsize=40)

# === 图例只显示一次 ===
ax_high.legend(fontsize=30)

plt.subplots_adjust(hspace=0.1)  # 子图之间空隙小一点
plt.subplots_adjust(left=0.13, right=0.98, top=0.98, bottom=0.12)
# plt.tight_layout(rect=[0, 0, 1, 0.98])
plt.savefig("latency_intro.pdf", dpi=300)
plt.show()
