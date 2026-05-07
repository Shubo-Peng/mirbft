class env():

    '''
    Questions: 
    1. 为什么throughput是101, requests是100?
    2. 单位是什么? 是每n秒统计一次的方式吗?
    3. 生成requests的逻辑和处理requests的逻辑分别是什么?
    现有的问题是我不知道这个系统处理一个单位的size的一个req要多久, 
    我只知道运行许多固定size的req的总时间(考虑了batchsize和timeout的影响)
    是不是甚至不需要模拟一个队列? 我直接把(req, size, bs, bt)当作一个四元组, 旧的直接输出, 新的就就近匹配??

    前一秒累积了很多，然后下一秒疯狂满足出块需求的话，这样算到1s的throughput里面？

    设置一个最小时间单位ns，以该单位进行累加
    '''
    
    def __init__(self, sendrate, bt, bs):
        # 用于记录batch内第一个req的进入时间，单位ns
        self.startTime = 0
        # 用于记录第一个req到了之后，过了多久，与timeout作对比，单位ns
        self.realTime = 0


        # client的发送req的速率，单位 个/s
        self.sendRate = sendrate
        # client发送req的大小，单位byte
        self.reqSize= 0

        # 队列的属性
        self.batchTimeout = bt
        self.batchSize = bs
        
        # 当前batch的req数
        self.currentBS = 0

        self.waitNum = 0

        # 每隔1s发布一次latency和throughput
        self.publishTime = 0
        self.throughput = 0
        self.latency = 0

    
    # sendrate的单位是 个/s，处理的时候time单位是ms
    def runTime(self):

        while(True):

            self.publishTime += 1
            self.realTime += 1

            # sendrate是每s发多少个req，现求每个req要多少ns
            delay = 1000000 // self.sendRate
            print("delay: ", delay)
            
            if self.realTime % delay == 0:
                self.currentBS += 1
            

            # 队列处理逻辑
            if self.currentBS < self.batchSize:
                if self.realTime - self.startTime > self.batchTimeout:
                    # self.throughtput表示当前s的吞吐量
                    self.throughput += self.currentBS
                    self.currentBS = 0
                    self.startTime = self.realTime
                else:
                    # wait
                    pass
            else:
                self.throughput += self.currentBS
                self.currentBS = 0
                self.startTime = self.realTime

            
            # 在动态变化咋整
            self.latency = self.latencyMap[(self.sendRate,self.reqSize,self.batchSize,self.batchTimeout)]

            # 假如1s内变更了多次request size怎么办？
            # 发布消息逻辑
            if self.publishTime >= 1000000:
                self.writeResult()
                self.publishTime = 0
                self.throughput = 0
                self.latency = 0

    
    def writeResult(self):
        with open('output.txt', 'w') as f:
            line = f"{self.throughput}\t{self.latency}\t{self.sendRate}\t{self.reqSize}\t{self.batchSize}\t{self.batchTimeout}\t{0}"
            print(line)
            f.write(line + '\n')
    
    def adjustParams(self, bt, bs):
        self.batchTimeout = bt
        self.batchSize = bs

    def adjustSendRate(self, sendrate):
        self.sendRate = sendrate
    
    def getLatency(self):
        # 查表，能否搞成实时的？
        latency = 0
        return latency


if __name__ == "__main__":
    en = env(1000,100,100)
    en.runTime()








