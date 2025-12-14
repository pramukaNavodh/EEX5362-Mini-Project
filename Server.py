import simpy
import random
import statistics
import matplotlib.pyplot as plt

#conf -server
RAM = 8
CPU = 4
PORT_MBPS = 100
STORAGE = 75

#conf -clients
UPLOAD_CLIENTS = 300 #considered mqtt through uploads from the client
UPLOAD_PACKET_SIZE = 500
UPLOAD_RATE = 0.2

DOWNLOAD_CLIENTS = 50 #considered REST through downloads from the server
DOWNLOAD_PACKET_SIZE = 50
DOWNLOAD_RATE = 1

SIMULATION_TIME = 500 # s

#params
BITS_PER_BYTE = 8
MBPS_TO_BPS = 1_000_000
PORT_BPS = PORT_MBPS * MBPS_TO_BPS #port bps = portmbps*1000000

UPLOAD_PACKET_BITS = UPLOAD_PACKET_SIZE * 1024 * BITS_PER_BYTE
DOWNLOAD_PACKET_BITS = DOWNLOAD_PACKET_SIZE * 1024 * BITS_PER_BYTE

CPU_SERVICE_TIME = 0.001 # 1 ms - bline process time

response_times = []
utilization_times = []
throughput_times = []
concurrency_times = []
time_points = []

#sim -server
def server(env, cpu, network, packet_bits, response_times):
    arrival_time = env.now # network - limited bandwidt
    with network.request() as net_req:
        yield net_req
        transmission_time = packet_bits / PORT_BPS
        yield env.timeout(transmission_time)
    # cpu process
    with cpu.request() as cpu_req:
        yield cpu_req
        yield env.timeout(random.expovariate(1 / CPU_SERVICE_TIME))
    response_times.append(env.now - arrival_time)

#sim - client
def client(env, cpu, network, rate, packet_bits, response_times):
    while True:
        yield env.timeout(random.expovariate(rate))
        env.process(server(env, cpu, network, packet_bits, response_times))

#metrics
def monitor(env, cpu, response_times):
    interval = 1 # per sec
    last_count = 0
    window_size = 100  #avg response time in little law
    while True:
        yield env.timeout(interval)
        time_points.append(env.now)
        # cpu util 
        free_slots = cpu.count
        utilization = (CPU - free_slots) / CPU
        utilization_times.append(utilization * 100)
        # throughput - per s 
        throughput = len(response_times) - last_count
        throughput_times.append(throughput)
        last_count = len(response_times)
        # concurrency)
        if len(response_times) >= window_size:
            recent_responses = response_times[-window_size:]
            recent_avg_rt = statistics.mean(recent_responses)
            concurrency = throughput * recent_avg_rt
        else:
            concurrency = 0.0
        concurrency_times.append(concurrency)

#sim run
env = simpy.Environment()
cpu = simpy.Resource(env, capacity=CPU)
network = simpy.Resource(env, capacity=1) # port

# upload sim
for _ in range(UPLOAD_CLIENTS):
    env.process(client(env, cpu, network, UPLOAD_RATE, UPLOAD_PACKET_BITS, response_times))

#download sim
for _ in range(DOWNLOAD_CLIENTS):
    env.process(client(env, cpu, network, DOWNLOAD_RATE, DOWNLOAD_PACKET_BITS, response_times))

env.process(monitor(env, cpu, response_times))
env.run(until=SIMULATION_TIME)

#performance metrincs in console output
avg_response = statistics.mean(response_times)
throughput = len(response_times) / SIMULATION_TIME
utilization_cpu = statistics.mean(utilization_times)  # restructured moni
concurrency = statistics.mean(concurrency_times)  

#print data
print("PERFORMANCE RESULTS OF SERVER")
print(f"Average Response Time: {avg_response:.6f} seconds")
print(f"Throughput: {throughput:.2f} packets/sec")
print(f"CPU Utilization: {utilization_cpu:.2f}%")
print(f"Concurrency (Active Requests): {concurrency:.2f}")

#visualisation
#chart for resoponse time
plt.figure(figsize=(8,5))
plt.hist(response_times, bins=50, color='skyblue', edgecolor='black')
plt.xlabel("Response Time (s)")
plt.ylabel("Frequency")
plt.title("Response Time Distribution")
plt.grid(True)
plt.show()

plt.figure(figsize=(8,5))
plt.plot(sorted(response_times), color='orange')
plt.xlabel("Request Index")
plt.ylabel("Response Time (seconds)")
plt.title("Response Time Trend")
plt.grid(True)
plt.show()

#chartt for utilization
plt.figure(figsize=(8,5))
plt.plot(time_points, utilization_times, color='green')
plt.xlabel("Time (s)")
plt.ylabel("CPU Utilization (%)")
plt.title("CPU Utilization Over Time")
plt.grid(True)
plt.show()

#chart for througput
plt.figure(figsize=(8,5))
plt.plot(time_points, throughput_times, color='blue')
plt.xlabel("Time (s)")
plt.ylabel("Throughput (packets/sec)")
plt.title("Throughput Over Time")
plt.grid(True)
plt.show()

#chart for concurrency
plt.figure(figsize=(8,5))
plt.plot(time_points, concurrency_times, color='red')
plt.xlabel("Time (s)")
plt.ylabel("Concurrency (Active Requests)")
plt.title("Concurrency Over Time")
plt.grid(True)
plt.show()