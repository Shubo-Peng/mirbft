import psutil
import time

def monitor_memory(interval=1):
    file = open("time.txt", "w")
    cnt = 0
    while True:
        memory = psutil.virtual_memory()
        total = memory.total
        used = memory.used
        free = memory.free
        percent = memory.percent

        print(f"Total: {total} bytes, Used: {used} bytes, Free: {free} bytes, Percent: {percent}%")
        cnt += 1
        file.write(f'Total: {total} bytes, Used: {used} bytes, Free: {free} bytes, Percent: {percent}%, Count: {cnt}\n')
        file.flush()
        time.sleep(interval)

if __name__ == "__main__":
    monitor_memory()
