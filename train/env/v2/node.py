import grpc
from concurrent import futures
import pbft_pb2
import pbft_pb2_grpc
import time
import threading
import os

PRINT_MESSAGE = False

# 问题在于决定如何处理的是哪一批次的request，如何丢弃没有用的request
all_clients_connected, all_received = threading.Condition(), threading.Condition()

class Node(pbft_pb2_grpc.PbftServiceServicer):
    def __init__(self, port, other_node_ports):
        self.port = port
        self.other_node_ports = other_node_ports
        self.prepare_count = 0
        self.lock = threading.Lock()
        self.fault_tolerate = 1
        self.prepare_message = {}
        self.commit_message = {}
        self.port_to_stubs = {}
        self.generateStubs()

    def generateStubs(self):
        for port in self.other_node_ports:
            channel = grpc.insecure_channel(f'localhost:{port}')
            stub = pbft_pb2_grpc.PbftServiceStub(channel)
            self.port_to_stubs[port] = stub
            self.prepare_message[port] = None
            self.commit_message[port] = None

        
    def run(self,port):
        while True:
            # 有可能leader已经send preprepare了，但是node还在send commit，结果重新把prepare_message设置成None了，所以用完马上清空好一点
            while self.prepare_message[port] is None:
                continue
            if PRINT_MESSAGE:
                print(f"{self.port} send prepare to {port}")

            self.send_prepare(self.prepare_message[port], port)
            self.prepare_message[port] = None

            while self.commit_message[port] is None:
                continue

            self.send_commit(self.commit_message[port],port)
            self.commit_message[port] = None

    def GetPreprepare(self, request, context):
        if PRINT_MESSAGE:
            print(f"Node {self.port} received Preprepare from {request.ts}")
        try:
            prepare_message = pbft_pb2.PbftPrepare(sn = request.sn, view = request.view, digest=os.urandom(256),ts = int(self.port))
            for pt in self.other_node_ports:
                self.prepare_message[pt] = prepare_message            
        except Exception as e:
            print(f"Error calling GetPreprepare on port {self.port}: {e}")
        return pbft_pb2.google_dot_protobuf_dot_empty__pb2.Empty()
        
    def send_prepare(self,prepare_message,port):
        # channel = grpc.insecure_channel(f'localhost:{port}')
        # stub = pbft_pb2_grpc.PbftServiceStub(channel)
        stub = self.port_to_stubs[port]
        try:
            stub.GetPrepare(prepare_message)
        except Exception as e:
            print(f"Error calling GetPrepare on port {self.port} to {port}: {e}")
        # self.broadcast_prepare(prepare_message)
    
    def broadcast_prepare(self, prepare_message):
        for port in self.other_node_ports:
            channel = grpc.insecure_channel(f'localhost:{port}')
            stub = pbft_pb2_grpc.PbftServiceStub(channel)
            try:
                stub.GetPrepare(prepare_message)
            except Exception as e:
                print(f"Error calling GetPrepare on port {self.port}: {e}")
    
    # 不需要接收所有就可以结束，但是接收所有之后才能设置为0，count
    def GetPrepare(self, request, context):
        # print(f"Node {self.port} received Prepare: {request}")
        if PRINT_MESSAGE:
            print(f"Node {self.port} received Prepare from {request.ts}")   

        with self.lock:
            self.prepare_count += 1
        try:
            # 如果收到足够多的prepare消息，则发送commit消息, 2f+1,1可以是自己
            if self.prepare_count >= 2 * self.fault_tolerate:
                # self.commit_message[int(request.ts)] = pbft_pb2.PbftCommit(sn=request.sn, view=request.view, digest=request.digest, ts=int(self.port))
                commit_message = pbft_pb2.PbftCommit(sn=request.sn, view=request.view, digest=request.digest, ts=int(self.port))
                for pt in self.other_node_ports:
                    self.commit_message[pt] = commit_message
                self.prepare_count = 0
        except Exception as e:
            print(f"error happens in receiving GetPrepare on port {self.port}, message from {request.ts}")
        
        return pbft_pb2.google_dot_protobuf_dot_empty__pb2.Empty()
    
    def send_commit(self, commit_message,port):
        # channel = grpc.insecure_channel(f'localhost:{port}')
        # stub = pbft_pb2_grpc.PbftServiceStub(channel)
        stub = self.port_to_stubs[port]
        try:
            stub.GetCommit(commit_message)
        except Exception as e:
            print(f"Error calling GetCommit on port {port}: {e}")
        # self.broadcast_commit(commit_message)

    def broadcast_commit(self, commit_message):
        for port in self.other_node_ports:
            channel = grpc.insecure_channel(f'localhost:{port}')
            stub = pbft_pb2_grpc.PbftServiceStub(channel)
            stub.GetCommit(commit_message)

    def GetCommit(self, request, context):
        # print(f"Node {self.port} received Commit: {request}")
        if PRINT_MESSAGE:
            print(f"Node {self.port} received Commit from {request.ts}")
        return pbft_pb2.google_dot_protobuf_dot_empty__pb2.Empty()


def serve(port, other_node_ports):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    node = Node(port, other_node_ports)
    pbft_pb2_grpc.add_PbftServiceServicer_to_server(node, server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    for pt in other_node_ports:
        threading.Thread(target=node.run, args=(pt,)).start()

    print(f"Node {port} started")
    server.wait_for_termination()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 50050))
    # other_ports = [p for p in [50050, 50051, 50052] if p != port]
    other_ports = [p for p in [50050, 50051, 50052,50053] if p != port]

    serve(port, other_ports)
