import numpy as np
import matplotlib.pyplot as plt

def moving_average(data, window_size=5):
    """计算滑动平均，窗口大小默认为10"""
    result = []
    for i in range(len(data)):
        # 确定窗口起始位置（确保不超出数组边界）
        start_idx = max(0, i - window_size + 1)
        # 提取窗口内的数据
        window = data[start_idx:i+1]
        # 计算平均值并添加到结果中
        result.append(np.mean(window))
    return result

# 从文件读取数据
def read_data(filename):
    with open(filename, 'r') as f:
        return [float(line.strip()) for line in f]

# 读取原始数据
maml_ppo = read_data('maml_score.txt')
ppo = read_data('score.txt')

# 应用滑动平均
maml_smoothed = moving_average(maml_ppo)
ppo_smoothed = moving_average(ppo)

x = np.linspace(0, len(ppo)-1, len(ppo))

# 绘制图表
plt.figure(figsize=(12, 7))
plt.plot(x, maml_smoothed, label='FOMAML-PPO', color='blue', linewidth=3)
plt.plot(x, ppo_smoothed, label='PPO', color='orange', linewidth=3)

plt.tick_params(axis='x', labelsize=40)  # 改变x轴刻度文字大小
plt.tick_params(axis='y', labelsize=40)  # 改变y轴刻度文字大小

plt.xlabel('Training Steps', fontsize=40)
plt.ylabel('Mean Rewards', fontsize=40, labelpad=-25)
# plt.title('Learning Curves with 10-point Moving Average', fontsize=14)
plt.legend(fontsize=35)
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()

# 保存和显示图表
plt.savefig('learning_curve_5.pdf', dpi=1000)
plt.show()
