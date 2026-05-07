file1 = "./tuning-10-dyn/state"
file2 = "../state"

for i in range(10):
    lines = []
    filename = file1 + str(i) + ".txt"
    with open(filename, 'r') as file:
        # tmp = 0
        for line in file:
            if line[-1] != '\n':
                line = line + '\n'
            lines.append(line)
            # tmp += 1
            # if tmp >= 333:
            #     break
    filename = file2 + str(i) + ".txt"
    with open(filename, 'r') as file:
        tmp = 0
        for line in file:
            tmp += 1
            # if tmp <= 2:
            #     continue
            if tmp >= 333:
                break
            lines.append(line)
    print(len(lines))
    filename = file1 + str(i) + "_1.txt"
    with open(filename, 'w') as file:
        for line in lines:
            file.write(line)
