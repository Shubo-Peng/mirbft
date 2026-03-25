import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
from concurrent import futures
import grpc
import threading
import time
import os
import copy

import metrics_pb2 as monitor_pb2
import metrics_pb2_grpc as monitor_pb2_grpc

# === Hyperparameters ===
inner_lr = 0.01         # Task-specific learning rate
meta_lr = 0.001         # Meta update learning rate
inner_steps = 1         # Gradient steps in task
meta_batch_size = 5     # Number of tasks per meta update
T_horizon = 5
gamma = 0.98
lmbda = 0.95
c_thr, c_lat = 1, -4
num_node = 12

# === Discretization ===
A_values = torch.arange(-num_node, num_node+1, 1)
B_values = torch.arange(-128, 129, 4)
C_values = torch.arange(-60000, 60001, 1000)

# === Model ===
class PPO(nn.Module):
    def __init__(self):
        super(PPO, self).__init__()
        self.fc1 = nn.Linear(6, 64)
        self.fc_pi_a = nn.Linear(64, len(A_values))
        self.fc_pi_b = nn.Linear(64, len(B_values))
        self.fc_pi_c = nn.Linear(64, len(C_values))
        self.fc_v = nn.Linear(64, 1)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        return x

    def pi(self, x):
        x = self.forward(x)
        prob_a = F.softmax(self.fc_pi_a(x), dim=-1)
        prob_b = F.softmax(self.fc_pi_b(x), dim=-1)
        prob_c = F.softmax(self.fc_pi_c(x), dim=-1)
        return prob_a, prob_b, prob_c

    def v(self, x):
        x = self.forward(x)
        return self.fc_v(x)
    
    def select_action(self, s):
        prob_a, prob_b, prob_c = self.pi(torch.from_numpy(s).float())
        a = torch.argmax(prob_a).item()
        b = torch.argmax(prob_b).item()
        c = torch.argmax(prob_c).item()
        return a, b, c

def Normalized(state):
    return (state - np.mean(state)) / (np.std(state) + 1e-6)

# === Meta learner ===
meta_model = PPO()
meta_optimizer = optim.Adam(meta_model.parameters(), lr=meta_lr)
lock, model_update_lock = threading.Lock(), threading.Lock()
task_buffer = []

# === Load Model ===
model_path = "meta_model_checkpoint.pth"
if os.path.exists(model_path):
    checkpoint = torch.load(model_path)
    meta_model.load_state_dict(checkpoint['model_state'])

# === FOMAML Training ===
def fomaml_task_train(task_state_buffer, task_id):
    model = copy.deepcopy(meta_model)
    optimizer = optim.SGD(model.parameters(), lr=inner_lr)

    for step in range(inner_steps):
        loss = compute_loss(model, task_state_buffer)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    return model

def compute_loss(model, buffer):
    s, r, a_idx, b_idx, c_idx, prob_a, prob_b, prob_c, s_prime = zip(*buffer)

    s = torch.tensor(s, dtype=torch.float)
    r = torch.tensor(r, dtype=torch.float).unsqueeze(1)
    s_prime = torch.tensor(s_prime, dtype=torch.float)

    td_target = r + gamma * model.v(s_prime)
    delta = td_target - model.v(s)
    advantage = delta.detach()

    pi_a, pi_b, pi_c = model.pi(s)
    pi_a = pi_a.gather(1, torch.tensor(a_idx).unsqueeze(1))
    pi_b = pi_b.gather(1, torch.tensor(b_idx).unsqueeze(1))
    pi_c = pi_c.gather(1, torch.tensor(c_idx).unsqueeze(1))

    ratio = torch.log(pi_a + 1e-8) + torch.log(pi_b + 1e-8) + torch.log(pi_c + 1e-8) - \
            torch.log(torch.tensor(prob_a).unsqueeze(1) + 1e-8) - \
            torch.log(torch.tensor(prob_b).unsqueeze(1) + 1e-8) - \
            torch.log(torch.tensor(prob_c).unsqueeze(1) + 1e-8)

    loss = -(ratio * advantage).mean()
    return loss

def update_meta_model(models):
    meta_grads = [torch.zeros_like(p) for p in meta_model.parameters()]
    for model in models:
        for idx, p in enumerate(model.parameters()):
            meta_grads[idx] += p.data - list(meta_model.parameters())[idx].data

    for p, g in zip(meta_model.parameters(), meta_grads):
        p.data += meta_lr * g / len(models)

# === gRPC Handler ===
class MetricsServiceServicer(monitor_pb2_grpc.MetricsServiceServicer):
    def __init__(self):
        self.task_states = {}
        self.task_models = {}
        self.task_counters = {}

    def SendMetrics(self, request, context):
        if num_node not in self.task_states:
            self.task_states[num_node] = []

        state = np.array([request.throughput, request.latency, request.requests, request.Instance, request.Epoch, request.ViewTimeout])
        reward = c_thr * request.throughput + c_lat * request.latency
        norm_state = Normalized(state)

        with torch.no_grad():
            prob_a, prob_b, prob_c = meta_model.pi(torch.tensor(norm_state).float())
            a = torch.argmax(prob_a).item()
            b = torch.argmax(prob_b).item()
            c = torch.argmax(prob_c).item()

        self.task_states[num_node].append((norm_state, reward/40000, a, b, c, prob_a[a].item(), prob_b[b].item(), prob_c[c].item(), norm_state))

        if len(self.task_states[num_node]) >= T_horizon:
            with lock:
                task_buffer.append((num_node, self.task_states[num_node][:]))
                self.task_states[num_node] = []

        if len(task_buffer) >= meta_batch_size:
            with lock:
                print("[Meta] Running FOMAML meta-update")
                adapted_models = [fomaml_task_train(buf, tid) for tid, buf in task_buffer[:meta_batch_size]]
                update_meta_model(adapted_models)
                torch.save({'model_state': meta_model.state_dict()}, 'meta_model_checkpoint.pth')
                task_buffer.clear()

        # Return dummy response
        with model_update_lock:
            state = np.array([
                request.throughput,
                request.latency,
                request.requests,
                request.Instance,
                request.Epoch,
                request.ViewTimeout
            ])
            # 推理获取动作
            instance_delta, epoch_delta, viewtimeout_delta = meta_model.select_action(Normalized(state))
            
            # 加上原来的参数得到新的建议值
            instance = int(np.clip(request.Instance + instance_delta, 1, num_node))
            epoch = int(np.clip(request.Epoch + epoch_delta, 16, 256))
            viewtimeout = int(np.clip(request.ViewTimeout + viewtimeout_delta, 30000, 120000))

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
    print("[Server] Meta-Learning Server Started on Port 45678")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
