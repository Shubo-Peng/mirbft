import re

latency = 0
throughput = 0
tot = 0
noResTot = 0

for i in range(4):
    filename = "state" + str(i) + ".txt"
    with open(filename, 'r') as file:
        for line in file:
            content = re.split(r'[ \t\n]+', line)[1:]
            if float(content[2]) < 1e5:
                latency += float(content[2])
            else: noResTot += 1
            throughput += float(content[3])
            tot += 1

print("Average latency(ms): " + str(latency/tot))
print("Average throupught(r/s): " + str(throughput/tot))
print("The ratio of no quick response for requests sent by client: " + str(noResTot/tot))