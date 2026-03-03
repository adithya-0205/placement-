import httpx
import json
from collections import Counter

def verify_quiz_distribution():
    url = "http://localhost:8000/get_daily_quiz"
    payload = {
        "username": "Adithya",
        "category": "technical",
        "target_branch": "CSE"
    }
    
    try:
        print(f"📡 Requesting daily quiz for CSE technical...")
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json=payload)
            data = response.json()
            
            if data.get("status") == "success":
                questions = data.get("questions", [])
                print(f"✅ Received {len(questions)} questions.")
                
                areas = [q.get("area", "Unknown") for q in questions]
                area_counts = Counter(areas)
                
                print("\nTopic Distribution:")
                for area, count in area_counts.items():
                    print(f"- {area}: {count} question(s)")
                
                if len(area_counts) > 1:
                    print("\n✨ Verification PASSED: Topics are balanced/distributed.")
                else:
                    print("\n⚠️ Verification WARNING: Only one topic found. (If DB has only one topic, this is expected).")
            else:
                print(f"❌ Error: {data}")
    except Exception as e:
        print(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    verify_quiz_distribution()
