from fastapi import APIRouter, HTTPException
import requests
from typing import List, Dict
import time
from concurrent.futures import ThreadPoolExecutor

router = APIRouter(prefix="/news", tags=["news"])

# Simple in-memory cache
news_cache = {
    "data": [],
    "last_updated": 0
}
CACHE_DURATION = 600  # 10 minutes

def fetch_story(story_id):
    """Worker function to fetch a single story's details."""
    try:
        item_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        res = requests.get(item_url, timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Error fetching story {story_id}: {e}")
    return None

@router.get("/latest")
async def get_latest_news():
    """
    Fetch top stories from Hacker News and filter for industry/tech trends.
    Uses parallel fetching for high performance.
    """
    global news_cache
    
    current_time = time.time()
    if news_cache["data"] and (current_time - news_cache["last_updated"] < CACHE_DURATION):
        return news_cache["data"]

    keywords = [
        "tech", "software", "developer", "hiring", "job", "career", "AI", "LLM", 
        "engineering", "coding", "startup", "recruitment", "salary", "interview", 
        "placement", "algorithm", "system design", "cloud", "aws", "google", 
        "microsoft", "apple", "nvidia", "meta", "web", "mobile", "frontend", "backend"
    ]

    try:
        # 1. Get top story IDs
        top_ids_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        response = requests.get(top_ids_url, timeout=10)
        response.raise_for_status()
        top_ids = response.json()[:80] # Check more stories for better filtering

        # 2. Parallel fetch story details
        with ThreadPoolExecutor(max_workers=20) as executor:
            raw_items = list(executor.map(fetch_story, top_ids))

        stories = []
        for item in raw_items:
            if not item: continue
            
            title = item.get("title", "").lower()
            if any(kw in title for kw in keywords):
                if item.get("type") == "story" and "url" in item:
                    stories.append({
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "score": item.get("score"),
                        "time": item.get("time"),
                        "by": item.get("by")
                    })
            
            if len(stories) >= 15: break

        # Fallback to top stories if not enough industry ones found
        if len(stories) < 5:
            for item in raw_items:
                if not item: continue
                if any(s["id"] == item.get("id") for s in stories): continue
                if item.get("type") == "story" and "url" in item:
                    stories.append({
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "score": item.get("score"),
                        "time": item.get("time"),
                        "by": item.get("by")
                    })
                if len(stories) >= 10: break

        news_cache["data"] = stories
        news_cache["last_updated"] = current_time
        return stories

    except Exception as e:
        print(f"Error fetching news: {e}")
        if news_cache["data"]: return news_cache["data"]
        raise HTTPException(status_code=500, detail="Failed to fetch industry news")
