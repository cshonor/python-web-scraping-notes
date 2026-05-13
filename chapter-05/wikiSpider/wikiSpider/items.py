import scrapy


class ArticleItem(scrapy.Item):
    url = scrapy.Field()
    title = scrapy.Field()
    # 正文区域文本（由爬虫截断，避免单条 Item 过大）
    text = scrapy.Field()
    last_updated = scrapy.Field()
    # 由 Pipeline 尝试解析；失败则不写入
    last_updated_iso = scrapy.Field()
