# Scrapy settings for medexbot project
import os
from dotenv import load_dotenv

load_dotenv()

BOT_NAME = "medexbot"
SPIDER_MODULES = ["medexbot.spiders"]
NEWSPIDER_MODULE = "medexbot.spiders"

# Browser settings
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Basic settings
# MedEx blocks some automated crawlers via robots.txt and redirects to
# a Terms page. We explicitly ignore robots.txt here because we crawl
# only public catalogue pages and respect polite delays.
ROBOTSTXT_OBEY = False
COOKIES_ENABLED = True
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"

# Polite crawling
DOWNLOAD_DELAY = 1.0
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 4

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0

# Proxy setup (optional)
PROXY_HOST = os.environ.get("PROXY_HOST")
PROXY_PORT = os.environ.get("PROXY_PORT")
PROXY_USER = os.environ.get("PROXY_USER")
PROXY_PASSWORD = os.environ.get("PROXY_PASSWORD")

# Middlewares and pipelines
DOWNLOADER_MIDDLEWARES = {
    "medexbot.proxy_middlewares.ProxyMiddleware": 350,
}

ITEM_PIPELINES = {
    "medexbot.pipelines.MedexbotPipeline": 300,
}

# Optional Playwright integration (enabled for this project)
ENABLE_PLAYWRIGHT = True  # Required for medex.com.bd scraping

if ENABLE_PLAYWRIGHT:
    try:
        import scrapy_playwright
        TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
        DOWNLOAD_HANDLERS = {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler", 
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        }
        PLAYWRIGHT_BROWSER_TYPE = "chromium"
        PLAYWRIGHT_LAUNCH_OPTIONS = {
            "headless": False,  # Use visible browser instead of headless
            "channel": "chrome",  # Use Chrome instead of Chromium
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=VizDisplayCompositor",
            ]
        }
        PLAYWRIGHT_CONTEXTS = {
            "default": {
                "storage_state": "playwright_state.json",
                "user_agent": USER_AGENT,
                "locale": "en-US",
                "viewport": {"width": 1366, "height": 768},
                "extra_http_headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
                "java_script_enabled": True,
                "accept_downloads": False,
                "ignore_https_errors": False,
            }
        }
        
        # Playwright specific settings for better CAPTCHA handling
        PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000  # 60 seconds
    except ImportError:
        pass

LOG_LEVEL = "INFO"
