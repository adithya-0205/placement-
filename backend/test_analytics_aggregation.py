import sys
import os
import json
from datetime import datetime, timedelta

# Mocking database and fastapi dependencies for a simple unit-like test of the aggregation logic
# Alternatively, we can use the actual DB if it's running, but let's try a direct logic check if possible.
# Since the logic is tied to DB queries, we'll try to run a subset or just verify the endpoint exists and returns 200 via requests if the server is up.

import requests

def test_weekly_report_api():
    username = "Student" # Adjust if a specific user exists
    url = f"http://localhost:8000/weekly_report/{username}"
    
    try:
        print(f"Testing API: {url}")
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("API Response Structure:")
            print(json.dumps(data, indent=2))
            
            # Basic validation of keys
            expected_keys = ["has_data", "aptitude_daily", "technical_daily", "gd_weekly", "interview_weekly", "status", "current_performance"]
            for key in expected_keys:
                if key in data:
                    print(f"✅ Key found: {key}")
                else:
                    print(f"❌ Key missing: {key}")
        else:
            print(f"❌ API test failed with status code {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error during API test: {e}")

if __name__ == "__main__":
    # Check if the server is running first
    try:
        requests.get("http://localhost:8000/", timeout=2)
        test_weekly_report_api()
    except:
        print("⚠️ FastAPI server is not running on http://localhost:8000. Skipping live API test.")
        print("Please start the server with 'python backend/main.py' to run this test.")
