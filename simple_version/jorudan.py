from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
import requests
import requests_cache
from retrying import retry
import sqlite3
import json
from tqdm import tqdm
from datetime import datetime, timedelta
import hashlib
import pytz
import argparse
from utils import parse_title, clean_params


class Station:
    def __init__(self, name, url):
        self.name = name
        self.url = url

    def __eq__(self, other):
        return isinstance(other, Station) and self.url == other.url

    def __hash__(self):
        return hash(self.url)


class Schedule:
    def __init__(self, name, url):
        self.name = name
        self.url = url

    def __eq__(self, other):
        return isinstance(other, Station) and self.url == other.url

    def __hash__(self):
        return hash(self.url)


class ScheduleStation:
    def __init__(self, schedule_id, name, cn_name, number, series, direction, stop_name, _date, time, station_url):
        self.id = hashlib.md5((str(schedule_id) + stop_name + _date).encode()).hexdigest()
        self.schedule_id = schedule_id
        self.name = name
        self.cn_name = cn_name
        self.number = number
        self.series = series
        self.direction = direction
        self.stop_name = stop_name
        self.date = _date
        self.time = time
        self.station_url = station_url

    def to_dict(self):
        return {
            'id': self.id,
            'schedule_id': self.schedule_id,
            'name': self.name,
            'cn_name': self.cn_name,
            'number': self.number,
            'series': self.series,
            'direction': self.direction,
            'stop_name': self.stop_name,
            'date': self.date,
            'time': self.time,
            'station_url': self.station_url
        }


# 启用缓存,缓存有效期为24小时
requests_cache.install_cache('requests_cache', expire_after=60 * 60 * 24)
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/119.0.0.0 Safari/537.36'}
base_url = 'https://www.jorudan.co.jp'


@retry(stop_max_attempt_number=10, wait_fixed=1000)
def get_stations():
    """
    获取所有新干线站点列表
    """
    url = base_url + '/time/shinkansen.html'
    r = requests.get(url, headers=headers, )
    soup = BeautifulSoup(r.text, "html.parser")
    div_elements = soup.find_all('div', class_='section_none')
    _stations = set()
    for div in div_elements:
        a_elements = div.find_all('a')
        for a in a_elements:
            _stations.add(Station(a.text, a['href']))
    return sorted(list(_stations), key=lambda x: x.name)


@retry(stop_max_attempt_number=10, wait_fixed=1000)
def get_schedules(_station, _date, reverse_direction=True):
    """
    获取一个站点下的班次列表
    """
    url = base_url + _station.url + _date.strftime("?Ddd=%d&Dym=%Y%m")
    r = requests.get(url, headers=headers, )
    soup = BeautifulSoup(r.text, "html.parser")
    table_elements = soup.find_all('table', class_='timetable2')
    _schedules = set()
    for div in table_elements:
        a_elements = div.find_all('a')
        for a in a_elements:
            href = clean_params(a['href'])
            name = a.select_one('span').text
            _schedules.add(Schedule(name, href))
    if reverse_direction:
        bk = soup.find_all('a', class_='tab')
        if len(bk) > 1:
            print("多个反向班次!!!" + _station.url)
        for a in bk:
            href = a['href']
            name = _station.name
            reverse_schedules = get_schedules(Station(name, href), _date, False)
            _schedules.update(reverse_schedules)

    return sorted(list(_schedules), key=lambda x: x.name)


@retry(stop_max_attempt_number=10, wait_fixed=1000)
def get_schedule_stations(_schedule, _date):
    """
    获取一个班次下的所有站点信息
    """
    # 解析URL
    parsed_url = urlparse(_schedule.url)
    # 获取查询参数字典
    params = parse_qs(parsed_url.query)
    _schedule_infos = []
    url = base_url + _schedule.url
    r = requests.get(url, headers=headers, )
    soup = BeautifulSoup(r.text, "html.parser")
    title_element = soup.find('h1', class_='time')
    # 这里有时候返回的数据是错的,清除掉缓存试试
    if title_element is None:
        requests_cache.get_cache().delete_url(url)
        print("缓存失效,重新请求:"+url)
    title = title_element.text
    name, cn_name, number, series, direction = parse_title(title)

    # 查找所有class为"js_rosenEki"的元素
    eki_elements = soup.find_all("tr", class_="js_rosenEki")
    for eki in eki_elements:
        stop_name = eki.find("td", class_="eki").text.strip()
        time = eki.find("td", class_="time").text.strip().replace(" 発", "").replace(" 着", "")
        station_url = eki.find("a", class_="noprint")["href"]

        _schedule_infos.append(
            ScheduleStation(int(params['lid'][0]), name, cn_name, number, series, direction, stop_name,
                            _date.strftime("%Y-%m-%d"), time, base_url + station_url))
    return _schedule_infos


def create_schedule_table():
    conn = sqlite3.connect('schedule_info.sqlite')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedule_info (
            id TEXT PRIMARY KEY,
            schedule_id TEXT,
            name TEXT,
            cn_name TEXT,
            number TEXT,
            series TEXT,
            direction TEXT,
            stop_name TEXT,
            date TEXT,
            time TEXT,
            station_url TEXT
        )
    ''')

    conn.commit()
    conn.close()


# Function to insert data into SQLite table
def insert_schedule_data(schedule_info):
    conn = sqlite3.connect('schedule_info.sqlite')
    cursor = conn.cursor()

    for _info in schedule_info:
        cursor.execute('''
            REPLACE INTO schedule_info (id, schedule_id, name,cn_name, number, series, direction,stop_name, date, time, station_url) VALUES (:id, :schedule_id, :name,:cn_name, :number, :series, :direction,:stop_name, :date, :time, :station_url)
        ''', _info.to_dict())

    conn.commit()
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process schedules for future days.')
    parser.add_argument('--days', type=int, default=3, help='Number of future days to process')
    args = parser.parse_args()

    # 获取当前日期和时间
    today = datetime.now()

    # 设置目标时区为日本时区
    japan_timezone = pytz.timezone('Asia/Tokyo')

    # 计算未来三天的日期，并转换为日本时区
    future_dates_japan = [today + timedelta(days=i) for i in range(args.days)]
    future_dates_japan = [date.astimezone(japan_timezone) for date in future_dates_japan]

    # 创建 SQLite 表
    create_schedule_table()
    # 获取所有的站点列表
    stations = get_stations()

    # stations = [Station('東京', '/time/timetable/新横浜/新幹線のぞみ/名古屋/')]

    for date in future_dates_japan[2:3]:
        schedules_set = set()
        schedule_infos = []
        tqdm_stations = tqdm(stations, desc="加载[" + date.strftime('%Y%m%d') + "]站点信息...", ncols=150)
        for station in tqdm_stations:
            schedules = get_schedules(station, date)
            schedules_set.update(schedules)
        all_schedules = sorted(schedules_set, key=lambda x: x.name)
        tqdm_schedules = tqdm(all_schedules, desc="加载[" + date.strftime('%Y%m%d') + "]班次信息...", ncols=150)
        for schedule in tqdm_schedules[2:3]:
            infos = get_schedule_stations(schedule, date)
            # 将 schedule_infos 写入 SQLite 文件
            insert_schedule_data(infos)
            for info in infos:
                schedule_infos.append(info)
        # 按天写入json文件
        with open('schedule_info_' + date.strftime('%Y%m%d') + '.json', 'w', encoding='utf-8') as json_file:
            json.dump([schedule.to_dict() for schedule in schedule_infos], json_file, ensure_ascii=False, indent=4)
