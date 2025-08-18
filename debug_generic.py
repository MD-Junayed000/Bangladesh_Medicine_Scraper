#!/usr/bin/env python
"""
Debug script to see what's happening with generic spider requests
"""
import os
import json
import requests

# Set up Django first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from scrapy.http import Request
from scrapy.utils.test import get_crawler
from medexbot.spiders.generic_spider import GenericSpider

def debug_generic_spider():
    """Debug the generic spider step by step."""
    
    print("🔍 DEBUGGING GENERIC SPIDER")
    print("=" * 40)
    
    # Load cookies
    with open('playwright_state.json', 'r') as f:
        state = json.load(f)
    
    cookies = state.get('cookies', [])
    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
    
    print(f"🍪 Loaded {len(cookies)} cookies")
    print("Cookie names:", list(cookie_dict.keys()))
    
    # Test direct request first
    print("\n🌐 Testing direct request...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://medex.com.bd/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    response = requests.get(
        'https://medex.com.bd/generics?page=1',
        cookies=cookie_dict,
        headers=headers
    )
    
    print(f"📊 Direct request status: {response.status_code}")
    print(f"📏 Content length: {len(response.text)}")
    print(f"🔒 Contains captcha: {'captcha' in response.text.lower()}")
    print(f"💊 Contains generic: {'generic' in response.text.lower()}")
    
    if 'captcha' not in response.text.lower():
        print("✅ Direct request works!")
        
        # Now test with Scrapy request
        print("\n🕷️ Testing Scrapy request...")
        
        # Create a mock spider
        crawler = get_crawler()
        spider = GenericSpider()
        spider._set_crawler(crawler)
        
        # Create a request like the spider would
        req = Request(
            'https://medex.com.bd/generics?page=1',
            cookies=cookie_dict,
            headers=headers,
            meta={'cookies': cookie_dict, 'headers': headers}
        )
        
        print(f"🔗 Request URL: {req.url}")
        print(f"🍪 Request cookies: {req.cookies}")
        print(f"📋 Request headers: {dict(req.headers)}")
        print(f"📝 Request meta: {req.meta}")
        
        # Test if the request would work
        print("\n💡 The issue might be:")
        print("   1. Scrapy's default headers are being detected")
        print("   2. The site is checking for automation patterns")
        print("   3. Cookies need to be refreshed")
        
    else:
        print("❌ Direct request also fails - cookies might be expired")

if __name__ == '__main__':
    debug_generic_spider()
