"""示例管线：透传（可按需加清洗、去重、入库）。"""


class WikiSpiderPipeline:
    def process_item(self, item, spider):
        return item
