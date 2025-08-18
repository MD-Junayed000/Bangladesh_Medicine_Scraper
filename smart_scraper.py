#!/usr/bin/env python
"""
Smart Scraper with CAPTCHA Detection and Bypass
Handles both CAPTCHA-protected and regular pages intelligently.
"""
import os
import sys
import json
import time
import requests
from pathlib import Path

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

# Import after Django setup
from crawler.models import Manufacturer, Generic, Medicine, DrugClass, DosageForm, Indication

class SmartScraper:
    """Intelligent scraper that handles CAPTCHA and non-CAPTCHA pages."""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://medex.com.bd"
        self.state_file = "playwright_state.json"
        self.load_session_state()
        
    def load_session_state(self):
        """Load cookies from playwright state if available."""
        if Path(self.state_file).exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    
                # Extract cookies from playwright state
                cookies = state.get('cookies', [])
                for cookie in cookies:
                    self.session.cookies.set(
                        name=cookie['name'],
                        value=cookie['value'],
                        domain=cookie.get('domain', ''),
                        path=cookie.get('path', '/')
                    )
                print(f"✅ Loaded {len(cookies)} cookies from saved state")
                
            except Exception as e:
                print(f"⚠️  Could not load session state: {e}")
    
    def check_captcha_required(self, url):
        """Check if a URL requires CAPTCHA by making a test request."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = self.session.get(url, headers=headers, timeout=10)
            content = response.text.lower()
            
            # Check for CAPTCHA indicators
            captcha_indicators = [
                'captcha-challenge',
                'cloudflare',
                'challenge',
                'verify you are human',
                'just a moment',
                'checking your browser'
            ]
            
            has_captcha = any(indicator in content for indicator in captcha_indicators)
            
            if has_captcha:
                print(f"🛡️  CAPTCHA detected at {url}")
                return True
            else:
                print(f"✅ No CAPTCHA at {url}")
                return False
                
        except Exception as e:
            print(f"❌ Error checking {url}: {e}")
            return True  # Assume CAPTCHA if we can't check
    
    def scrape_without_captcha(self, url):
        """Scrape pages that don't require CAPTCHA using requests."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            response = self.session.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"✅ Successfully scraped {url} without CAPTCHA")
                return response.text
            else:
                print(f"❌ Failed to scrape {url}: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
            return None
    
    def test_endpoints(self):
        """Test different endpoints to see which require CAPTCHA."""
        endpoints = [
            f"{self.base_url}/companies",
            f"{self.base_url}/companies?page=1", 
            f"{self.base_url}/generics",
            f"{self.base_url}/generics?page=1",
            f"{self.base_url}/medicines",
            f"{self.base_url}/medicines?page=1",
            f"{self.base_url}/drug-classes",
            f"{self.base_url}/indications",
            f"{self.base_url}/dosage-forms",
        ]
        
        results = {}
        
        print("🔍 Testing endpoints for CAPTCHA requirements...")
        print("=" * 60)
        
        for endpoint in endpoints:
            requires_captcha = self.check_captcha_required(endpoint)
            results[endpoint] = requires_captcha
            time.sleep(1)  # Be polite
            
        print("\n📊 CAPTCHA Test Results:")
        print("=" * 60)
        
        captcha_free = []
        captcha_required = []
        
        for url, needs_captcha in results.items():
            if needs_captcha:
                print(f"🛡️  CAPTCHA: {url}")
                captcha_required.append(url)
            else:
                print(f"✅ FREE:    {url}")
                captcha_free.append(url)
        
        print(f"\n📈 Summary:")
        print(f"   ✅ CAPTCHA-Free URLs: {len(captcha_free)}")
        print(f"   🛡️  CAPTCHA-Required URLs: {len(captcha_required)}")
        
        return results
    
    def validate_session_state(self):
        """Validate if our saved session state is still working."""
        test_url = f"{self.base_url}/companies?page=1"
        
        print("🔍 Validating session state...")
        
        # First check with our loaded session
        requires_captcha = self.check_captcha_required(test_url)
        
        if not requires_captcha:
            print("✅ Session state is valid - no CAPTCHA required!")
            return True
        else:
            print("❌ Session state expired or invalid - CAPTCHA required")
            return False
    
    def recommend_strategy(self):
        """Recommend the best scraping strategy based on current state."""
        print("\n🎯 SCRAPING STRATEGY RECOMMENDATIONS")
        print("=" * 60)
        
        # Test session validity
        session_valid = self.validate_session_state()
        
        if session_valid:
            print("✅ RECOMMENDED: Use HTTP requests scraping")
            print("   - Your session state is working")
            print("   - No CAPTCHA challenges detected")
            print("   - Faster and more efficient")
            print("\n📝 Commands to try:")
            print("   python smart_scraper.py --scrape manufacturers")
            print("   python smart_scraper.py --scrape generics")
            
        else:
            print("🛡️  RECOMMENDED: Update session state first")
            print("   - Current session has expired")
            print("   - CAPTCHA challenges detected")
            print("   - Need to refresh authentication")
            print("\n📝 Commands to run:")
            print("   1. python save_medex_state.py")
            print("   2. Solve any CAPTCHA manually")
            print("   3. python smart_scraper.py --validate")
            
        # Test individual endpoints
        print("\n🔍 Testing individual endpoints...")
        results = self.test_endpoints()
        
        return session_valid, results

def main():
    """Main function to run smart scraper analysis."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        scraper = SmartScraper()
        
        if command == "--validate":
            scraper.validate_session_state()
        elif command == "--test":
            scraper.test_endpoints()
        elif command == "--recommend":
            scraper.recommend_strategy()
        else:
            print("Available commands:")
            print("  --validate    Check if session state is working")
            print("  --test       Test all endpoints for CAPTCHA")
            print("  --recommend  Get scraping strategy recommendations")
    else:
        # Default: run full analysis
        scraper = SmartScraper()
        scraper.recommend_strategy()

if __name__ == "__main__":
    main()
