import subprocess
import time
import sys

def start_node(port):
    print(f"Starting node on port {port}...")
    return subprocess.Popen([sys.executable, 'node.py'], env={"PORT": str(port)})

def start_leader():
    print("Starting leader...")
    return subprocess.Popen([sys.executable, 'leader.py'])

if __name__ == "__main__":
    nodes = []
    node_ports = [50051,50052,50053]

    # 启动三个节点
    for port in node_ports:
        nodes.append(start_node(port))
        time.sleep(1)

    # 启动 leader
    leader = start_leader()

    # 保持进程活跃
    leader.wait()
    for node in nodes:
        node.wait()
