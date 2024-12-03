# boost_view_count.py
import sys
import threading
from time import sleep
from datetime import date, datetime, timedelta
import requests
from fake_useragent import UserAgent

# parameters
timeout = 3  # seconds for proxy connection timeout
thread_num = 75  # thread count for filtering active proxies
round_time = 305  # seconds for each round of view count boosting
update_pbar_count = 10  # update view count progress bar for every xx proxies
bv = sys.argv[1]  # video BV id
target = int(sys.argv[2])  # target view count

def time(seconds: int) -> str:
    if seconds < 60:
        return f'{seconds}s'
    else:
        return f'{int(seconds / 60)}min {seconds % 60}s'

# progress bar
def pbar(n: int, total: int) -> str:
    progress = '━' * int(n / total * 50)
    blank = ' ' * (50 - len(progress))
    return f'\r{n}/{total} {progress}{blank}'

# 3.boost view count
print(f'\nstart boosting {bv} at {datetime.now().strftime("%H:%M:%S")}')
current = 0
while True:
    reach_target = False
    start_time = datetime.now()
    info = {}  # video information JSON
    # send POST click request for each proxy
    with open('proxy.txt', 'r') as f:
        active_proxies = f.read().splitlines()
    for i, proxy in enumerate(active_proxies):
        try:
            if i % update_pbar_count == 0:  # update progress bar for every {update_pbar_count} proxies
                print(f'{pbar(current, target)} updating view count...', end='')
                info = (requests.get(f'https://api.bilibili.com/x/web-interface/view?bvid={bv}',
                                     headers={'User-Agent': UserAgent().random})
                       .json()['data'])
                current = info['stat']['view']
                if current >= target:
                    reach_target = True
                    print(f'{pbar(current, target)} done                 ', end='')
                    break

            requests.post('http://api.bilibili.com/x/click-interface/click/web/h5',
                          proxies={'http': 'http://'+proxy},
                          headers={'User-Agent': UserAgent().random},
                          timeout=timeout,
                          data={
                              'aid': info['aid'],
                              'cid': info['cid'],
                              'bvid': bv,
                              'part': '1',
                              'mid': info['owner']['mid'],
                              'jsonp': 'jsonp',
                              'type': info['desc_v2'][0]['type'] if info['desc_v2'] else '1',
                              'sub_type': '0'
                          })
            print(f'{pbar(current, target)} proxy({i+1}/{len(active_proxies)}) success   ', end='')
        except:  # proxy connect timeout
            print(f'{pbar(current, target)} proxy({i+1}/{len(active_proxies)}) fail      ', end='')

    if reach_target:  # reach target view count
        break
    remain_seconds = int(round_time-(datetime.now()-start_time).total_seconds())
    if remain_seconds > 0:
        for second in reversed(range(remain_seconds)):
            print(f'{pbar(current, target)} next round: {time(second)}          ', end='')
            sleep(1)
print(f'\nfinish at {datetime.now().strftime("%H:%M:%S")}\n')
