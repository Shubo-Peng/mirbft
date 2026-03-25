import matplotlib.pyplot as plt

instances = [1, 2,3, 4, 6, 12]
throughput = [19.88, 21.12, 21.96, 21.01, 20.92, 20.69]

plt.figure(figsize=(8, 5))
plt.plot(instances, throughput, marker='o', color='purple', linewidth=2)

for x, y in zip(instances, throughput):
    plt.text(x, y + 0.3, f"{y:.2f}k", ha='center', fontsize=10)

plt.xlabel("Number of Instances", fontsize=12)
plt.ylabel("Throughput (k)", fontsize=12)
plt.title("Throughput vs. Number of Instances", fontsize=14)
plt.xticks(instances)
plt.ylim(19, 23)
plt.grid(True)
plt.tight_layout()
plt.savefig('Throughput.png', format='png', dpi=1000)
plt.show()
