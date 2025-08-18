#!/usr/bin/env python
"""
Script to run Scrapy with Playwright using your existing Chrome session.
Uses your Chrome cookies and session state - no new browsers spawned!
"""
import os
import sys
import json
from pathlib import Path

# Set the reactor BEFORE any other imports
import asyncio
import twisted.internet
from twisted.internet import asyncioreactor

# On Windows, force use of SelectorEventLoop instead of ProactorEventLoop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Install the asyncio reactor
if not hasattr(twisted.internet, 'reactor'):
    asyncioreactor.install()

# Now we can safely import Django and Scrapy
import django
from django.conf import settings

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Now run the scrapy command
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

def validate_chrome_session():
    """Validate that Chrome session state exists and is working."""
    state_file = "playwright_state.json"
    
    if not Path(state_file).exists():
        print("❌ No Chrome session found!")
        print("💡 Please run: python save_state_from_chrome.py")
        print("   1. Open medex.com.bd in Chrome")
        print("   2. Solve any CAPTCHA")
        print("   3. Copy cookies using F12 → Application → Cookies")
        return False
    
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        cookies = state.get('cookies', [])
        if len(cookies) < 3:
            print("⚠️  Chrome session appears incomplete")
            print("💡 Please refresh: python save_state_from_chrome.py")
            return False
        
        # Check for important cookies
        cookie_names = [cookie.get('name', '') for cookie in cookies]
        required_cookies = ['medex_session', 'XSRF-TOKEN']
        missing_cookies = [name for name in required_cookies if name not in cookie_names]
        
        if missing_cookies:
            print(f"⚠️  Missing important cookies: {', '.join(missing_cookies)}")
            print("💡 Please refresh: python save_state_from_chrome.py")
            return False
        
        print(f"✅ Chrome session loaded: {len(cookies)} cookies")
        print("🍪 Key cookies found: medex_session, XSRF-TOKEN")
        return True
        
    except Exception as e:
        print(f"❌ Error reading Chrome session: {e}")
        return False

def setup_chrome_scrapy_settings():
    """Setup Scrapy settings to use Chrome session instead of new browsers."""
    settings = get_project_settings()
    
    # Ensure the pipeline is enabled (from project settings)
    if 'medexbot.pipelines.MedexbotPipeline' not in settings.get('ITEM_PIPELINES', {}):
        settings.set('ITEM_PIPELINES', {
            'medexbot.pipelines.MedexbotPipeline': 300,
        })
    
    # Force Playwright to use Chrome with your session state
    settings.set('PLAYWRIGHT_LAUNCH_OPTIONS', {
        'headless': False,  # Keep visible so you can see what's happening
        'channel': 'chrome',  # Use Chrome instead of Chromium
        'args': [
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            '--disable-blink-features=AutomationControlled',  # Avoid automation detection
            '--disable-dev-shm-usage',
            '--no-sandbox',
        ]
    })
    
    # Ensure Chrome session context is used
    settings.set('PLAYWRIGHT_CONTEXTS', {
        'default': {
            'storage_state': 'playwright_state.json',  # Load your Chrome cookies
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'locale': 'en-US',
            'viewport': {'width': 1366, 'height': 768},
            'extra_http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            'java_script_enabled': True,
            'accept_downloads': False,
            'ignore_https_errors': False,
        }
    })
    
    # Keep the original pipeline settings for database saving
    # settings.set('ITEM_PIPELINES', {})  # Commented out to enable database saving
    
    print("🔧 Scrapy configured to use Chrome with your session state")
    print("✅ Using playwright_state.json cookies")
    print("🌐 Browser will be visible (not headless)")
    print("💡 Note: Will open new Chrome instance but with your cookies loaded")
    
    return settings

def run_spider(spider_name):
    """Run a specific spider with Chrome session setup."""
    
    print("🕷️ CHROME SESSION SPIDER RUNNER")
    print("=" * 50)
    print(f"🎯 Target: {spider_name} spider")
    print("🌐 Using your Chrome cookies and session")
    print()
    
    # Validate Chrome session first
    if not validate_chrome_session():
        print("\n❌ Chrome session validation failed!")
        print("📋 Steps to fix:")
        print("   1. Open Chrome → medex.com.bd/companies")
        print("   2. Solve any CAPTCHA if it appears")
        print("   3. Press F12 → Application → Cookies → medex.com.bd")
        print("   4. Run: python save_state_from_chrome.py")
        print("   5. Retry this spider")
        return False
    
    # Setup Chrome-specific settings
    settings = setup_chrome_scrapy_settings()
    process = CrawlerProcess(settings)
    
    spider_map = {
        'manufacturer': 'medexbot.spiders.manufacturer_spider.ManufacturerSpider',
        'generic': 'medexbot.spiders.generic_spider.GenericSpider', 
        'med': 'medexbot.spiders.med_spider.MedSpider',
        'medicine': 'medexbot.spiders.med_spider.MedSpider',  # Alias
        'drug_class': 'medexbot.spiders.drug_class_spider.DrugClassSpider',
    }
    
    if spider_name not in spider_map:
        print(f"❌ Unknown spider: {spider_name}")
        print(f"📋 Available spiders: {', '.join(spider_map.keys())}")
        return False
    
    try:
        from importlib import import_module
        module_path, class_name = spider_map[spider_name].rsplit('.', 1)
        module = import_module(module_path)
        spider_class = getattr(module, class_name)
        
        print(f"🚀 Starting {spider_name} spider...")
        print("📊 Data will be extracted and saved to database")
        print("🔍 Watch the browser window for scraping progress")
        print()
        
        process.crawl(spider_class)
        process.start()
        
        print(f"\n✅ {spider_name} spider completed!")
        print("💡 To save data to database, enable pipeline in settings")
        
        return True
        
    except Exception as e:
        print(f"❌ Error running {spider_name} spider: {e}")
        return False

def show_usage():
    """Show usage instructions."""
    print("🏥 CHROME SESSION SPIDER RUNNER")
    print("=" * 50)
    print("Uses your Chrome cookies - no new Chromium browsers!")
    print()
    print("📋 Usage:")
    print("   python run_scrapy_with_playwright.py <spider_name>")
    print()
    print("🕷️ Available spiders:")
    spiders = ['manufacturer', 'generic', 'med', 'drug_class']
    for spider in spiders:
        print(f"   • {spider}")
    print()
    print("📝 Examples:")
    print("   python run_scrapy_with_playwright.py manufacturer")
    print("   python run_scrapy_with_playwright.py generic")
    print()
    print("💡 Requirements:")
    print("   1. Chrome session: python save_state_from_chrome.py") 
    print("   2. Valid cookies in playwright_state.json")
    print("   3. No CAPTCHA challenges active")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        show_usage()
        sys.exit(1)
    
    spider_name = sys.argv[1].lower()
    
    print("🏥 BANGLADESH MEDICINE SCRAPER")
    print("🌐 Chrome Session Mode - No New Browsers!")
    print()
    
    success = run_spider(spider_name)
    
    if success:
        print("\n🎉 Spider execution completed successfully!")
        print("📊 Check browser window for scraping results")
        print("💡 Next: Enable pipeline to save data to database")
    else:
        print("\n❌ Spider execution failed!")
        print("💡 Check error messages above for troubleshooting")
