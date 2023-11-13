# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class StationItem(scrapy.Item):
    name = scrapy.Field()
    url = scrapy.Field()


class ScheduleItem(scrapy.Item):
    name = scrapy.Field()
    url = scrapy.Field()


class SchedulesStationItem(scrapy.Item):
    id = scrapy.Field()
    schedule_id = scrapy.Field()
    name = scrapy.Field()
    cn_name = scrapy.Field()
    number = scrapy.Field()
    series = scrapy.Field()
    direction = scrapy.Field()
    stop_name = scrapy.Field()
    date = scrapy.Field()
    time = scrapy.Field()
    station_url = scrapy.Field()
