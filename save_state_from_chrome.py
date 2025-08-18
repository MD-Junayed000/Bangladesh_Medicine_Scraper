#!/usr/bin/env python
"""
Save Session State from Your Local Chrome Browser
Extracts cookies and session data from your real Chrome browser.
"""
import os
import json
import sqlite3
import time
from pathlib import Path
import sys

def find_chrome_profile_path():
    """Find Chrome user data directory."""
    username = os.getenv('USERNAME')
    possible_paths = [
        f"C:/Users/{username}/AppData/Local/Google/Chrome/User Data/Default",
        f"C:/Users/{username}/AppData/Local/Google/Chrome/User Data/Profile 1",
        f"C:/Users/{username}/AppData/Local/Google/Chrome/User Data",
    ]
    
    for path in possible_paths:
        cookies_path = Path(path) / "Cookies"
        if cookies_path.exists():
            return Path(path)
    
    return None

def extract_medex_cookies():
    """Extract medex.com.bd cookies from Chrome."""
    profile_path = find_chrome_profile_path()
    
    if not profile_path:
        print("❌ Chrome profile not found")
        return None
    
    cookies_db = profile_path / "Cookies"
    
    if not cookies_db.exists():
        print(f"❌ Cookies database not found: {cookies_db}")
        return None
    
    print(f"🔍 Found Chrome profile: {profile_path}")
    print(f"📂 Cookies database: {cookies_db}")
    
    # Copy cookies database (Chrome locks it when running)
    import shutil
    temp_cookies = "temp_cookies.db"
    
    try:
        shutil.copy2(cookies_db, temp_cookies)
        print("✅ Copied cookies database")
    except Exception as e:
        print(f"❌ Cannot copy cookies database: {e}")
        print("💡 Close Chrome and try again, or use the manual method")
        return None
    
    try:
        # Connect to cookies database
        conn = sqlite3.connect(temp_cookies)
        cursor = conn.cursor()
        
        # Query medex.com.bd cookies
        query = """
        SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly, samesite
        FROM cookies 
        WHERE host_key LIKE '%medex.com.bd%'
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        cookies = []
        for row in rows:
            name, value, domain, path, expires, secure, httponly, samesite = row
            
            # Convert Chrome timestamp to seconds
            expires_seconds = expires / 1000000 - 11644473600 if expires else -1
            
            cookie = {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
                "expires": expires_seconds,
                "httpOnly": bool(httponly),
                "secure": bool(secure),
                "sameSite": "Strict" if samesite == 1 else "Lax" if samesite == 2 else "None"
            }
            cookies.append(cookie)
        
        conn.close()
        os.remove(temp_cookies)  # Clean up
        
        print(f"✅ Extracted {len(cookies)} medex.com.bd cookies")
        return cookies
        
    except Exception as e:
        print(f"❌ Failed to extract cookies: {e}")
        if os.path.exists(temp_cookies):
            os.remove(temp_cookies)
        return None

def save_playwright_state(cookies):
    """Save cookies in Playwright format."""
    if not cookies:
        print("❌ No cookies to save")
        return False
    
    playwright_state = {
        "cookies": cookies,
        "origins": []
    }
    
    try:
        with open("playwright_state.json", "w") as f:
            json.dump(playwright_state, f, indent=2)
        
        print("✅ Saved session state to playwright_state.json")
        print(f"📊 {len(cookies)} cookies saved")
        
        # Show cookie summary
        for cookie in cookies[:3]:  # Show first 3
            print(f"   🍪 {cookie['name']}: {cookie['value'][:20]}...")
        
        if len(cookies) > 3:
            print(f"   ... and {len(cookies) - 3} more cookies")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to save state: {e}")
        return False

def manual_cookie_extraction():
    """Manual method using browser dev tools."""
    print("\n🔧 MANUAL COOKIE EXTRACTION")
    print("=" * 40)
    print()
    print("If automatic extraction failed, use this manual method:")
    print()
    print("1. Open Chrome and go to https://medex.com.bd/companies")
    print("2. Solve any CAPTCHA if it appears")
    print("3. Press F12 to open Developer Tools")
    print("4. Go to Application tab → Storage → Cookies → https://medex.com.bd")
    print("5. Copy all cookie values")
    print()
    print("🍪 Key cookies to look for:")
    print("   - medex_session")
    print("   - XSRF-TOKEN") 
    print("   - __m_cache_uis")
    print("   - __m_cache_uf")
    print("   - _ga")
    print()
    print("6. Create playwright_state.json manually with these cookies")

def test_session_state():
    """Test if the saved session state works."""
    if not os.path.exists("playwright_state.json"):
        print("❌ No playwright_state.json found")
        return False
    
    try:
        with open("playwright_state.json", "r") as f:
            state = json.load(f)
        
        cookies = state.get("cookies", [])
        print(f"🔍 Testing session state with {len(cookies)} cookies")
        
        # Quick test with requests
        import requests
        session = requests.Session()
        
        for cookie in cookies:
            session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain", ""),
                path=cookie.get("path", "/")
            )
        
        # Test request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }
        
        response = session.get("https://medex.com.bd/companies?page=1", headers=headers, timeout=10)
        content_lower = response.text.lower()
        
        if 'captcha' in content_lower or 'challenge' in content_lower:
            print("🛡️ CAPTCHA still detected - session may be expired")
            return False
        else:
            print("✅ Session state appears to be working!")
            return True
            
    except Exception as e:
        print(f"❌ Failed to test session: {e}")
        return False

def main():
    """Main function."""
    print("🍪 EXTRACT COOKIES FROM LOCAL CHROME")
    print("=" * 50)
    print()
    print("This will extract medex.com.bd cookies from your Chrome browser")
    print("and save them for Playwright to use.")
    print()
    
    # Step 1: Extract cookies
    print("🔍 Extracting cookies from Chrome...")
    cookies = extract_medex_cookies()
    
    if cookies:
        # Step 2: Save state
        print("\n💾 Saving session state...")
        success = save_playwright_state(cookies)
        
        if success:
            # Step 3: Test state
            print("\n🧪 Testing session state...")
            if test_session_state():
                print("\n🎉 SUCCESS! Session state is ready for scraping")
                print("\n📝 Next steps:")
                print("   python run_scrapy_with_playwright.py manufacturer")
                print("   python run_crawler.py")
            else:
                print("\n⚠️ Session state saved but may need refresh")
                print("💡 Navigate to medex.com.bd in Chrome and solve any CAPTCHA")
        else:
            print("\n❌ Failed to save session state")
    else:
        print("\n❌ Cookie extraction failed")
        manual_cookie_extraction()

if __name__ == "__main__":
    main()
