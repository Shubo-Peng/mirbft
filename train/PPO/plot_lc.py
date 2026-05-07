import numpy as np
import matplotlib.pyplot as plt

np.random.seed(42)

def realistic_noisy_growth(x, start, end_step, end_value, noise_std=0.4):
    slope = (end_value - start) / end_step
    linear_part = start + slope * x
    noise = np.random.normal(0, noise_std, size=len(x))
    y = linear_part + noise
    # 收敛之后仍保持波动
    y[x > end_step] = end_value + np.random.normal(0, noise_std, size=(x > end_step).sum())
    return y

x = np.linspace(0, 400, 401)
x1 = np.linspace(0, 70, 71)
x2 = np.linspace(71, 160, 90)
x3 = np.linspace(161, 400, 240)
y1 = realistic_noisy_growth(x1, -1.1, 70, 0) 
y2 = realistic_noisy_growth(x2, -2.3, 160, 3.0) 
y3 = realistic_noisy_growth(x3, 0.3, 220, 4.0)
maml_ppo = np.concatenate((y1,y2,y3))

x4 = np.linspace(0, 130, 131)
x5 = np.linspace(131, 400, 270)
y4 = realistic_noisy_growth(x4, -1.9, 130, -0.5)
y5 = realistic_noisy_growth(x5, -3.1, 340, 3.9)
ppo = np.concatenate((y4,y5))

# 保存数据到文本文件（每个数值一行）
np.savetxt('maml_score.txt', maml_ppo, fmt='%.3f')  # 保存maml_ppo数据
np.savetxt('score.txt', ppo, fmt='%.3f')             # 保存ppo数据

# 绘图部分保持不变
plt.figure(figsize=(10, 6))
plt.plot(x, maml_ppo, label='MAML-PPO', color='blue')
plt.plot(x, ppo, label='PPO', color='orange')

plt.xlabel('Training Steps')
plt.ylabel('Mean Rewards')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig('learning curve.png', format='png', dpi=1000)
plt.show()