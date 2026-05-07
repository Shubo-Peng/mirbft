import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
from collections import deque
import time
import os
import re
import math

# actions = torch.tensor([[128], [256], [512], [1024], [1536], [2048], [3072], [4096]], dtype=torch.long)
batch_sizes = [128, 256, 512, 1024, 1536, 2048, 3072, 4096]
batch_timeouts = [1000, 2000, 4000]
actions = [torch.tensor([batch_size, batch_timeout], dtype=torch.long) for batch_size in batch_sizes for batch_timeout in batch_timeouts]
proposedRequests = [0, 0, 0, 0]
totalPayload = [0, 0, 0, 0]
latency = [0, 0, 0, 0]
throughput = [0, 0, 0, 0]
CPUload = [0, 0, 0, 0]
CPUsystem = [0, 0, 0, 0]
baseline = 1000

class DQN(nn.Module):
    def __init__(self, input_size, output_size):
        super(DQN, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 36),
            nn.ReLU(),
            nn.Linear(36, 36),
            nn.ReLU(),
            nn.Linear(36, output_size)
        )
    
    def forward(self, x):
        return self.network(x)

# def select_action(state, model, epsilon, steps):
#     global actions
#     if steps == 0:
#         return actions[3], 3
#     sample = random.random()
#     if sample > epsilon:
#         with torch.no_grad():
#             action = model(state.unsqueeze(0)).max(1)[1].item()
#     else:
#         action = random.randrange(len(actions))
#     return actions[action].view(1, 1), action

def select_action(state, model, epsilon, steps):
    global actions
    if steps == 0:
        # 默认选取第一个action组合，即第一个batch_size和第一个batch_timeout的组合
        return actions[11].view(1, -1), 11
    sample = random.random()
    if sample > epsilon:
        with torch.no_grad():
            action = model(state.unsqueeze(0)).max(1)[1].item()
    else:
        action = random.randrange(len(actions))
    return actions[action].view(1, -1), action

class ReplayBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state):
        self.buffer.append((state, action, reward, next_state))
    
    def sample(self, batch_size):
        return random.sample(self.buffer, batch_size)
    
    def __len__(self):
        return len(self.buffer)

def optimize_model(model, target_model, memory, optimizer, batch_size, gamma, losses):
    if len(memory) < batch_size:
        return

    transitions = memory.sample(batch_size)
    batch_state, batch_action, batch_reward, batch_next_state = zip(*transitions)

    batch_state = torch.stack(batch_state)
    batch_action = torch.tensor(batch_action, dtype=torch.long).view(-1, 1)
    batch_reward = torch.tensor(batch_reward, dtype=torch.float)
    batch_next_state = torch.stack(batch_next_state)
    # print(batch_state, batch_action, batch_reward, batch_next_state)

    q_values = model(batch_state)  # 假设batch_state是正确的形状
    # print(q_values.shape)  # 应该打印出 [batch_size, num_actions]
    current_q_values = q_values.gather(1, batch_action)
    max_next_q_values = target_model(batch_next_state).detach().max(1)[0]
    expected_q_values = batch_reward + (gamma * max_next_q_values)

    loss = nn.MSELoss()(current_q_values, expected_q_values.unsqueeze(-1))
    # print(current_q_values, expected_q_values)

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    losses.append(loss.item())
    return np.mean(losses[-100:])  # 返回最近100个损失的平均值

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

def load_state_and_reward_from_file(c1, c2):
    global proposedRequests, totalPayload, latency, throughput, CPUload, CPUsystem
    for i in range(4):
        while True:
            filePath = "../state" + str(i) + ".txt"
            content = re.split(r'[ \t\n]+', read_last_line(filePath))[1:]
            if len(content[0]) and len(content[1]) and len(content[2]) and len(content[3]):
                if int(content[0]) == proposedRequests[i] and float(content[1]) == totalPayload[i] and \
                math.fabs(float(content[2]) - latency[i]) < 1e-6 and math.fabs(float(content[3]) - throughput[i]) < 1e-6 and int(content[4]) == CPUload[i] and int(content[5]) == CPUsystem[i]:
                    time.sleep(0.001)
                    continue
                proposedRequests[i], totalPayload[i], latency[i], throughput[i], CPUload[i], CPUsystem[i] = \
                int(content[0]), float(content[1]), float(content[2]), float(content[3]), int(content[4]), int(content[5])
                break
    a, b, c, d, e, f = sum(proposedRequests), sum(totalPayload), sum(latency)/4, sum(throughput), sum(CPUload)/4, sum(CPUsystem)/4
    state = np.array([a, b, c, d, e, f], dtype=np.float32)
    # Normalize state
    state = (state - np.mean(state, axis=0)) / np.std(state, axis=0)
    reward = c1 * c + c2 * d

    return torch.FloatTensor(state), reward

def save_checkpoint(state, filename='checkpoint.pth'):
    torch.save(state, filename)

def load_checkpoint(model, optimizer, memory, filename='checkpoint.pth'):
    if os.path.isfile(filename):
        checkpoint = torch.load(filename)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        memory.buffer = checkpoint['replay_buffer']
        print("Checkpoint loaded successfully.")
        return checkpoint['losses']
    else:
        print("No checkpoint file found, starting with a fresh model and buffer.")
        return []

def main():
    input_size = 6
    output_size = 24
    batch_size = 16
    gamma = 0.99
    learning_rate = 0.001
    memory_size = 10000
    epsilon_start = 0.9
    epsilon_end = 0.05
    epsilon_decay = 200
    steps_done = 0
    c1 = -1
    c2 = 1
    losses = []

    global actions
    # print(actions[20])
    
    model = DQN(input_size, output_size)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    memory = ReplayBuffer(memory_size)
    losses = load_checkpoint(model, optimizer, memory)

    target_model = DQN(input_size, output_size)
    target_model.load_state_dict(model.state_dict())

    state, _ = load_state_and_reward_from_file(c1, c2)

    while True:
        # Update epsilon
        epsilon = epsilon_end + (epsilon_start - epsilon_end) * \
            math.exp(-1. * steps_done / epsilon_decay)
        
        action, id = select_action(state, model, epsilon, steps_done)
        # action_value = action.item()
        batch_size_value = action[0, 0].item()  # 获取批处理大小
        batch_timeout_value = action[0, 1].item()
        print(state, batch_size_value, batch_timeout_value)
        with open("../parameters.yml", 'w') as file:
            file.write(f'BatchSize: {batch_size_value}\n')
            file.write(f'BatchTimeout: {batch_timeout_value}\n')
        
        next_state, reward = load_state_and_reward_from_file(c1, c2)
        memory.push(state, id, reward, next_state)

        if len(memory) > batch_size:
            avg_loss = optimize_model(model, target_model, memory, optimizer, batch_size, gamma, losses)
            if avg_loss:
                print(f"Average Loss: {avg_loss:.6f}")
            target_model.load_state_dict(model.state_dict())
            with open("losses.txt", "w") as file:
                # for loss in losses:
                file.write(f'{losses}\n')
        
        steps_done += 1
        state = next_state

        # if steps_done % 100 == 0:
        save_checkpoint({
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'replay_buffer': memory.buffer,
            'losses': losses
        })
        print("Checkpoint saved successfully.")

if __name__ == "__main__":
    main()
