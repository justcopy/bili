import sys
import requests
from datetime import date, timedelta
from fake_useragent import UserAgent
import datetime
import threading
import argparse
import re

# 配置参数解析
parser = argparse.ArgumentParser(description='Proxy Filtering and Saving Utility')
parser.add_argument('--proxy-source-url', nargs='+', default=['https://checkerproxy.net/api/archive/',
                                                               'https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt',
                                                               'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
                                                               'https://raw.githubusercontent.com/parserpp/ip_ports/main/proxyinfo.txt'],
                    help='URLs to fetch proxy list from (can be multiple)')
parser.add_argument('--test_url', type=str, default='http://httpbin.org/post',
                    help='URL to test proxy availability')
parser.add_argument('--thread-num', type=int, default=75,
                    help='Number of threads for filtering active proxies')
parser.add_argument('--timeout', type=int, default=3,
                    help='Timeout in seconds for proxy connection')
parser.add_argument('--output-file', type=str, default='proxy.txt',
                    help='Output file name to save active proxies')
args = parser.parse_args()


def time(seconds: int) -> str:
    if seconds < 60:
        return f'{seconds}s'
    else:
        return f'{int(seconds / 60)}min {seconds % 60}s'


# 进度条显示函数
def pbar(n: int, total: int) -> str:
    progress = '━' * int(n / total * 50)
    blank = ' ' * (50 - len(progress))
    return f'\r{n}/{total} {progress}{blank}'


# 获取代理列表，支持从多个不同来源获取并合并
def get_proxies():
    all_proxies = []
    for url in args.proxy_source_url:
        print(f'\ngetting proxies from {url}...')
        try:
            if "api/archive/" in url:
                yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
                full_url = f'{url}{yesterday}'
                proxies_json = requests.get(full_url).json()
                all_proxies.extend([proxy['addr'] for proxy in proxies_json])
            else:
                response = requests.get(url)
                content = response.text
                # 根据不同文件格式提取代理地址，这里简单示例以IP:端口形式提取，可根据实际情况完善正则
                proxies = re.findall(r'\d+\.\d+\.\d+\.\d+:\d+', content)
                all_proxies.extend(proxies)
        except requests.RequestException as e:
            print(f"Error fetching proxies from {url}: {e}")
    print(f'successfully get {len(all_proxies)} proxies in total')
    return all_proxies


# 2. 多线程筛选活跃代理
active_proxies = []
count = 0
ua = UserAgent()  # 创建UserAgent实例用于生成随机User-Agent


def filter_proxys(proxies: 'list[str]') -> None:
    global count
    for proxy in proxies:
        count = count + 1
        headers = {'User-Agent': ua.random}  # 设置随机User-Agent
        try:
            requests.post(args.test_url,
                          proxies={'http': 'http://'+proxy},
                          headers=headers,
                          timeout=args.timeout)
            active_proxies.append(proxy)
        except requests.RequestException as e:
            print(f"Error testing proxy {proxy}: {e}")
        print(f'{pbar(count, len(all_proxies))} {100*count/len(all_proxies):.1f}%   ', end='')


start_filter_time = datetime.datetime.now()
print('\nfiltering active proxies using'+ args.test_url + '...')
all_proxies = get_proxies()
thread_proxy_num = len(all_proxies) // args.thread_num
threads = []
for i in range(args.thread_num):
    start = i * thread_proxy_num
    end = start + thread_proxy_num if i < (args.thread_num - 1) else None
    thread = threading.Thread(target=filter_proxys, args=(all_proxies[start:end],))
    thread.start()
    threads.append(thread)
for thread in threads:
    thread.join()
filter_cost_seconds = int((datetime.datetime.now() - start_filter_time).total_seconds())
print(f'\nsuccessfully filter {len(active_proxies)} active proxies using {time(filter_cost_seconds)}')


# 3. 保存活跃代理到文件
with open(args.output_file, 'w') as f:
    for proxy in active_proxies:
        f.write(proxy + '\n')