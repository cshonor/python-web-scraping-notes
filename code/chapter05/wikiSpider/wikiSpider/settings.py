BOT_NAME = "wikiSpider"
SPIDER_MODULES = ["wikiSpider.spiders"]
NEWSPIDER_MODULE = "wikiSpider.spiders"

ROBOTSTXT_OBEY = True

USER_AGENT = (
    "wikiSpider/0.1 (educational notes; "
    "https://github.com/REMitchell/python-scraping; mailto:you@example.com)"
)

CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 1.0
CONCURRENT_REQUESTS_PER_DOMAIN = 2

LOG_LEVEL = "INFO"

# 演示用：抓取若干页后自动停止，避免长时间占用维基带宽
CLOSESPIDER_PAGECOUNT = 30

ITEM_PIPELINES = {
    "wikiSpider.pipelines.WikiSpiderPipeline": 300,
}
