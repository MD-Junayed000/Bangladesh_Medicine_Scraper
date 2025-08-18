import re
import scrapy
from django.utils.text import slugify
from scrapy_playwright.page import PageMethod

from medexbot.items import DrugClassItem


class DrugClassSpider(scrapy.Spider):
    name = "drug_class"
    allowed_domains = ['medex.com.bd']
    start_urls = ['https://medex.com.bd/drug-classes']

    def start_requests(self):
        """Start requests with Playwright like the working generic spider."""
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
        """Parse the drug classes listing page."""
        # Detect challenge page early
        if "captcha" in response.url.lower() or "challenge" in response.url.lower():
            self.logger.warning("Captcha challenge detected at %s — stopping.", response.url)
            return

        self.logger.info("Parsing drug classes listing page")
        
        # Extract drug class links
        drug_class_links = response.css('a[target="_blank"] ::attr("href")').getall()
        
        if not drug_class_links:
            self.logger.warning("No drug class links found on %s", response.url)
            return
        
        self.logger.info(f"Found {len(drug_class_links)} drug class links")
        
        # Follow each drug class link
        for link in drug_class_links:
            if link and 'drug-classes' in link:
                # Extract drug class info from the link
                drug_class_id_match = re.findall("drug-classes/(\S*)/", link)
                if drug_class_id_match:
                    drug_class_id = drug_class_id_match[0]
                    # Get the drug class name from the link text
                    link_element = response.css(f'a[href="{link}"]')
                    drug_class_name = link_element.css('::text').get()
                    
                    if drug_class_name:
                        self.logger.info(f"Following drug class: {drug_class_name} (ID: {drug_class_id})")
                        yield response.follow(
                            link,
                            callback=self.parse_drug_class,
                            headers={"Referer": response.url},
                            meta={
                                "playwright": True,
                                "playwright_context": "default",
                                "playwright_page_methods": [PageMethod("wait_for_load_state", "networkidle")],
                                "drug_class_id": drug_class_id,
                                "drug_class_name": drug_class_name.strip()
                            }
                        )

    def parse_drug_class(self, response):
        """Parse individual drug class page."""
        # Skip CAPTCHA pages
        if 'captcha-challenge' in response.url:
            self.logger.warning("Skipping CAPTCHA page: %s", response.url)
            return
        
        # Get drug class info from meta
        drug_class_id = response.meta.get('drug_class_id')
        drug_class_name = response.meta.get('drug_class_name')
        
        if not drug_class_id or not drug_class_name:
            self.logger.warning("Missing drug class info in meta for %s", response.url)
            return
        
        self.logger.info(f"Processing drug class: {drug_class_name} (ID: {drug_class_id})")
        
        # Create drug class item
        item = DrugClassItem()
        item['drug_class_id'] = drug_class_id
        item['drug_class_name'] = drug_class_name
        
        # Count generics in this drug class
        generic_links = response.css('a.hoverable-block ::attr("href")').getall()
        item['generics_count'] = len(generic_links)
        
        # Generate slug
        item['slug'] = slugify(drug_class_name + '-' + drug_class_id, allow_unicode=True)
        
        self.logger.info(f"Successfully extracted drug class: {drug_class_name} with {item['generics_count']} generics")
        yield item
