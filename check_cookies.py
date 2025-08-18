#!/usr/bin/env python
import json
from datetime import datetime

# Load cookies
with open('playwright_state.json', 'r') as f:
    data = json.load(f)

print("🍪 Cookie Expiry Check")
print("=" * 30)

for cookie in data['cookies']:
    name = cookie['name']
    expires = cookie['expires']
    
    if expires == -1:
        status = "Session cookie (no expiry)"
    else:
        # Convert timestamp to readable date
        expiry_date = datetime.fromtimestamp(expires)
        now = datetime.now()
        
        if expiry_date > now:
            status = f"Valid until {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            status = f"EXPIRED on {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}"
    
    print(f"{name}: {status}")

print(f"\n📅 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
