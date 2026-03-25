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
import statistics
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
c_thr, c_lat = 1, -4

requests = []
old_state = []
cnt = 0
score = 0
notify_counter = 0
max_notify_count = 36

global model, scores, metrics
model_path = "ppo_model_checkpoint.pth"

# MAX_EPISODE = 10000

# Discretization
# A_values = torch.linspace(-5, 5, 41)
A_values = torch.linspace(100, 7000, 70).int()
B_values = torch.linspace(100, 4000, 40).int() # BatchTimeout

num_node = 4
start_time, connected_clients, received_msg = 0, 0, 0
all_clients_connected, all_received = threading.Condition(), threading.Condition()
received_msg_lock = threading.Lock()

class PPO(nn.Module):
    def __init__(self):
        super(PPO, self).__init__()
        self.data = []
        hidden_dims = 256
        self.fc1 = nn.Linear(7, hidden_dims)
        self.fc_pi_a = nn.Linear(hidden_dims, 70)
        self.fc2 = nn.Linear(hidden_dims + 70, hidden_dims)
        self.fc_pi_b = nn.Linear(hidden_dims, 40)
        self.fc_v = nn.Linear(hidden_dims, 1)  # Value output
        self.optimizer = optim.Adam(self.parameters(), lr=learning_rate)
        # self.initialize_uniform_probabilities()

    def initialize_uniform_probabilities(self):
        # Initialize the final layers to produce uniform probabilities
        nn.init.constant_(self.fc_pi_a.weight, 0)
        nn.init.constant_(self.fc_pi_a.bias, 0)
        nn.init.constant_(self.fc_pi_b.weight, 0)
        nn.init.constant_(self.fc_pi_b.bias, 0)

    def pi(self, x, softmax_dim=-1):
        x = F.relu(self.fc1(x))
        prob_a = F.softmax(self.fc_pi_a(x), dim=softmax_dim)
        x = torch.cat((x, prob_a), dim=-1)
        x = F.relu(self.fc2(x))
        prob_b = F.softmax(self.fc_pi_b(x), dim=softmax_dim)
        return prob_a, prob_b

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
        s_lst, a_lst, b_lst, r_lst, s_prime_lst, prob_a_lst, prob_b_lst= [], [], [], [], [], [], []
        for transition in self.data:
            s, a, b, r, s_prime, prob_a, prob_b = transition
            s_lst.append(s)
            a_lst.append([a])
            b_lst.append([b])
            r_lst.append([r])
            s_prime_lst.append(s_prime)
            prob_a_lst.append([prob_a])
            prob_b_lst.append([prob_b])

        s = np.array(s)
        s, a, b, r = torch.tensor(np.array(s_lst), dtype=torch.float), torch.tensor(np.array(a_lst)), torch.tensor(np.array(b_lst)), torch.tensor(r_lst)
        s_prime, prob_a, prob_b = torch.tensor(np.array(s_prime_lst), dtype=torch.float), torch.tensor(np.array(prob_a_lst)), torch.tensor(np.array(prob_b_lst))
        self.data = []
        return s, a, b, r, s_prime, prob_a, prob_b
    
    def train_net(self):
        s, a, b, r, s_prime, prob_a, prob_b = self.make_batch()
        # print(prob_a, prob_b)

        for i in range(K_epoch):
            td_target = r + gamma * self.v(s_prime)
            delta = (td_target - self.v(s)).detach().numpy()

            advantage_lst, advantage = [], 0.0
            for delta_t in delta[::-1]:
                advantage = gamma * lmbda * advantage + delta_t[0]
                advantage_lst.append([advantage])
            advantage_lst.reverse()
            advantage = torch.tensor(np.array(advantage_lst), dtype=torch.float)

            pi_a, pi_b = self.pi(s)
            # print("train net", pi_a, pi_b)
            pi_a, pi_b = pi_a.gather(1, a), pi_b.gather(1, b)
            # print("gather", pi_a, pi_b)
            pi_ab, prob_ab = pi_a * pi_b, prob_a * prob_b
            # print(pi_ab, prob_ab)

            ratio = torch.exp(torch.log(pi_ab) - torch.log(prob_ab))

            surr1 = ratio * advantage
            surr2 = torch.clamp(ratio, 1-eps_clip, 1+eps_clip) * advantage
            loss = -torch.min(surr1, surr2) + F.smooth_l1_loss(self.v(s), td_target.detach())

            self.optimizer.zero_grad()
            loss.mean().backward()
            self.optimizer.step()

    def select_action(self, s):
        prob_a, prob_b = self.pi(torch.from_numpy(s).float())
        # print(prob_a, prob_b)
        m_a = Categorical(prob_a)
        m_b = Categorical(prob_b)
        a = m_a.sample().item()
        b = m_b.sample().item()
        return a, b

class MetricsServiceServicer(monitor_pb2_grpc.MetricsServiceServicer):
    def SendMetrics(self, request, context):
        global received_msg, num_node, requests, batchSize, batchTimeout
        with all_received:
            print(f"Received request: Throughput={request.throughput}, Latency={request.latency}, "
                f"Requests={request.requests}, RequestsSize={request.requests_size}, "
                f"BatchSize={request.BatchSize}, BatchTimeout={request.BatchTimeout}, Leader={request.Leader}")
            with received_msg_lock:
                received_msg += 1
            requests.append(request)
            if request.Leader[-1]%100 > 0:
                batchSize = int(request.BatchSize[-1])
                batchTimeout = request.BatchTimeout[-1]
            if received_msg < num_node:
                all_received.wait()
            else:
                received_msg = 0
                notify_counter += 1
                if notify_counter > max_notify_count:
                    print("One cycle completed. Quit running.")
                    os._exit(0)
                batchSize, batchTimeout = modelUpdate(batchSize, batchTimeout, False)
                all_received.notify_all()
        
        response = monitor_pb2.MetricsResponse(
            BatchSize=batchSize,
            BatchTimeout=batchTimeout
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
    
def getLength(requests):
    length = []
    for req in requests:
        length.append(len(req.throughput))
    print(length)
    return min(length)

def handleMetrics(requests, length):
    global metrics
    thr, lat, rqs, size, BS, BT, lead = [], [], [], [], [], [], []
    for i in range(length):
        tmp_thr, tmp_lat, tmp_rqs, tmp_size, tmp_BS, tmp_BT, tmp_lead = [], [], [], [], [], [], []
        for j in range(4):
            tmp_thr.append(requests[j].throughput[i])
            tmp_lat.append(requests[j].latency[i] * requests[j].throughput[i])
            tmp_rqs.append(requests[j].requests[i])
            tmp_size.append(requests[j].requests_size[i])
            tmp_BS.append(requests[j].BatchSize[i])
            tmp_BT.append(requests[j].BatchTimeout[i])
            tmp_lead.append(int(requests[j].Leader[i]/100))
        thr.append(sum(tmp_thr))
        if thr[-1] != 0:
            lat.append(sum(tmp_lat)/sum(tmp_thr))
        else: lat.append(sum(tmp_lat))
        rqs.append(sum(tmp_rqs))
        size.append(sum(tmp_size)/1000)
        BS.append(statistics.mode(tmp_BS))
        BT.append(statistics.mode(tmp_BT))
        lead.append(statistics.mode(tmp_lead))
        metrics.write('{:8d}\t{:8.2f}\t{:8d}\t{:8.2f}\t{:8d}\t{:8d}\t{:8d}\n'.format(thr[-1], lat[-1], rqs[-1], size[-1], BS[-1], BT[-1], lead[-1]))
        metrics.flush()
    return thr, lat, rqs, size, BS, BT, lead

def Normalized(state):
    return (state - np.mean(state, axis=0)) / np.std(state, axis=0)

def modelUpdate(batchsize, batchtimeout, flag):
    global model, scores, cnt, requests, old_state, score
    # score = 0
    length = getLength(requests)
    thr, lat, rqs, size, BS, BT, lead = handleMetrics(requests, length)
    requests = []

    if not flag:
        return batchsize, batchtimeout

    if len(old_state) == 0:
        old_state = np.array([thr[0], lat[0], rqs[0], size[0], BS[0], BT[0], lead[0]])
        thr, lat, rqs, size, BS, BT, lead = thr[1:], lat[1:], rqs[1:], size[1:], BS[1:], BT[1:], lead[1:]
        length -= 1
    
    for i in range(length):
        new_state = np.array([thr[i], lat[i], rqs[i], size[i], BS[i], BT[i], lead[i]])

        prob_a, prob_b = model.pi(torch.from_numpy(Normalized(old_state)).float())
        # print("model update", i, prob_a)

        # a = (torch.abs(A_values - math.log2(BS[i]/old_state[4]))).argmin().item()
        a = (torch.abs(A_values - BS[i])).argmin().item()
        b = (torch.abs(B_values - BT[i])).argmin().item()
        # print(a,b,A_values[a].item(),B_values[b].item())

        reward = c_thr * old_state[0] + c_lat * old_state[1]
        if reward == 0 : reward = -40000
        model.put_data((Normalized(old_state), a, b, reward/40000, Normalized(new_state), prob_a[a].item(), prob_b[b].item()))

        score, old_state = score+reward/40000, new_state

    # if length > 0:
    if len(model.data) >= T_horizon:
        model.train_net()
        cnt += 1
        scores.write(f'# of episode :{cnt}, score : {score/1.0}\n')
        scores.flush()
        print("score =",score, old_state)
        score = 0
        checkpoint = {
            'model_state': model.state_dict(),
            'optimizer_state': model.optimizer.state_dict()
        }
        torch.save(checkpoint, model_path)
        print("Saved checkpoint to {}".format(model_path))

    bs, bt = model.select_action(Normalized(old_state))
    # bs, bt = math.ceil(old_state[4] * (2**A_values[bs].item())), B_values[bt].item()
    bs, bt = A_values[bs].item(), B_values[bt].item()
    # print("bs =", int(bs), "bt =", bt)
    return int(bs), bt

    
def main():
    global model, scores, metrics
    model = PPO()
    scores = open("scores.txt",'w')
    metrics = open("metrics.txt",'w')

    if os.path.exists(model_path):
        checkpoint = torch.load(model_path)
        model.load_state_dict(checkpoint['model_state'])
        model.optimizer.load_state_dict(checkpoint['optimizer_state'])
        print("Loaded checkpoint from {}".format(model_path))

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
