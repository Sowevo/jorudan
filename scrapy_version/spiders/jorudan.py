import re
import scrapy
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from scrapy_version.items import StationItem, ScheduleItem, SchedulesStationItem


class JorudanSpider(scrapy.Spider):
    name_map = {
        'あさま': {'cn_name': '浅间', 'series': ''},
        'かがやき': {'cn_name': '光辉', 'series': ''},
        'こだま': {'cn_name': '回声', 'series': ''},
        'こまち': {'cn_name': '小町', 'series': ''},
        'さくら': {'cn_name': '樱', 'series': ''},
        'たにがわ': {'cn_name': '谷川', 'series': ''},
        'つばさ': {'cn_name': '翼', 'series': ''},
        'つばめ': {'cn_name': '燕', 'series': ''},
        'つるぎ': {'cn_name': '剑', 'series': ''},
        'とき': {'cn_name': '朱鹭', 'series': ''},
        'なすの': {'cn_name': '那须野', 'series': ''},
        'のぞみ': {'cn_name': '希望', 'series': ''},
        'はくたか': {'cn_name': '白鹰', 'series': ''},
        'はやて': {'cn_name': '疾风', 'series': ''},
        'はやぶさ': {'cn_name': '隼', 'series': ''},
        'ひかり': {'cn_name': '光', 'series': ''},
        'みずほ': {'cn_name': '瑞穗', 'series': ''},
        'やまびこ': {'cn_name': '山彦', 'series': ''}
    }
    name = "jorudan"
    allowed_domains = ["www.jorudan.co.jp"]
    start_urls = ["https://www.jorudan.co.jp/time/shinkansen.html"]

    def parse_schedules_station(self, response):
        """
        获取一个班次下的所有站点信息
        """
        title = response.css('h1.time::text').get()
        name, cn_name, number, series, direction = self.parse_title(title)
        schedules_stations = response.css('tr.js_rosenEki')
        for schedule_station in schedules_stations:
            stop_name = schedule_station.css('td.eki::text').get()
            time = schedule_station.css('td.time::text').get().strip().replace(' 発', '').replace(' 着', '')
            station_url = schedule_station.css('a.noprint::attr(href)').get()
            station_url = response.urljoin(station_url)
            item = SchedulesStationItem()
            item['name'] = name
            item['cn_name'] = cn_name
            item['number'] = number
            item['series'] = series
            item['direction'] = direction
            item['stop_name'] = stop_name
            # item['date'] = response.meta['date']
            item['time'] = time
            item['station_url'] = station_url
            yield item

    def parse_schedules(self, response):
        """
        获取一个站点下的班次列表
        """
        schedules_links = response.css('table.timetable2 a')
        # TODO 处理日期
        for link in schedules_links[:1]:
            name = link.css('span::text').get()
            url = link.css('::attr(href)').get()
            url = self.clean_params(response.urljoin(url))
            item = ScheduleItem()
            item['name'] = name
            item['url'] = url
            yield item
            yield scrapy.http.Request(url, self.parse_schedules_station)
        reverse_tags = response.css('a.tab')
        # 处理反向
        for reverse_tag in reverse_tags:
            reverse_url = reverse_tag.css('::attr(href)').get()
            reverse_url = response.urljoin(reverse_url)
            yield scrapy.http.Request(reverse_url, self.parse_schedules)

    def parse(self, response, *args, **kwargs):
        """
        获取所有新干线站点列表
        """
        # 使用CSS选择器提取 <a> 标签的内容和链接
        station_links = response.css('.section_none a')
        for link in station_links[2:3]:
            name = link.css('::text').get()
            url = link.css('::attr(href)').get()
            url = response.urljoin(url)
            item = StationItem()
            item['name'] = name
            item['url'] = url
            yield item
            yield scrapy.http.Request(url, self.parse_schedules)

    def clean_params(self, url):
        """
        清理URL中的参数
        """
        # 解析URL
        parsed_url = urlparse(url)
        # 获取查询参数字典
        params = parse_qs(parsed_url.query)
        # 只保留'lid'参数
        if 'lid' in params:
            new_params = {'lid': params['lid']}
        else:
            new_params = {}
        # 重新构建URL
        new_query = urlencode(new_params, doseq=True)
        new_url = urlunparse(
            (parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, new_query, parsed_url.fragment))
        return new_url

    def parse_title(self, text):
        """
        从标题中解析出车次部分信息
        """
        # 使用正则表达式来匹配信息，允许车型信息可选，并排除括号
        pattern = r'^(.*?)\d+号(?:\((.*?)\))? *\((.*?)行\)の運行表$'
        match = re.match(pattern, text)

        if match:
            name = match.group(1)
            series = match.group(2) if match.group(2) else None
            direction = match.group(3)
            number = re.search(r'\d+', text).group()
        else:
            name = None
            series = None
            direction = None
            number = None
        cn_name = self.name_map[name]['cn_name'] if name in self.name_map else name
        return name, cn_name, number, series, direction
