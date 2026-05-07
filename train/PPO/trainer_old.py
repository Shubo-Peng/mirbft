import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
from torch.distributions import Categorical
import sys
import os
import time
import re
import math
import grpc
from concurrent import futures
import threading
import monitor_pb2
import monitor_pb2_grpc

# Hyperparameters
learning_rate = 0.0005
gamma = 0.98
lmbda = 0.98
eps_clip = 0.1
K_epoch = 2
T_horizon = 10

# MAX_EPISODE = 10000

# Discretization
A_values = torch.linspace(128, 4096, 20).int() # BatchSize
B_values = torch.linspace(1000, 4000, 20).int() # BatchTimeout
C_values = torch.tensor([128, 256, 512], dtype=torch.int) # CheckpointInterval
D_values = torch.tensor([128, 256, 512], dtype=torch.int) # WatermarkWindowSize
E_values = torch.tensor([32, 48, 64], dtype=torch.int) # SegmentLength
# default 1024 4000 256 256 64

num_node = 4
connected_clients, received_msg = 0, 0
start_time, tmp_batchSize = 0, 0
all_clients_connected, all_received = threading.Condition(), threading.Condition()

totalRequests = [-1 for _ in range(num_node)]
totalPayload = [-1 for _ in range(num_node)]
proposedRequests = [-1 for _ in range(num_node)]
pRPayload = [-1 for _ in range(num_node)]
latency = [-1 for _ in range(num_node)]
throughput = [-1 for _ in range(num_node)]
CPUload = [-1 for _ in range(num_node)]
CPUsystem = [-1 for _ in range(num_node)]
BS, BT = [0 for _ in range(num_node)], [0 for _ in range(num_node)]
timestamp = [0 for _ in range(num_node)]
totalLatency, totalThroughput = 0, 1e-8
baseline = 1000

class PPO(nn.Module):
    def __init__(self):
        super(PPO, self).__init__()
        self.data = []
        hidden_dims = 256
        self.fc1 = nn.Linear(10, hidden_dims)
        # TODO： Now A and B are independent of each other, use conditional probability?
        self.fc_pi_a = nn.Linear(hidden_dims, 20)
        self.fc2 = nn.Linear(hidden_dims + 20, hidden_dims)
        self.fc_pi_b = nn.Linear(hidden_dims, 20)
        self.fc_pi_c = nn.Linear(hidden_dims, 3)   # CheckpointInterval
        self.fc_pi_d = nn.Linear(hidden_dims, 3)   # WatermarkWindowSize
        self.fc_pi_e = nn.Linear(hidden_dims, 3)   # SegmentLength
        # self.fc_pi_a = nn.Linear(hidden_dims, 40)  # Action A output
        # self.fc_pi_b = nn.Linear(hidden_dims, 40)  # Action B output
        self.fc_v = nn.Linear(hidden_dims, 1)  # Value output
        self.optimizer = optim.Adam(self.parameters(), lr=learning_rate)

    def pi(self, x, softmax_dim=-1):
        # x = torch.relu(self.fc1(x))
        # x = torch.relu(self.fc2(x))
        # prob_a = torch.softmax(self.fc_pi_a(x), dim=softmax_dim)
        # prob_b = torch.softmax(self.fc_pi_b(x), dim=softmax_dim)
        x = F.relu(self.fc1(x))
        prob_a = F.softmax(self.fc_pi_a(x), dim=softmax_dim)
        prob_c = F.softmax(self.fc_pi_c(x), dim=softmax_dim)
        prob_d = F.softmax(self.fc_pi_d(x), dim=softmax_dim)
        prob_e = F.softmax(self.fc_pi_e(x), dim=softmax_dim)
        x = torch.cat((x, prob_a), dim=-1)
        x = F.relu(self.fc2(x))
        prob_b = F.softmax(self.fc_pi_b(x), dim=softmax_dim)
        return prob_a, prob_b, prob_c, prob_d, prob_e

    def v(self, x):
        x = F.relu(self.fc1(x))
        prob_a = F.softmax(self.fc_pi_a(x), dim=-1)
        x = torch.cat((x, prob_a), dim=-1)
        x = F.relu(self.fc2(x))
        v = self.fc_v(x)
        return v

    def put_data(self, transition):
        self.data.append(transition)

    def make_batch(self):
        s_lst, a_lst, b_lst, c_lst, d_lst, e_lst, r_lst, s_prime_lst, prob_a_lst, prob_b_lst, prob_c_lst, prob_d_lst, prob_e_lst = [], [], [], [], [], [], [], [], [], [], [], [], []
        for transition in self.data:
            s, a, b, c, d, e, r, s_prime, prob_a, prob_b, prob_c, prob_d, prob_e = transition
            s_lst.append(s)
            a_lst.append([a])
            b_lst.append([b])
            c_lst.append([c])
            d_lst.append([d])
            e_lst.append([e])
            r_lst.append([r])
            s_prime_lst.append(s_prime)
            prob_a_lst.append([prob_a])
            prob_b_lst.append([prob_b])
            prob_c_lst.append([prob_c])
            prob_d_lst.append([prob_d])
            prob_e_lst.append([prob_e])

        s= np.array(s)
        s, a, b, c, d, e, r = torch.tensor(np.array(s_lst), dtype=torch.float), torch.tensor(np.array(a_lst)), torch.tensor(np.array(b_lst)), torch.tensor(np.array(c_lst)), torch.tensor(np.array(d_lst)), torch.tensor(np.array(e_lst)), torch.tensor(r_lst)
        s_prime, prob_a, prob_b, prob_c, prob_d, prob_e =  torch.tensor(np.array(s_prime_lst), dtype=torch.float), torch.tensor(np.array(prob_a_lst)), torch.tensor(np.array(prob_b_lst)), torch.tensor(np.array(prob_c_lst)), torch.tensor(np.array(prob_d_lst)), torch.tensor(np.array(prob_e_lst))
        self.data = []
        return s, a, b, c, d, e, r, s_prime, prob_a, prob_b, prob_c, prob_d, prob_e

    def train_net(self):
        s, a, b, c, d, e, r, s_prime, prob_a, prob_b, prob_c, prob_d, prob_e = self.make_batch()

        for i in range(K_epoch):
            td_target = r + gamma * self.v(s_prime)
            # print(r.shape, td_target.shape)
            delta = td_target - self.v(s)
            delta = delta.detach().numpy()

            advantage_lst = []
            advantage = 0.0
            for delta_t in delta[::-1]:
                advantage = gamma * lmbda * advantage + delta_t[0]
                advantage_lst.append([advantage])
            advantage_lst.reverse()
            advantage = torch.tensor(np.array(advantage_lst), dtype=torch.float)

            pi_a, pi_b, pi_c, pi_d, pi_e = self.pi(s)
            pi_a = pi_a.gather(1, a)
            pi_b = pi_b.gather(1, b)
            pi_c = pi_c.gather(1, c)
            pi_d = pi_d.gather(1, d)
            pi_e = pi_e.gather(1, e)
            ratio_a = torch.exp(torch.log(pi_a) - torch.log(prob_a))
            ratio_b = torch.exp(torch.log(pi_b) - torch.log(prob_b))
            ratio_c = torch.exp(torch.log(pi_c) - torch.log(prob_c))
            ratio_d = torch.exp(torch.log(pi_d) - torch.log(prob_d))
            ratio_e = torch.exp(torch.log(pi_e) - torch.log(prob_e))
            surr1_a = ratio_a * advantage
            surr2_a = torch.clamp(ratio_a, 1-eps_clip, 1+eps_clip) * advantage
            surr1_b = ratio_b * advantage
            surr2_b = torch.clamp(ratio_b, 1-eps_clip, 1+eps_clip) * advantage
            surr1_c = ratio_c * advantage
            surr2_c = torch.clamp(ratio_c, 1-eps_clip, 1+eps_clip) * advantage
            surr1_d = ratio_d * advantage
            surr2_d = torch.clamp(ratio_d, 1-eps_clip, 1+eps_clip) * advantage
            surr1_e = ratio_e * advantage
            surr2_e = torch.clamp(ratio_e, 1-eps_clip, 1+eps_clip) * advantage

            actor_loss = -(
                0.40 * torch.min(surr1_a, surr2_a).mean() +
                0.40 * torch.min(surr1_b, surr2_b).mean() +
                0.067 * torch.min(surr1_c, surr2_c).mean() +
                0.067 * torch.min(surr1_d, surr2_d).mean() +
                0.067 * torch.min(surr1_e, surr2_e).mean()
            )

            critic_loss = F.smooth_l1_loss(self.v(s), td_target.detach())

            loss = actor_loss + 0.5 * critic_loss

            self.optimizer.zero_grad()
            loss.mean().backward()
            self.optimizer.step()

def select_action(s, model):
    prob_a, prob_b, prob_c, prob_d, prob_e = model.pi(torch.from_numpy(s).float())
    m_a = Categorical(prob_a)
    m_b = Categorical(prob_b)
    m_c = Categorical(prob_c)
    m_d = Categorical(prob_d)
    m_e = Categorical(prob_e)
    a = m_a.sample().item()
    b = m_b.sample().item()
    c = m_c.sample().item()
    d = m_d.sample().item()
    e = m_e.sample().item()
    return a, b, c, d, e, prob_a, prob_b, prob_c, prob_d, prob_e

def read_last_line(filename):
    with open(filename, 'rb') as file:
        # 移动到文件的最后一个字节
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        if file_length == 0:
            return ""
        pos = -1
        while True:
            file.seek(pos, os.SEEK_END)
            if file.tell() == 0:
                file.seek(0)
                break
            byte = file.read(1)
            if byte == b'\n' and pos != -1:
                break
            pos -= 1
        last_line = file.readline().decode()
    return last_line

def load_state_and_reward_from_file(c1, c2, c3, c4, count):
    global totalRequests, totalPayload, proposedRequests, pRPayload, latency, throughput, CPUload, CPUsystem, totalLatency, totalThroughput
    for i in range(num_node):
        while True:
            filePath = "../state" + str(i) + ".txt"
            content = re.split(r'[ \t\n]+', read_last_line(filePath))[1:]
            if len(content) >= 8:
                if int(content[0]) == totalRequests[i] and float(content[1]) == totalPayload[i] and int(content[2]) == proposedRequests[i] and float(content[3]) == pRPayload[i] and \
                math.fabs(float(content[4]) - latency[i]) < 1e-6 and math.fabs(float(content[5]) - throughput[i]) < 1e-6 and int(content[6]) == CPUload[i] and int(content[7]) == CPUsystem[i]:
                    time.sleep(0.001)
                    continue
                totalRequests[i], totalPayload[i], proposedRequests[i], pRPayload[i], latency[i], throughput[i], CPUload[i], CPUsystem[i] = \
                int(content[0]), float(content[1]), int(content[2]), float(content[3]), float(content[4]), float(content[5]), int(content[6]), int(content[7])
                break
    # print(totalRequests, totalPayload)
    a, b, c, d, e, f, g, h = sum(totalRequests)/num_node, sum(totalPayload)/num_node, sum(proposedRequests), sum(pRPayload), 0, sum(throughput), sum(CPUload)/num_node, sum(CPUsystem)/num_node
    tmp = num_node
    for i in range(num_node):
        if throughput[i] > 0:
            e += latency[i] * throughput[i]
            totalLatency += latency[i] * throughput[i]
            totalThroughput += throughput[i]
            tmp -= 1
    if f>0 : e /= f
    else: e = 2000
    state = np.array([a,b,c,d,e,f,g,h,totalLatency/totalThroughput,totalThroughput/(count+1)], dtype=np.float32)
    reward = c1*e + c2*totalLatency/totalThroughput + c3*f + c4*totalThroughput/(count+1)

    # Normalize state
    norm_state = (state - np.mean(state, axis=0)) / np.std(state, axis=0)
    return norm_state, state, reward

def load_state_from_file():
    global totalRequests, totalPayload, proposedRequests, pRPayload, latency, throughput, BS, BT, timestamp
    for i in range(num_node):
        while True:
            filePath = "../state" + str(i) + ".txt"
            content = re.split(r'[ \t\n]+', read_last_line(filePath))[1:]
            if len(content) >= 9:
                if int(content[8]) == timestamp[i]:
                    time.sleep(0.001)
                    continue
                totalRequests[i], totalPayload[i], proposedRequests[i], pRPayload[i], latency[i], throughput[i], BS[i], BT[i], timestamp[i] = \
                int(content[0]), float(content[1]), int(content[2]), float(content[3]), float(content[4]), float(content[5]), int(content[6]), int(content[7]), int(content[8])
                break
    a, b, c, d, e, f = sum(totalRequests), sum(totalPayload), 0, sum(throughput), BS[0], BT[0]
    for i in range(num_node):
        if throughput[i] > 0:
            c += latency[i] * throughput[i]
    if d != 0: c = c/d
    return np.array([int(a),int(b),int(c),int(d),int(e),int(f)])

def main():
    model = PPO()
    # print(model.state_dict())
    a = [1 for _ in range(10)]
    print(model.pi(torch.from_numpy(np.array(a)).float()))
    model_path = "ppo_model_checkpoint.pth"
    score = 0.0
    c1 = -1
    c2 = -0.1
    c3 = 2
    c4 = 0.25

    # for n_epi in range(MAX_EPISODE):
    # s = np.random.randn(6)  # Assuming the state vector is 6-dimensional
    global totalLatency, totalThroughput
    cnt, count = 0, 0

    # Load model and variables
    if os.path.exists(model_path):
        checkpoint = torch.load(model_path)
        model.load_state_dict(checkpoint['model_state'])
        model.optimizer.load_state_dict(checkpoint['optimizer_state'])
        cnt = checkpoint['cnt']
        count = checkpoint['count']
        totalLatency = checkpoint['totalLatency']
        totalThroughput = checkpoint['totalThroughput']
        print("Loaded checkpoint from {}".format(model_path))

    # s, state, r = load_state_and_reward_from_file(c1, c2, c3, c4, count)
    state = load_state_from_file()
    # scores = open("scores.txt",'w')
    throughput, pointer, enough = [0 for _ in range(10)], 0, False
    while True:

        new_state = load_state_from_file()
        if enough:
            avg_throughput, batchSize, batchTimeout = new_state[3], new_state[4], new_state[5]/1000000
            print(avg_throughput, batchSize, new_state[0], state[0])
            if avg_throughput * 1.1 >= state[0]:
                batchSize = math.ceil(batchSize * new_state[0] / state[0])
            else :
                # batchSize = 
                batchSize = 1000
            with open("../parameters.yml", 'w') as file:
                file.write(f'BatchSize: {int(batchSize)}\n')
                file.write(f'BatchTimeout: {int(batchTimeout)}\n')
        throughput[pointer] = new_state[3]
        pointer += 1
        if pointer == 10:
            pointer, enough = 0, True
        state = new_state


        # for _ in range(T_horizon):
        #     # TODO: Use the mean and variance to create a normal distribution for multiple parameters
        #     #       and then sample from this distribution instead of from a discrete distribution
        #     # prob_a, prob_b = model.pi(torch.from_numpy(s).float())
        #     # m_a = Categorical(prob_a)
        #     # m_b = Categorical(prob_b)
        #     # a = m_a.sample().item()
        #     # b = m_b.sample().item()
        #     a, b, c, d, e, prob_a, prob_b, prob_c, prob_d, prob_e = select_action(s, model)
        #     # print(a, b, A_values[a].item(), B_values[b].item())
        #     batchSize = A_values[a].item()
        #     batchTimeout = B_values[b].item()
        #     checkpointInterval = C_values[c].item()
        #     watermarkWindowSize = D_values[d].item()
        #     segmentLength = E_values[e].item()
        #     with open("../parameters.yml", 'w') as file:
        #         file.write(f'BatchSize: {batchSize}\n')
        #         file.write(f'BatchTimeout: {batchTimeout}\n')
        #         file.write(f'CheckpointInterval: {checkpointInterval}\n')
        #         file.write(f'WatermarkWindowSize: {watermarkWindowSize}\n')
        #         file.write(f'EpochLength: {segmentLength * num_node}\n')
        #         file.write(f'SegmentLength: {segmentLength}\n')

        #     count += 1
        #     s_prime, state_prime, r = load_state_and_reward_from_file(c1, c2, c3, c4, count)
        #     print(count, [state[i] for i in range(10)], r, batchSize, batchTimeout, checkpointInterval, watermarkWindowSize, segmentLength)

        #     model.put_data((s, a, b, c, d, e, r, s_prime, prob_a[a].item(), prob_b[b].item(), prob_c[c].item(), prob_d[d].item(), prob_e[e].item()))
        #     s, state = s_prime, state_prime

        #     score += r

        # model.train_net()
        # cnt += 1

        # Save model and variables
        # checkpoint = {
        #     'model_state': model.state_dict(),
        #     'optimizer_state': model.optimizer.state_dict(),
        #     'cnt': cnt,
        #     'count': count,
        #     'totalLatency': totalLatency,
        #     'totalThroughput': totalThroughput
        # }
        # torch.save(checkpoint, model_path)
        # print("Saved checkpoint to {}".format(model_path))
        
        # print(f"# of episode :{cnt}, avg score : {score/1.0}", file="scores.txt")
        # scores.write(f'# of episode :{cnt}, avg score : {score/1.0}\n')
        # scores.flush()
        # print(score)
        # score = 0.0

class MetricsServiceServicer(monitor_pb2_grpc.MetricsServiceServicer):
    def SendMetrics(self, request, context):
        global received_msg, num_node, tmp_batchSize
        with all_received:
            print(f"Received request: Throughput={request.throughput}, Latency={request.latency}, "
                f"Requests={request.requests}, RequestsSize={request.requests_size}, "
                f"BatchSize={request.BatchSize}, BatchTimeout={request.BatchTimeout}, Leader={request.Leader}")
            received_msg += 1
            if request.requests[0] > 0:
                tmp_batchSize = request.BatchSize[0]
            if received_msg < num_node:
                all_received.wait()
            else:
                all_received.notify_all()
        
        response = monitor_pb2.MetricsResponse(
            BatchSize=tmp_batchSize,
            BatchTimeout=request.BatchTimeout[0]
        )
        return response

    def Connect(self, request, context):
        global connected_clients, start_time, num_node
        with all_clients_connected:
            connected_clients += 1
            if connected_clients == 1:
                start_time = request.timestamp + 5000000000
            if connected_clients == num_node:
                print("All nodes connected.")
                all_clients_connected.notify_all()
        response = monitor_pb2.Timestamp(
            timestamp=start_time
        )
        return response
    
def connection_test():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=num_node))
    monitor_pb2_grpc.add_MetricsServiceServicer_to_server(MetricsServiceServicer(), server)
    server.add_insecure_port('[::]:32767')
    server.start()
    print("Server started and waiting for clients to connect.")

    with all_clients_connected:
        all_clients_connected.wait()
    
    server.wait_for_termination()

if __name__ == '__main__':
    main()
    # connection_test()
