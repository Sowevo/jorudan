# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import json
import os
import sqlite3

from scrapy_version.items import StationItem, ScheduleItem, SchedulesStationItem


class SQLitePipeline(object):
    def __init__(self):
        self.curr = None
        self.conn = None
        self.create_connection()
        self.create_table()

    def create_connection(self):
        directory = "output"
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.conn = sqlite3.connect(directory+"/schedule_info.sqlite")
        self.curr = self.conn.cursor()

    def create_table(self):
        self.curr.execute('''
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

    def process_item(self, item, spider):
        if isinstance(item, SchedulesStationItem):
            self.store_db(item)
        return item

    def store_db(self, item):
        self.curr.execute("""
            REPLACE INTO schedule_info (id, schedule_id, name,cn_name, number, series, direction,stop_name, date, time, station_url) VALUES (:id, :schedule_id, :name,:cn_name, :number, :series, :direction,:stop_name, :date, :time, :station_url)
        """, (
            item['id'], item['schedule_id'], item['name'], item['cn_name'], item['number'], item['series'],
            item['direction'], item['stop_name'], item['date'], item['time'], item['station_url']
        ))
        self.conn.commit()


class JsonPipeline(object):
    def __init__(self):
        self.file_handles = {}

    def process_item(self, item, spider):
        file_path = f'output/unknown.json'
        # 根据item类型，选择存储路径
        if isinstance(item, StationItem):
            file_path = f'output/station.json'
        elif isinstance(item, ScheduleItem):
            file_path = f'output/schedule.json'
        elif isinstance(item, SchedulesStationItem):
            date = item['date'].replace('-', '')
            file_path = f'output/schedules_station_{date}.json'

        item_json = json.dumps(dict(item), ensure_ascii=False, indent=None, separators=(',', ':'))
        if file_path not in self.file_handles:
            file = open(file_path, 'w+', encoding='UTF-8')
            file.write('[')
            file.write(item_json + ',')
            self.file_handles[file_path] = file
        else:
            file = self.file_handles[file_path]
            file.write(item_json + ',')

        return item

    def close_spider(self, spider):
        # 在结束后，需要对 每个文件 最后一次执行输出的 “逗号” 去除
        for file in self.file_handles.values():
            file.seek(file.tell() - 1, 0)
            file.truncate()
            file.write(']')
            file.close()
