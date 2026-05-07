import grpc
import pbft_pb2
import pbft_pb2_grpc
import time
import threading
from node import Node
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
        self.large_size = 100
        self.size_to_time = {}
        self.startFlag = False
        self.preprepare_message = self.generate_preprepare_message(1,1,1,100)

        self.pre_time = 0
        self.prepre_time = 0
        self.com_time = 0

    def generate_preprepare_message(self,sn, view, leader_id ,total_batchsize):
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
        return preprepare_message

    def controller(self):
        while True:
            self.start_time = time.time()

            self.startFlag = True
            
            if PRINT_MESSAGE:
                print("\nstart_time: ", self.start_time,"\n")

            while self.complete == 0:
                continue
        
            self.end_time = time.time()
            self.complete = 0

            if PRINT_MESSAGE:
                print("end time: ", self.end_time,"\n")
            
            print(f"cost time: {self.end_time-self.start_time}")
    
    def start(self, sn, view, leader_id, port):
        # 设置total_batchsize的变化，sn, view
        while True:
            if self.startFlag == True:

                self.commit_message[port] = None

                if PRINT_MESSAGE:
                    print(f"leader send prepreare message to: {port}")
                
                # 100是batchsize
                self.send_preprepare(0, view, leader_id, 100, port)

                print("after send preprepare: ", time.time() - self.start_time)
                
                while self.commit_message[port] is None:
                    continue
                self.startFlag = False

                self.send_commit(self.commit_message[port],port)
            
    def send_preprepare(self, sn, view, leader_id, total_batchsize, port):
        # 打包请求
        stub = self.port_to_stubs[port]
        try:
            stub.GetPreprepare(self.preprepare_message)
        except Exception as e:
            print(f"Error leader calling GetPreprepare on port {port}: {e}")

        # self.broadcast_preprepare(preprepare_message)

    def broadcast_preprepare(self, preprepare_message):
        
        for pt in self.other_node_ports:
            if PRINT_MESSAGE:
                print("leader send to port: ",port)
            stub = self.port_to_stubs[pt]
            try:
                stub.GetPreprepare(preprepare_message)
            except Exception as e:
                print(f"Error leader calling GetPreprepare on port {port}: {e}")

        # stub1 = self.port_to_stubs[P1]
        # stub2 = self.port_to_stubs[P2]
        # stub3 = self.port_to_stubs[P3]

        # if PRINT_MESSAGE:
        #     print("leader send to port: ",port)

        # try:
        #     stub1.GetPreprepare(preprepare_message)
        #     stub2.GetPreprepare(preprepare_message)
        #     stub3.GetPreprepare(preprepare_message)
        # except Exception as e:
        #     print(f"Error leader calling GetPreprepare on port {port}: {e}")
  
    # 不需要接收所有就可以结束，但是接收所有之后才能设置为0，count, 要不要在preprepare那一步设置count==0？不是在这里设置？
    def GetCommit(self, request, context):
        if PRINT_MESSAGE:
            print(f"Leader {self.port} received Commit from {request.ts}")
        with self.lock:
            self.commit_count += 1
        # if self.commit_count >= 2 * self.fault_tolerate:
        if self.commit_count >= len(self.other_node_ports):
            self.complete = 1
            self.commit_count = 0    

        return pbft_pb2.google_dot_protobuf_dot_empty__pb2.Empty()

def serve(port, other_node_ports):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    leader = Leader(batch_size=5, batch_timeout=10, other_node_ports=other_node_ports)
    pbft_pb2_grpc.add_PbftServiceServicer_to_server(leader, server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"Leader {port} started")
    for pt in other_node_ports:
        threading.Thread(target=leader.start, args=(1,1,0,pt,)).start()
    time.sleep(1)
    threading.Thread(target=leader.controller).start()
    server.wait_for_termination()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 50050))
    other_ports = [p for p in [50050, 50051,50052,50053] if p != port]
    serve(port, other_ports)



#    for total_batchsize in range(self.small_size,self.large_size+1,100):
#             record_list = []
#             cnt = 0
#             for i in range(1):
#                 self.commit_message = None

#                 start_time = time.time()
                
#                 if PRINT_MESSAGE:
#                     print("\nstart_time: ", start_time)

#                 ###########################################################
#                 # 需要并行
#                 self.send_preprepare(cnt, view, leader_id, total_batchsize)
                
#                 while self.commit_message is None:
#                     continue
#                 self.send_commit(self.commit_message)
#                 ###########################################################

#                 while self.complete == 0:
#                     continue
#                 # print("test")
#                 self.complete = 0

#                 end_time = time.time()
#                 if PRINT_MESSAGE:
#                     print("end time: ", end_time,"\n")
#                 record = (cnt, total_batchsize, end_time-start_time)
#                 cnt += 1
#                 print("record is",record)
#                 record_list.append(record[2])
#             mean_time = sum(record_list)/len(record_list)
#             if WRITE_MODE:
#                 with open("size_to_time.txt", 'w') as file:
#                     file.write(f"{total_batchsize}\t{mean_time * 1000}\n")
#                 file.close()
#             else:
#                 print("total size and mean time: ",total_batchsize,mean_time)
            