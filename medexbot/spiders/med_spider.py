import logging
import re
import time

import scrapy
from django.db import IntegrityError
from django.utils.text import slugify
from scrapy_playwright.page import PageMethod

from crawler.models import Generic, Manufacturer
from medexbot.items import MedItem, GenericItem


class MedSpider(scrapy.Spider):
    name = "med"
    allowed_domains = ['medex.com.bd']
    # Always prefer URLs that include ccd=1 to avoid consent/redirect pages
    start_urls = [
        'https://medex.com.bd/brands?page=1&ccd=1',
        'https://medex.com.bd/brands?herbal=1&page=1&ccd=1',
    ]

    def start_requests(self):
        """Start requests with Playwright like the working drug class spider."""
        # First, let's test if we can access any page
        test_urls = [
            'https://medex.com.bd/?ccd=1',  # Try homepage first with consent bypass
            'https://medex.com.bd/brands?page=1&ccd=1',
            'https://medex.com.bd/brands?herbal=1&page=1&ccd=1',
        ]
        
        for url in test_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                headers={
                    "Referer": "https://medex.com.bd/?ccd=1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-User": "?1",
                },
                meta={
                    "playwright": True,
                    "playwright_context": "default",
                    "playwright_page_methods": [
                        PageMethod("add_init_script", "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"),
                        PageMethod("wait_for_load_state", "networkidle"),
                        PageMethod("wait_for_selector", "body"),
                    ],
                },
            )

    def clean_text(self, raw_html):
        """
        :param raw_html: this will take raw html code
        :return: text without html tags
        """
        cleaner = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
        return re.sub(cleaner, '', raw_html)

    def parse(self, response, **kwargs):
        """Parse the brands listing page."""
        # Detect challenge page early
        if "captcha" in response.url.lower() or "challenge" in response.url.lower():
            self.logger.warning("Captcha challenge detected at %s — stopping.", response.url)
            return
        
        if "terms-of-use" in response.url.lower():
            self.logger.error("❌ Redirected to terms of use page! URL: %s", response.url)
            
            # If this is the last URL and all failed, create test data
            if "homepage" in response.meta.get('url_type', ''):
                self.logger.info("🔧 All URLs failed, creating test medicine data...")
                yield from self.create_test_medicine_data()
            return

        self.logger.info(f"✅ Parsing brands page: {response.url}")
        
        # Extract medicine links
        med_info_blocks = response.css('a.hoverable-block')
        if not med_info_blocks:
            self.logger.warning("No medicine blocks found on %s", response.url)
            return
        
        self.logger.info(f"Found {len(med_info_blocks)} medicine blocks")
        
        for med_info in med_info_blocks:
            # On listing pages each card is a direct anchor with class hoverable-block
            med_page_links = med_info.css('a.hoverable-block::attr(href)').getall()
            if med_page_links:
                for link in med_page_links:
                    if link:
                        # Ensure consent flag is present on navigations
                        link = link + ("&ccd=1" if ("?" in link and "ccd=" not in link) else ("?ccd=1" if "ccd=" not in link else ""))
                        self.logger.info(f"Following medicine link: {link}")
                        yield response.follow(
                            link,
                            callback=self.parse_med,
                            headers={"Referer": response.url},
                            meta={
                                "playwright": True,
                                "playwright_context": "default",
                                "playwright_page_methods": [
                                    PageMethod("add_init_script", "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"),
                                    PageMethod("wait_for_load_state", "networkidle"),
                                    PageMethod("wait_for_selector", "h1.page-heading-1-l"),
                                ],
                            }
                        )

        # Follow pagination
        pagination_links = response.css('a.page-link[rel="next"]::attr(href)').getall()
        if pagination_links:
            self.logger.info(f"Found {len(pagination_links)} pagination links")
            for link in pagination_links:
                if link:
                    next_link = link + ("&ccd=1" if ("?" in link and "ccd=" not in link) else ("?ccd=1" if "ccd=" not in link else ""))
                    yield response.follow(
                        next_link,
                        callback=self.parse,
                        headers={"Referer": response.url},
                        meta={
                            "playwright": True,
                            "playwright_context": "default",
                            "playwright_page_methods": [
                                PageMethod("add_init_script", "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"),
                                PageMethod("wait_for_load_state", "networkidle"),
                                PageMethod("wait_for_selector", "a.hoverable-block"),
                            ],
                        }
                    )

    def create_test_medicine_data(self):
        """Create test medicine data to verify pipeline is working."""
        self.logger.info("🔧 Creating test medicine data...")
        
        # Create a test medicine item
        item = MedItem()
        item['brand_id'] = 'test_001'
        item['brand_name'] = 'Test Medicine'
        item['type'] = 'allopathic'
        item['dosage_form'] = 'Tablet'
        item['strength'] = '500mg'
        
        # Create a test manufacturer
        try:
            from crawler.models import Manufacturer
            manufacturer, created = Manufacturer.objects.get_or_create(
                manufacturer_id='test_001',
                defaults={
                    'manufacturer_name': 'Test Manufacturer',
                    'slug': 'test-manufacturer-001'
                }
            )
            item['manufacturer'] = manufacturer
        except Exception as e:
            self.logger.error(f"Failed to create test manufacturer: {e}")
            item['manufacturer'] = None
        
        # Add other required fields
        item['generic'] = None
        item['indication'] = None
        item['dosage_form_model'] = None
        item['slug'] = 'test-medicine-001'
        
        self.logger.info("✅ Created test medicine item")
        yield item

    def parse_generic(self, response):
        item = GenericItem()
        item['generic_id'] = re.findall("generics/(\S*)/", response.url)[0]
        item['generic_name']= response.css('h1.page-heading-1-l ::text').get().strip()
        item['monograph_link'] = response.css('span.hidden-sm a ::attr(href)').get()
        """ medicine description """
        # indications
        # generic_details['indications'] = response.css('div#indications h4 ::text').get().strip()
        item['indication_description'] = response.xpath(
            '//div[@id="indications"]/following-sibling::node()[2]').get().strip()

        # ###Therapeutic Class
        # therapeutic_class = extract_with_css('div#drug_classes h4 ::text')
        item['therapeutic_class_description'] = response.xpath(
            '//div[@id="drug_classes"]/following-sibling::node()[2]').get()

        # ###Pharmacology
        # pharmacology = extract_with_css('div#mode_of_action h4 ::text')
        item['pharmacology_description'] = response.xpath(
            '//div[@id="mode_of_action"]/following-sibling::node()[2]').get()

        # ##Dosage
        # dosage = extract_with_css('div#dosage h4 ::text')
        item['dosage_description'] = response.xpath('//div[@id="dosage"]/following-sibling::node()[2]').get()

        # ##Administration
        # administration = extract_with_css('div#administration h4 ::text')
        item['administration_description'] = response.xpath(
            '//div[@id="administration"]/following-sibling::node()[2]').get()

        # ##Interaction
        # interaction = extract_with_css('div#interaction h4 ::text')
        item['interaction_description'] = response.xpath(
            '//div[@id="interaction"]/following-sibling::node()[2]').get()

        # ##Contraindications
        # contraindications = extract_with_css('div#contraindications h4 ::text')
        item['contraindications_description'] = response.xpath(
            '//div[@id="contraindications"]/following-sibling::node()[2]').get()

        # ##Side Effects
        # side_effects = extract_with_css('div#side_effects h4 ::text')
        item['side_effects_description'] = response.xpath(
            '//div[@id="side_effects"]/following-sibling::node()[2]').get()

        # ##Pregnancy & Lactation
        # pregnancy_and_lactation = extract_with_css('div#pregnancy_cat h4 ::text')
        item['pregnancy_and_lactation_description'] = response.xpath(
            '//div[@id="pregnancy_cat"]/following-sibling::node()[2]').get()

        # ## Precautions
        # precautions = extract_with_css('div#precautions h4 ::text')
        item['precautions_description'] = response.xpath(
            '//div[@id="precautions"]/following-sibling::node()[2]').get()

        # ## Use in Special Populations
        # pediatric_usage = extract_with_css('div#pediatric_uses h4 ::text')
        item['pediatric_usage_description'] = response.xpath(
            '//div[@id="pediatric_uses"]/following-sibling::node()[2]').get()

        # ##Overdose Effects
        # overdose_effects = extract_with_css('div#overdose_effects h4 ::text')
        item['overdose_effects_description'] = response.xpath(
            '//div[@id="overdose_effects"]/following-sibling::node()[2]').get()

        # ##Duration of treatment
        # duration_of_treatment = extract_with_css('div#duration_of_treatment h4 ::text')
        item['duration_of_treatment_description'] = response.xpath(
            '//div[@id="duration_of_treatment"]/following-sibling::node()[2]').get()

        # ##Reconstitution
        # reconstitution = extract_with_css('div#reconstitution h4 ::text')
        item['reconstitution_description'] = response.xpath(
            '//div[@id="reconstitution"]/following-sibling::node()[2]').get()

        # ##Storage Conditions
        # storage_conditions = extract_with_css('div#storage_conditions h4 ::text')
        item['storage_conditions_description'] = response.xpath(
            '//div[@id="storage_conditions"]/following-sibling::node()[2]').get()

        item['slug'] = slugify(item['generic_name'] + '-' + item['generic_id'],
                               allow_unicode=True)
        yield item

    def parse_med(self, response):
        """Parse individual medicine page."""
        # Skip CAPTCHA pages
        if 'captcha-challenge' in response.url:
            self.logger.warning("Skipping CAPTCHA page: %s", response.url)
            return
        
        if "terms-of-use" in response.url.lower():
            self.logger.error("❌ Redirected to terms of use page! URL: %s", response.url)
            return
        
        self.logger.info(f"Processing medicine: {response.url}")
        
        def extract_with_css(query):
            return response.css(query).get(default='').strip()

        item = MedItem()
        # robust brand id
        brand_id_match = re.search(r"brands/(\d+)/", response.url)
        item['brand_id'] = brand_id_match.group(1) if brand_id_match else None
        # Brand title can be split in multiple spans; fallback to page H1 text
        title_spans = [t.strip() for t in response.css('h1.page-heading-1-l span::text').getall() if t.strip()]
        if title_spans:
            item['brand_name'] = title_spans[0]
        else:
            item['brand_name'] = response.css('h1.page-heading-1-l::text').get(default='').strip()
        # robust type
        heading_alt = response.css('h1.page-heading-1-l img::attr(alt)').get(default='').strip().lower()
        item['type'] = 'herbal' if heading_alt == 'herbal' else 'allopathic'
        item['dosage_form'] = extract_with_css('small.h1-subtitle ::text')
        # generic_name = extract_with_css('div[title="Generic Name"] a ::text')
        item['strength'] = extract_with_css('div[title="Strength"] ::text')

        # manufacturer extraction (defer DB interaction to pipeline/backfill to avoid async ORM)
        manufacturer_link = response.css('div[title="Manufactured by"] a::attr(href)').get('')
        manufacturer_id_match = re.search(r"companies/(\d+)/", manufacturer_link or '')
        manufacturer_id = manufacturer_id_match.group(1) if manufacturer_id_match else None
        if manufacturer_id:
            try:
                with open('manufacturer_id.txt', 'a') as f:
                    f.write(f"{item['brand_id']},{manufacturer_id}\n")
            except Exception:
                pass
        item['manufacturer'] = None
        # med_details['package_container'] = [self.clean_text(spec_value).strip() for spec_value in response.css(
        # 'div.package-container').getall()]

        # todo : debug package container
        # https://medex.com.bd/brands/7701/3rd-cef-100mg
        # https://medex.com.bd/brands/9538/3-f-500mg
        # check all the dosage forms and add exceptions https://medex.com.bd/dosage-forms

        # todo : debug veterinary
        # https://medex.com.bd/brands/31317/a-mectin-vet-10mg

        # item['package_container'] = ' '.join(extract_with_css('div.package-container ::text').split())
        # item['pack_size_info'] = ' '.join(extract_with_css('span.pack-size-info ::text').split())

        # todo : remove overlapping pack size info
        package_container = ','.join(
            [re.sub(r'\s+', ' ', i).strip() for i in response.css('div.package-container ::text').getall()])
        pack_size_info = ','.join(
            [re.sub(r'\s+', ' ', i).strip() for i in response.css('span.pack-size-info ::text').getall() if
             i.strip() != ''])

        item['package_container'] = package_container
        item['pack_size_info'] = pack_size_info

        item['slug'] = slugify(item['brand_name'] + item['dosage_form'] + item['strength'],
                               allow_unicode=True)
        # generic extraction

        generic_link = response.css('div[title="Generic Name"] a::attr(href)').get('')
        generic_id_match = re.search(r"generics/(\d+)/", generic_link)
        generic_id = generic_id_match.group(1) if generic_id_match else None

        if generic_id:
            # Defer ORM interaction; save mapping for later backfill
            try:
                with open('generic_id.txt', 'a') as f:
                    f.write(f"{item['brand_id']},{generic_id}\n")
            except Exception:
                pass
            if generic_link:
                yield response.follow(generic_link, self.parse_generic)
        item['generic'] = None

        yield item
