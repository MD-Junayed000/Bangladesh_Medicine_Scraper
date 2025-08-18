import re
import scrapy
from django.utils.text import slugify
from scrapy_playwright.page import PageMethod

from medexbot.items import ManufacturerItem


class ManufacturerSpider(scrapy.Spider):
    name = "manufacturer"
    allowed_domains = ["medex.com.bd"]
    start_urls = ["https://medex.com.bd/companies?page=1"]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                headers={
                    "Referer": "https://medex.com.bd/",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-User": "?1",
                },
                meta={
                    "playwright": True,
                    "playwright_context": "default",
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                    ],
                },
            )

    def parse(self, response, **kwargs):
        # Detect challenge page early
        u = response.url.lower()
        t = response.text.lower()
        if "captcha" in u or "challenge" in u or "captcha" in t:
            self.logger.warning("Captcha challenge detected at %s — stopping.", response.url)
            return

        for company_info in response.css("div.data-row"):
            item = ManufacturerItem()

            manufacturer_link = company_info.css("div.data-row-top a::attr(href)").get()
            if not manufacturer_link:
                continue

            # gather the two counters robustly
            tail_texts = company_info.css("div.col-xs-12 ::text").getall()
            tail = (tail_texts[-1].strip() if tail_texts else "") or ""
            digits = [int(s) for s in tail.split() if s.isdigit()]
            generic_counter, brand_name_counter = (digits + [0, 0])[:2]

            item["manufacturer_id"] = re.findall(r"companies/(\d+)/", manufacturer_link)[0]
            item["manufacturer_name"] = company_info.css("div.data-row-top a::text").get()
            item["generics_count"] = generic_counter
            item["brand_names_count"] = brand_name_counter
            item["slug"] = slugify(f"{item['manufacturer_name']}-{item['manufacturer_id']}", allow_unicode=True)
            yield item

        # follow pagination with Playwright as well
        for href in response.css('a.page-link[rel="next"]::attr(href)').getall():
            yield response.follow(
                href,
                callback=self.parse,
                headers={"Referer": response.url},
                meta={
                    "playwright": True,
                    "playwright_context": "default",
                    "playwright_page_methods": [PageMethod("wait_for_load_state", "networkidle")],
                },
            )
