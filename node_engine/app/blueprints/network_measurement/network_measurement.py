import ipaddress
import socket
import platform

from flask import Blueprint
from requests import get
import io
import os
import sys
from itertools import islice
import subprocess
import re

network_measurement = Blueprint("network_measurement", __name__)

def get_ip_info():
    ip = socket.gethostbyname(socket.gethostname())
    if ipaddress.ip_address(ip).is_private:
        #public_ip = get('https://api.ipify.org').text
        resp = get('https://api4.ipify.org?format=json').text
        import ast
        public_ip = ast.literal_eval(resp)['ip']
        router_rtt = ping(public_ip)
        private_ip = ip
    else:
        public_ip = ip
        private_ip = None
        router_rtt = None

    return {"public": public_ip, "private": private_ip, "router_rtt": router_rtt}


def ping(target_ip):
    # Parameter for number of packets differs between the operating systems
    param = "-n" if platform.system().lower() == "windows" else "-c"
    command = ["ping", param, "3", target_ip]
    response = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    regex_pattern = "rtt min/avg/max/mdev = (\d+.\d+)/(\d+.\d+)/(\d+.\d+)/(\d+.\d+)"
    # times = min,avg,max,mdev
    times = re.findall(regex_pattern, str(response))[0]
    avg_rtt = times[1]

    return avg_rtt

def parallel_ping_retry(target_ips):
    statistics = parallel_ping(target_ips)
    if len(statistics) != len(target_ips):
        # retry for IPs that did return empty result
        retry_ips = [ip for ip in target_ips if ip not in statistics]
        # Try longer ping
        ping_count = 5
        stats = {}
        for i in range(4):
            stats = {**stats, **parallel_ping(retry_ips, ping_count)}
            if len(stats) == len(retry_ips):
                break
            else:
                ping_count *= 2
        return {**statistics, **stats}

    return statistics

def parallel_ping(target_ips, ping_count=3):
    ON_POSIX = 'posix' in sys.builtin_module_names
    # Create a pipe to get data
    input_fd, output_fd = os.pipe()
    # start several subprocesses
    processes = [subprocess.Popen(['ping', '-c', str(ping_count), ip], stdout=output_fd, close_fds=ON_POSIX) for ip in target_ips]
    os.close(output_fd)
    statistics = {}
    ip_pattern = "\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    rtt_pattern = "rtt min/avg/max/mdev = (\d+.\d+)/(\d+.\d+)/(\d+.\d+)/(\d+.\d+)"
    with io.open(input_fd, 'r', buffering=1) as file:
        for line in file:
            if 'ping statistics' in line:
                # Find target ip
                ip_match = re.search(ip_pattern, line)
                # Find RTTs
                statistic = ''.join(islice(file, 2))
                statistic_match = re.findall(rtt_pattern, statistic)
                if len(statistic_match) != 0 and ip_match is not None:
                    ip = ip_match[0]
                    stat = statistic_match[0]
                    # min_rtt = float(stat[0])
                    avg_rtt = float(stat[1])
                    statistics[ip] = avg_rtt

    for p in processes:
        p.wait()

    return statistics
