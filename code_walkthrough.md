# Project Code Walkthrough: Line-by-Line Logic

This guide explores the most critical code sections in your project, explaining exactly what happens in each block.

---

## 🟢 BACKEND: `backend/news_routes.py`
This file handles the Fetching and AI Summarization of industry news.

```python
# Line 1-7: Imports
# We import FastAPI for the router, requests for network calls, 
# and ollama for the AI model interaction.
from fastapi import APIRouter, HTTPException
import requests
import ollama

# Line 11-15: Caching logic
# We store news in-memory for 10 minutes (600s) to avoid
# hitting Hacker News and Ollama too frequently.
news_cache = {"data": [], "last_updated": 0}

# Line 30-50: The News Fetcher
# This function calls the HackerNews API.
# It uses keywords like "tech", "AI", "placement" to 
# filter out irrelevant stories and keep only career-focused news.

# Line 106: The AI Summary Endpoint
@router.post("/summary")
def get_news_summary(request: SummaryRequest):
    # This is the CORE AI logic. 
    # It sends the news title to Llama 3.1 with a strict prompt:
    # "Summarize into a single concise, professional sentence..."
    response = ollama.generate(
        model='llama3.1:latest',
        prompt=prompt,
        options={'num_predict': 100, 'temperature': 0.7}
    )
    # The 'temperature: 0.7' allows for creative but professional language.
```

---

## 🔵 FRONTEND: `lib/widgets/news_notification.dart`
This defines the popup that appears on the side of the screen.

```dart
// Line 20-35: Animation Logic
// Defines a SlideTransition. 
// begin: Offset(1.5, 0.0) means it starts off-screen to the right.
// end: Offset.zero means it ends at its natural position.
// curve: Curves.easeOutBack gives it a "bouncy" premium feel.

// Line 74: The Read Summary Logic
Future<void> _handleRead() async {
  // 1. Check if summary is already fetched.
  // 2. If not, call ApiConfig.fetchNewsSummary(title).
  // 3. Once received, use widget.onRead(summary) which triggers TTS.
}

// Line 110: UI Construction
// Uses a Column within a Container.
// BoxShadow is added (blurRadius: 15) to make it look floating and premium.
// Border.all uses purpleAccent with opacity to match the theme.
```

---

## 🟢 BACKEND: `backend/main.py`
This is the main entry point and setup.

```python
# Line 59: Whisper Model Loading
# We load the 'base' model of Whisper. 
# It's balanced for speed and accuracy on local machines.
stt_model = whisper.load_model("base")

# Line 191: get_todays_questions
# This logic ensures students don't get the same questions twice.
# 1. It checks the 'daily_quiz' table for a cached set.
# 2. If empty, it pulls 10 random questions from the 'questions' table
#    based on the user's difficulty level (Easy/Medium/Hard).
# 3. It filters by 'branch' (CSE, EEE, MECH, etc.).

# Line 670: get_daily_quiz
# When a student starts a quiz, this endpoint is called.
# It triggers 'ensure_explanations_exist' as a BACKGROUND TASK.
# This means the user gets their quiz immediately, while the AI
# generates explanations in the background for them to see later.
```

---

## 🔵 FRONTEND: `lib/screens/dashboard_screen.dart`
The central dashboard with dynamic updates.

```dart
// Line 33-45: Initialization
// 1. loadData() fetches user stats (level, points).
// 2. _showTrendsPopup() shows the big news dialog once.
// 3. _startNewsTimer() begins the 5-minute counter for popups.

// Line 55: The 5-Minute Timer
void _startNewsTimer() {
  _newsTimer = Timer.periodic(const Duration(minutes: 5), (timer) {
    // Every 5 minutes, it moves to the next news item index
    // and calls _showNewsNotification(item).
  });
}

// Line 70: The Overlay logic
// Custom OverlayEntry allows the popup to "float" over the dashboard
// without being blocked by other views or dialogs.
```

---

### Summary for your Evaluators:
*   **Separation of Concerns**: We use a clean separation between the data (MySQL), the brain (FastAPI/AI), and the presentation (Flutter).
*   **Scalability**: Async background tasks in Python ensure the system stays fast even with complex AI operations.
*   **User Experience**: Animations and TTS (Text-to-Speech) make the application accessible and modern.
