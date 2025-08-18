# medexbot/spiders/indication_spider.py
import os
import logging
import re

from scrapy import Spider, Request
from scrapy_playwright.page import PageMethod
from django.db import IntegrityError
from django.utils.text import slugify

from crawler.models import Generic, Indication
from medexbot.items import IndicationItem


class IndicationSpider(Spider):
    name = "indication"
    allowed_domains = ["medex.com.bd"]
    start_urls = ["https://medex.com.bd/indications?page=1"]

    def _pw_meta(self, extra=None, tag="list"):
        os.makedirs("debug", exist_ok=True)
        methods = [
            # give CF some time, then wait for the real list
            PageMethod("wait_for_load_state", "networkidle"),
            PageMethod("wait_for_selector", "div.data-row", timeout=120000),
            # drop a screenshot per page for troubleshooting
            PageMethod("screenshot", path=f"debug/{tag}.png", full_page=True),
        ]
        meta = {
            "playwright": True,
            # IMPORTANT: use the *persistent* context
            "playwright_context": "human",
            "playwright_page_methods": methods,
        }
        if extra:
            meta.update(extra)
        return meta

    def start_requests(self):
        yield Request(self.start_urls[0], meta=self._pw_meta(tag="indications-page1"))

    def parse(self, response, **kwargs):
        rows = response.css("div.data-row")
        if not rows:
            # We didn’t get the list. Save the HTML we actually got.
            with open("debug/indications-page1.html", "wb") as f:
                f.write(response.body)
            self.logger.warning("No data rows on %s (saved debug/indications-page1.html)", response.url)
            return  # stop here; you can open the file to see if it’s the challenge

        for row in rows:
            link = row.css("div.data-row-top a::attr(href)").get()
            if not link:
                continue
            indication_id = re.findall(r"indications/(\S*)/", link)[0]
            indication_name = row.css("div.data-row-top a::text").get()
            nums = row.css("div.col-xs-12 ::text").re(r"(\d+)")
            generics_count = 0 if not nums else nums[0]

            yield response.follow(
                link,
                callback=self.parse_indication,
                meta=self._pw_meta(
                    {
                        "indication_id": indication_id,
                        "indication_name": indication_name,
                        "generics_count": generics_count,
                    },
                    tag=f"indication-{indication_id}",
                ),
            )

        # pagination
        for href in response.css('a.page-link[rel="next"]::attr(href)').getall():
            yield response.follow(href, callback=self.parse, meta=self._pw_meta(tag="indications-next"))

    def generic_id_mapping(self, indication, generic_ids):
        for gid in generic_ids or []:
            try:
                generic = Generic.objects.get(generic_id=gid)
                logging.info("Setting indication on generic %s", gid)
                generic.indication = indication
                generic.save(update_fields=["indication"])
            except Generic.DoesNotExist as ge:
                logging.info(ge)
            except IntegrityError as ie:
                logging.info(ie)

    def parse_indication(self, response):
        item = IndicationItem()
        item["indication_id"] = response.meta["indication_id"]
        item["indication_name"] = response.meta["indication_name"]
        item["generics_count"] = response.meta["generics_count"]
        item["slug"] = slugify(f"{item['indication_name']}-{item['indication_id']}", allow_unicode=True)

        generic_ids = []
        try:
            links = response.css("div.data-row-top a::attr(href)").getall()
            generic_ids = [re.findall(r"generics/(\S*)/", u)[0] for u in links]
        except IndexError as ie:
            logging.info(ie)

        try:
            indication = Indication.objects.get(indication_id=item["indication_id"])
            print("Indication exists", str(indication.indication_name))
            self.generic_id_mapping(indication, generic_ids)
        except Indication.DoesNotExist:
            indication = item.save()
            print("Created indication", str(indication.indication_name))
            self.generic_id_mapping(indication, generic_ids)

        yield item
