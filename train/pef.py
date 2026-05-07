import re

latency = 0
throughput = 0
tot = 0
noResTot = 0
lines = 10000

filepath = "./PPO/olddata/state"

for i in range(4):
    filename = filepath + str(i) + ".txt"
    with open(filename, 'r') as file:
        tmp = 0
        for line in file:
            tmp += 1
        lines = min(lines, tmp)
# print(lines)

for i in range(4):
    filename = filepath + str(i) + ".txt"
    with open(filename, 'r') as file:
        tmp = 0
        for line in file:
            tmp += 1
            if tmp > lines: break
            content = re.split(r'[ \t\n]+', line)[1:]
            if float(content[4]) < 1e3:
                latency += float(content[4])
            else: 
                noResTot += 1
            throughput += float(content[5])
            tot += 1

print("Average latency(ms): " + str(latency/(tot)))
print("Average throupught(r/s): " + str(throughput/lines))
print("The ratio of no quick response for requests sent by client: " + str(noResTot/tot))