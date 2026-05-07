import time

def get_time_from_table(total_batch_size):
    # 或许可以提前读成一个字典
    return 100 #ns

class req_sys:

    def __init__(self, batch_size, batch_timeout,request_size,send_rate):
        self.cur_time = 0 # ns
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout #单位是ns
        self.set_input(request_size,send_rate)
        self.latency = 0
        self.throughput = 0
        self.show_freq = 1000000 #每多少ns输出一次latency和throughput
        self.batch_start_time = 0 #用来记录一个batch被清空的起始时间
        self.req_cnt = 0 # 用来统计每个show_freq内有多少request
        self.batch = []
    
    # 用来切换
    def set_input(self,request_size,send_rate):
        self.req_size = request_size
        self.send_rate = send_rate #单位是 个/s
        self.msg_feq = 1000000//self.send_rate #单位是 ns/个  

    def generate_request(self):
        while True:
            # print(self.cur_time,self.msg_feq)
            # break
            self.cur_time += 1

            if self.cur_time%self.msg_feq==0:
                self.batch.append((self.req_size,self.cur_time))
                self.req_cnt += 1
            
            # 过去了1ns

            if len(self.batch) < self.batch_size:
                if self.cur_time < self.batch_timeout:
                    pass
                else:
                    self.publish_batch()
            else:
                self.publish_batch()
            
            if self.cur_time%self.show_freq==0:
                # print(self.cur_time)
                self.show_result()
            
    def publish_batch(self):

        total_timestamp = sum(item[1] for item in self.batch)
        total_byte = sum(item[0] for item in self.batch)

        process_time = get_time_from_table(total_byte) - self.batch_start_time
        if len(self.batch) != 0:
            wait_time = total_timestamp / len(self.batch)
        else:
            wait_time = 0

        self.latency = process_time + wait_time
        self.throughput += total_byte

        # reset batch params
        self.batch_start_time = self.cur_time
        self.req_cnt += len(self.batch)
        self.batch = []

    def show_result(self):
        latency = self.latency
        throughput = self.throughput
        req_cnt = self.req_cnt
        self.latency = 0
        self.throughput = 0
        self.req_cnt = 0

        # latency的单位是ms
        print(throughput, latency/1000, req_cnt, self.req_size, self.batch_size, self.batch_timeout)

def main():
    # batch_timeout单位是ms
    sys = req_sys(batch_size=1000,batch_timeout=100000000000,request_size=10,send_rate=50)
    sys.generate_request()

if __name__ == "__main__":
    main()



