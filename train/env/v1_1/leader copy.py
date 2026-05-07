import grpc
import pbft_pb2
import pbft_pb2_grpc
import time
import threading
from train.env.v2.node_bk import Node
from concurrent import futures
import os

# TODO: ts的格式不对，现在是port不是time

PRINT_MESSAGE = False
WRITE_MODE = False



def write_size_to_time_to_file(size_to_time, filename):
    with open(filename, 'w') as file:
        for size, time in size_to_time.items():
            file.write(f"{size}\t{time * 1000}\n")
    file.close()

class Leader(Node):

    def __init__(self, batch_size, batch_timeout, other_node_ports):
        super().__init__(port, other_node_ports)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.lock = threading.Lock()
        self.commit_count = 0
        self.complete = 0
        self.small_size = 100
        self.large_size = 10000
        self.size_to_time = {}
    
    def start(self, sn, view, leader_id):
        # 设置total_batchsize的变化，sn, view
        for total_batchsize in range(self.small_size,self.large_size+1,100):
            record_list = []
            cnt = 0
            for i in range(100):
                self.commit_message = None

                start_time = time.time()
                if PRINT_MESSAGE:
                    print("start_time: ", start_time)
                self.send_preprepare(cnt, view, leader_id, total_batchsize)
                while self.commit_message is None:
                    continue
                self.send_commit(self.commit_message)

                while self.complete == 0:
                    continue
                # print("test")
                self.complete = 0

                end_time = time.time()
                if PRINT_MESSAGE:
                    print("end time: ", end_time)
                record = (cnt, total_batchsize, end_time-start_time)
                cnt += 1
                print("record is",record)
                record_list.append(record[2])
            mean_time = sum(record_list)/len(record_list)
            if WRITE_MODE:
                with open("size_to_time.txt", 'w') as file:
                    file.write(f"{total_batchsize}\t{mean_time * 1000}\n")
                file.close()
            else:
                print("total size and mean time: ",total_batchsize,mean_time)
            
            
    def send_preprepare(self, sn, view, leader_id, total_batchsize):
        # 打包请求
        random_data = os.urandom(total_batchsize)

        request_id = pbft_pb2.RequestID(
            client_id = 1,
            client_sn = 2
        )

        client_request = pbft_pb2.ClientRequest(
            request_id = request_id,
            payload = random_data,
            pubkey = os.urandom(256),
            signature = os.urandom(256)
        )

        batch = pbft_pb2.Batch(
            requests = [client_request]
        )

        preprepare_message = pbft_pb2.PbftPreprepare(
            sn=sn,
            view=view,
            leader=leader_id,
            batch=batch,
            aborted=False,
            ts=int(self.port)
        )
        self.broadcast_preprepare(preprepare_message)

    def broadcast_preprepare(self, preprepare_message):
        # for port, (worker, queue) in self.worker_threads.items():
        #     queue.put(("preprepare", preprepare_message))
        for port in self.other_node_ports:
            if PRINT_MESSAGE:
                print("leader send to port: ",port)
            channel = grpc.insecure_channel(f'localhost:{port}')
            stub = pbft_pb2_grpc.PbftServiceStub(channel)
            try:
                stub.GetPreprepare(preprepare_message)
            except Exception as e:
                print(f"Error calling GetPreprepare on port {port}: {e}")
    
    def GetPrepare(self, request, context):
        return super().GetPrepare(request, context)
    
    def send_commit(self, commit_message):
        return super().send_commit(commit_message)
  
    # 不需要接收所有就可以结束，但是接收所有之后才能设置为0，count, 要不要在preprepare那一步设置count==0？不是在这里设置？
    def GetCommit(self, request, context):
        if PRINT_MESSAGE:
            print(f"Leader {self.port} received Commit from {request.ts}")
        with self.lock:
            self.commit_count += 1
        if self.commit_count >= len(self.other_node_ports):
            self.commit_count = 0
            self.complete = 1
    
        return pbft_pb2.google_dot_protobuf_dot_empty__pb2.Empty()

def serve(port, other_node_ports):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    leader = Leader(batch_size=5, batch_timeout=10, other_node_ports=other_node_ports)
    pbft_pb2_grpc.add_PbftServiceServicer_to_server(leader, server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"Leader {port} started")
    leader.start(sn=1, view=1, leader_id=0)
    server.wait_for_termination()



if __name__ == "__main__":
    port = int(os.getenv("PORT", 50050))
    other_ports = [p for p in [50050, 50051,50052,50053] if p != port]
    serve(port, other_ports)
