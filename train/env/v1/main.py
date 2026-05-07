# main.py
from server import serve
from client import Node
import threading
import time

def start_server(port):
    threading.Thread(target=serve, args=(port,), daemon=True).start()

def main():
    ports = [50051, 50052, 50053, 50054]
    
    # Start servers
    for port in ports:
        start_server(port)
    
    # Wait for servers to start
    time.sleep(2)
    
    # Create nodes
    nodes = [Node(f"Node{i+1}", port) for i, port in enumerate(ports)]
    
    # Example communication
    for i, node in enumerate(nodes):
        next_node = nodes[(i + 1) % len(nodes)]
        node.send_message(next_node.port, f"Hello from {node.name} to {next_node.name}")

if __name__ == "__main__":
    main()