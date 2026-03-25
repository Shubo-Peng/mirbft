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
import metrics_pb2 as monitor_pb2
import metrics_pb2_grpc as monitor_pb2_grpc

# Hyperparameters
learning_rate = 0.0005
gamma = 0.98
lmbda = 0.98
eps_clip = 0.1
K_epoch = 3
T_horizon = 5
c_thr, c_lat = 1, -4

num_node = 4
requests = []
old_state = []
cnt = 0
score = 0
notify_counter = 0
max_notify_count = 36

A_values = torch.arange(-num_node, num_node+1, 1)
B_values = torch.arange(-128, 129, 4)
C_values = torch.arange(-60000, 60001, 1000)
lastA, lastB, lastC = 0, 0, 0

global model, scores, metrics
model_path = "ppo_model_checkpoint.pth"

# MAX_EPISODE = 10000

start_time, connected_clients, received_msg = 0, 0, 0
all_clients_connected, all_received = threading.Condition(), threading.Condition()
model_update_lock = threading.Lock()

class PPO(nn.Module):
    def __init__(self):
        super(PPO, self).__init__()
        self.data = []

        input_dims = 6
        hidden_dims = 64

        self.fc1 = nn.Linear(input_dims, hidden_dims)
        self.fc_pi_a = nn.Linear(hidden_dims, len(A_values))
        self.fc_pi_b = nn.Linear(hidden_dims, len(B_values))
        self.fc_pi_c = nn.Linear(hidden_dims, len(C_values))
        self.fc_v = nn.Linear(hidden_dims, 1)

        self.optimizer = optim.Adam(self.parameters(), lr=learning_rate)

    def pi(self, x, softmax_dim=-1):
        x = F.relu(self.fc1(x))
        prob_a = F.softmax(self.fc_pi_a(x), dim=softmax_dim)
        prob_b = F.softmax(self.fc_pi_b(x), dim=softmax_dim)
        prob_c = F.softmax(self.fc_pi_c(x), dim=softmax_dim)
        return prob_a, prob_b, prob_c

    def v(self, x):
        x = F.relu(self.fc1(x))
        return self.fc_v(x)

    def put_data(self, transition):
        self.data.append(transition)
    def make_batch(self):
        s_lst, a_lst, b_lst, c_lst, r_lst, s_prime_lst, prob_a_lst, prob_b_lst, prob_c_lst = [], [], [], [], [], [], [], [], []

        for transition in self.data:
            s, a, b, c, r, s_prime, p_a, p_b, p_c = transition
            s_lst.append(s)
            a_lst.append([a])
            b_lst.append([b])
            c_lst.append([c])
            r_lst.append([r])
            s_prime_lst.append(s_prime)
            prob_a_lst.append([p_a])
            prob_b_lst.append([p_b])
            prob_c_lst.append([p_c])

        s, a, b, c, r = torch.tensor(np.array(s_lst), dtype=torch.float), torch.tensor(np.array(a_lst)), torch.tensor(np.array(b_lst)), torch.tensor(np.array(c_lst)), torch.tensor(np.array(r_lst))
        s_prime, prob_a, prob_b, prob_c = torch.tensor(np.array(s_prime_lst), dtype=torch.float), torch.tensor(np.array(prob_a_lst)), torch.tensor(np.array(prob_b_lst)), torch.tensor(np.array(prob_c_lst))
        self.data = []
        return s, a, b, c, r, s_prime, prob_a, prob_b, prob_c
    
    def train_net(self):
        s, a, b, c, r, s_prime, prob_a, prob_b, prob_c = self.make_batch()
        for i in range(K_epoch):
            td_target = r + gamma * self.v(s_prime)
            delta = td_target - self.v(s)
            delta = delta.detach().numpy()

            advantage_lst = []
            advantage = 0.0
            for delta_t in delta[::-1]:
                advantage = gamma * lmbda * advantage + delta_t[0]
                advantage_lst.append([advantage])
            advantage_lst.reverse()
            advantage = torch.tensor(advantage_lst, dtype=torch.float)

            pi_a, pi_b, pi_c = self.pi(s, softmax_dim=1)
            pi_a, pi_b, pi_c = pi_a.gather(1, a), pi_b.gather(1, b), pi_c.gather(1, c)
            ratio_a = torch.exp(torch.log(pi_a) - torch.log(prob_a))
            ratio_b = torch.exp(torch.log(pi_b) - torch.log(prob_b))
            ratio_c = torch.exp(torch.log(pi_c) - torch.log(prob_c))

            surr1 = ratio_a*advantage + ratio_b*advantage + ratio_c*advantage
            surr2 = torch.clamp(ratio_a, 1 - eps_clip, 1 + eps_clip) * advantage + \
                    torch.clamp(ratio_b, 1 - eps_clip, 1 + eps_clip) * advantage + \
                    torch.clamp(ratio_c, 1 - eps_clip, 1 + eps_clip) * advantage
            loss = -torch.min(surr1, surr2).mean() + F.smooth_l1_loss(self.v(s), td_target.detach())

            self.optimizer.zero_grad()
            loss.mean().backward()
            self.optimizer.step()

    def select_action(self, s):
        prob_a, prob_b, prob_c = self.pi(torch.from_numpy(s).float())
        a = torch.argmax(prob_a).item()
        b = torch.argmax(prob_b).item()
        c = torch.argmax(prob_c).item()
        return a, b, c

model = PPO()
if os.path.exists(model_path):
    checkpoint = torch.load(model_path)
    model.load_state_dict(checkpoint['model_state'])
    model.optimizer.load_state_dict(checkpoint['optimizer_state'])
    
def Normalized(state):
    return (state - np.mean(state, axis=0)) / np.std(state, axis=0)

def modelUpdate(batch_state):
    global model, cnt, old_state, score, lastA, lastB, lastC
    print(batch_state)
    
    if len(old_state) != 0:
        reward = c_thr * old_state[0] + c_lat * old_state[1]

        norm_state = Normalized(old_state)
        prob_a, prob_b, prob_c = model.pi(torch.from_numpy(norm_state).float())
        a = (torch.abs(A_values - lastA)).argmin().item();
        b = (torch.abs(B_values - lastB)).argmin().item();
        c = (torch.abs(C_values - lastC)).argmin().item();
    
        model.put_data((norm_state, a, b, c, reward / 40000, Normalized(batch_state),
                        prob_a[a].item(), prob_b[b].item(), prob_c[c].item()))

    if len(model.data) >= T_horizon:
        model.train_net()
        cnt += 1
        score = 0
        torch.save({
            'model_state': model.state_dict(),
            'optimizer_state': model.optimizer.state_dict()
        }, model_path)

    old_state = batch_state
    a, b, c = model.select_action(Normalized(old_state))
    lastA, lastB, lastC = A_values[a].item(), B_values[b].item(), C_values[c].item()
    return lastA, lastB, lastC

class MetricsServiceServicer(monitor_pb2_grpc.MetricsServiceServicer):
    def SendMetrics(self, request, context):
        global received_msg, num_node
        
        # 加锁开始
        with model_update_lock:
            new_state = np.array([
                request.throughput, 
                request.latency, 
                request.requests,
                request.Instance, 
                request.Epoch, 
                request.ViewTimeout
            ])
            
            start = time.perf_counter()
            
            instance, epoch, viewtimeout = modelUpdate(new_state)
            instance = int(np.clip(request.Instance + instance, 1, num_node))
            epoch = int(np.clip(request.Epoch + epoch, 16, 256))
            viewtimeout = int(np.clip(request.ViewTimeout + viewtimeout, 30000, 120000))
            print(instance, epoch, viewtimeout)
            
            end = time.perf_counter()
            print(f"代码运行时间: {end - start:.6f} 秒")
            
        # 锁自动释放（退出 with 块）
        return monitor_pb2.MetricsResponse(
            Instance=instance,
            Epoch=epoch,
            ViewTimeout=viewtimeout
        )

    
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    monitor_pb2_grpc.add_MetricsServiceServicer_to_server(MetricsServiceServicer(), server)
    server.add_insecure_port('[::]:45678')
    server.start()
    print("Server started on port 45678.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
