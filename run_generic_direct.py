#!/usr/bin/env python
"""
Direct runner for generic spider without Playwright dependencies.
Uses the converted generic spider with direct requests.
"""
import os
import sys
import django

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Now run the spider directly
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from medexbot.spiders.generic_spider import GenericSpider

def run_generic_spider():
    """Run the generic spider with direct requests."""
    
    print("🏥 BANGLADESH MEDICINE SCRAPER")
    print("🌐 Direct Request Mode - No Playwright!")
    print("=" * 50)
    
    # Get project settings but override Playwright settings
    settings = get_project_settings()
    
    # Disable Playwright completely
    settings.set('DOWNLOAD_HANDLERS', {})
    settings.set('TWISTED_REACTOR', None)
    
    # Enable our pipeline for database saving
    settings.set('ITEM_PIPELINES', {
        'medexbot.pipelines.MedexbotPipeline': 300,
    })
    
    # Set reasonable delays
    settings.set('DOWNLOAD_DELAY', 1)
    settings.set('RANDOMIZE_DOWNLOAD_DELAY', 0.5)
    settings.set('CONCURRENT_REQUESTS', 2)
    
    print("🔧 Settings configured for direct requests")
    print("✅ Database pipeline enabled")
    print("⏱️  Download delay: 1-1.5 seconds")
    print("🚀 Starting generic spider...")
    print()
    
    try:
        # Create crawler process
        process = CrawlerProcess(settings)
        
        # Add our spider
        process.crawl(GenericSpider)
        
        # Start crawling
        process.start()
        
        print("\n✅ Generic spider completed successfully!")
        print("💾 Check Django admin for scraped data")
        
    except Exception as e:
        print(f"\n❌ Error running spider: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = run_generic_spider()
    
    if success:
        print("\n🎉 All done! Check your database for generic data.")
    else:
        print("\n💥 Something went wrong. Check the error messages above.")
