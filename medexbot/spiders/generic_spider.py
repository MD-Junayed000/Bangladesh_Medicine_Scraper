import re
import scrapy
from django.utils.text import slugify
from scrapy_playwright.page import PageMethod

from medexbot.items import GenericItem


class GenericSpider(scrapy.Spider):
    name = "generic"
    allowed_domains = ['medex.com.bd']
    
    # Use the same approach as manufacturer spider
    start_urls = ['https://medex.com.bd/generics?page=1']

    def start_requests(self):
        """Start requests with Playwright like the working manufacturer spider."""
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
        """Parse the generic listing page."""
        # Detect challenge page early
        if "captcha" in response.url.lower() or "challenge" in response.url.lower():
            self.logger.warning("Captcha challenge detected at %s — stopping.", response.url)
            return

        # Extract generic page links
        generic_page_links = response.css('a.hoverable-block ::attr("href")').getall()
        
        if not generic_page_links:
            # Fallback selector
            generic_page_links = [link for link in response.css('div.search-result-title a ::attr("href")').getall() if 'brands' not in link]
        
        self.logger.info(f"Found {len(generic_page_links)} generic links on {response.url}")
        
        # Follow each generic page link
        for link in generic_page_links:
            yield response.follow(
                link, 
                callback=self.parse_generic,
                headers={"Referer": response.url},
                meta={
                    "playwright": True,
                    "playwright_context": "default",
                    "playwright_page_methods": [PageMethod("wait_for_load_state", "networkidle")],
                }
            )

        # Follow pagination with Playwright as well
        next_page_links = response.css('a.page-link[rel="next"]::attr(href)').getall()
        for href in next_page_links:
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

    def parse_generic(self, response):
        """Parse individual generic page."""
        # Skip CAPTCHA pages
        if 'captcha-challenge' in response.url:
            self.logger.warning("Skipping CAPTCHA page: %s", response.url)
            return
        
        # Extract generic ID safely
        generic_id_match = re.findall("generics/(\S*)/", response.url)
        if not generic_id_match:
            self.logger.warning("Could not extract generic ID from URL: %s", response.url)
            return
        
        item = GenericItem()
        item['generic_id'] = generic_id_match[0]
        
        # Extract generic name safely
        generic_name = response.css('h1.page-heading-1-l ::text').get()
        if not generic_name:
            self.logger.warning("Could not extract generic name from: %s", response.url)
            return
        
        item['generic_name'] = generic_name.strip()
        self.logger.info(f"Processing generic: {item['generic_name']} (ID: {item['generic_id']})")
        
        # Extract monograph link
        item['monograph_link'] = response.css('span.hidden-sm a ::attr(href)').get()
        
        # Extract all descriptions using XPath
        item['indication_description'] = self._extract_description(response, 'indications')
        item['therapeutic_class_description'] = self._extract_description(response, 'drug_classes')
        item['pharmacology_description'] = self._extract_description(response, 'mode_of_action')
        item['dosage_description'] = self._extract_description(response, 'dosage')
        item['administration_description'] = self._extract_description(response, 'administration')
        item['interaction_description'] = self._extract_description(response, 'interaction')
        item['contraindications_description'] = self._extract_description(response, 'contraindications')
        item['side_effects_description'] = self._extract_description(response, 'side_effects')
        item['pregnancy_and_lactation_description'] = self._extract_description(response, 'pregnancy_cat')
        item['precautions_description'] = self._extract_description(response, 'precautions')
        item['pediatric_usage_description'] = self._extract_description(response, 'pediatric_uses')
        item['overdose_effects_description'] = self._extract_description(response, 'overdose_effects')
        item['duration_of_treatment_description'] = self._extract_description(response, 'duration_of_treatment')
        item['reconstitution_description'] = self._extract_description(response, 'reconstitution')
        item['storage_conditions_description'] = self._extract_description(response, 'storage_conditions')
        
        # Generate slug
        item['slug'] = slugify(item['generic_name'] + '-' + item['generic_id'], allow_unicode=True)
        
        self.logger.info(f"Successfully extracted generic: {item['generic_name']}")
        yield item

    def _extract_description(self, response, section_id):
        """Helper method to extract description text from a section."""
        try:
            # Look for the section heading
            section_heading = response.xpath(f'//div[@id="{section_id}"]/h4/text()').get()
            if not section_heading:
                return None
            
            # Get the next sibling node (the description text)
            description = response.xpath(f'//div[@id="{section_id}"]/following-sibling::node()[2]').get()
            if description:
                # Clean up the text
                cleaned = description.strip()
                if cleaned.startswith('<'):
                    # If it's HTML, extract just the text
                    from scrapy.selector import Selector
                    sel = Selector(text=description)
                    cleaned = sel.get()
                return cleaned if cleaned else None
            return None
        except Exception as e:
            self.logger.debug(f"Could not extract {section_id}: {e}")
            return None
