import os
import re

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

last_line = read_last_line('state2.txt')
list = re.split(r'[ \t\n]+', last_line)
print(float(list[1]), float(list[2]))
