import scrapy
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from utils import parse_title, clean_params
from scrapy_version.items import StationItem, ScheduleItem, SchedulesStationItem


class JorudanSpider(scrapy.Spider):
    name = "jorudan"
    allowed_domains = ["www.jorudan.co.jp"]
    start_urls = ["https://www.jorudan.co.jp/time/shinkansen.html"]

    def parse_schedules_station(self, response):
        """
        获取一个班次下的所有站点信息
        """
        date = response.meta['date'].strftime("%Y-%m-%d")
        # 解析URL
        parsed_url = urlparse(response.url)
        # 获取查询参数字典
        params = parse_qs(parsed_url.query)
        schedule_id = params['lid'][0]
        title = response.css('h1.time::text').get()
        name, cn_name, number, series, direction = parse_title(title)
        schedules_stations = response.css('tr.js_rosenEki')
        for schedule_station in schedules_stations:
            stop_name = schedule_station.css('td.eki::text').get()
            time = schedule_station.css('td.time::text').get().strip().replace(' 発', '').replace(' 着', '')
            station_url = schedule_station.css('a.noprint::attr(href)').get()
            station_url = response.urljoin(station_url)
            item = SchedulesStationItem()
            item['id'] = hashlib.md5((str(schedule_id) + stop_name + date).encode()).hexdigest()
            item['schedule_id'] = schedule_id
            item['name'] = name
            item['cn_name'] = cn_name
            item['number'] = number
            item['series'] = series
            item['direction'] = direction
            item['stop_name'] = stop_name
            item['date'] = date
            item['time'] = time
            item['station_url'] = station_url
            yield item

    def parse_schedules(self, response):
        """
        获取一个站点下的班次列表
        """
        date = response.meta['date']
        schedules_links = response.css('table.timetable2 a')
        for link in schedules_links:
            name = link.css('span::text').get()
            url = link.css('::attr(href)').get()
            url = clean_params(response.urljoin(url))
            item = ScheduleItem()
            item['name'] = name
            item['url'] = url
            yield item
            yield scrapy.http.Request(url, self.parse_schedules_station, meta={'date': date})
        reverse_tags = response.css('a.tab')
        # 处理反向
        for reverse_tag in reverse_tags:
            reverse_url = reverse_tag.css('::attr(href)').get()
            reverse_url = response.urljoin(reverse_url)
            yield scrapy.http.Request(reverse_url, self.parse_schedules, meta={'date': date})

    def parse(self, response, *args, **kwargs):
        """
        获取所有新干线站点列表
        """
        # 获取当前日期
        today = datetime.now()
        # 计算未来三天的日期
        future_dates = [today + timedelta(days=i) for i in range(3)]
        # 使用CSS选择器提取 <a> 标签的内容和链接
        station_links = response.css('.section_none a')
        for link in station_links:
            name = link.css('::text').get()
            url = link.css('::attr(href)').get()
            url = response.urljoin(url)
            item = StationItem()
            item['name'] = name
            item['url'] = url
            yield item
            for date in future_dates:
                yield scrapy.http.Request(url + date.strftime("?Ddd=%d&Dym=%Y%m"), self.parse_schedules,
                                          meta={'date': date})
