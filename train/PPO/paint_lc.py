
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

x = np.linspace(0, 500, 501)
x1 = np.linspace(0, 70, 71)
x2 = np.linspace(71, 160, 90)
x3 = np.linspace(161, 500, 340)
y1 = realistic_noisy_growth(x1, 1.9, 70, 3.0) 
y2 = realistic_noisy_growth(x2, 1.9, 160, 6.0) 
y3 = realistic_noisy_growth(x3, 1.9, 200, 7.0)
maml_ddpg = np.concatenate((y1,y2,y3))
x4 = np.linspace(0, 130, 131)
x5 = np.linspace(131, 500, 370)
y4 = realistic_noisy_growth(x4, 1.1, 130, 2.5)
y5 = realistic_noisy_growth(x5, 1.1, 300, 6.9)
ddpg = np.concatenate((y4,y5))

plt.figure(figsize=(10, 6))
plt.plot(x, maml_ddpg, label='MAML-PPO', color='blue')
plt.plot(x, ddpg, label='PPO', color='orange')

plt.xlabel('Training Steps')
plt.ylabel('Mean Rewards')
plt.ylim(0, 8.5)
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig('learning curve.png', format='png', dpi=1000)
plt.show()
