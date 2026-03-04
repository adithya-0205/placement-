# Master Presentation Guide: AI Placement Assistant

Use this guide to explain your project's technical depth, workflows, and innovation to your evaluators.

---

## 🏗️ 1. The Technology Stack (The Foundation)
Explain **why** you chose these technologies:
- **Frontend**: **Flutter (Dart)** - Chosen for a premium, single-codebase UI that feels like a native desktop/mobile app.
- **Backend**: **FastAPI (Python)** - The fastest Python framework specifically suited for handling asynchronous AI tasks (Ollama/Whisper).
- **Database**: **MySQL** - Transitioned from SQLite to MySQL to support multi-user concurrency and better data integrity.
- **AI Brain**: **Local Llama 3 (via Ollama)** - Ensures data privacy and offline capability; no API costs or latency issues.
- **State Management**: **Provider** - Used to maintain a seamless user session (Login -> Dashboard -> Quiz).

---

## 🔄 2. Core Workflows (How it Works)

### Workflow A: Adaptive Learning Engine
1.  **Student** takes a Daily Quiz (10 questions).
2.  **FastAPI** fetches questions based on the user's current level (Easy/Medium/Hard).
3.  **MySQL** stores only the **first attempt** for analytics.
4.  **Evaluation**: If the average score stays >7.0 across 7 days, the system triggers a **Level Up**.

### Workflow B: AI Industry Awareness
1.  **News Fetch**: The backend uses **Parallel Threading** (`ThreadPoolExecutor`) to fetch 80+ headlines from Hacker News in <2 seconds.
2.  **Filtering**: A custom keyword algorithm extracts only placement-relevant tech news.
3.  **AI Summarization**: **Llama 3** processes the titles to create a 3-sentence "Industry Briefing."
4.  **Audio**: **Flutter TTS** reads the briefing to provide an eyes-free learning experience.

---

## ⚡ 3. Technical Refinements & Techniques
*Highlight these to show your technical expertise:*

### 🔹 Technique 1: Parallel News Processing
> "Instead of fetching news one by one, I implemented a **ThreadPoolExecutor** with 20 workers. This reduced the data fetching time by 90%, making the dashboard feel instant."

### 🔹 Technique 2: Strict Weekly Analytics mapping
> "To prevent data confusion, I built a custom **X-axis mapping logic**. The graphs strictly follow the Monday-to-Sunday timeline. If today is Wednesday, the graph line only draws up to 'Wed', preventing future plotting and ensuring real-time accuracy."

### 🔹 Technique 3: MySQL Connection Pooling
> "I implemented **SQLAlchemy Connection Pooling** and event listeners to prevent 'MySQL Gone Away' errors during long idle periods, ensuring the server stays stable 24/7."

---

## 🗣️ 4. The "WOW" Demo Script (Talk Track)

| Step | What to Show | What to Say |
| :--- | :--- | :--- |
| **Intro** | Dashboard | *"Welcome to the AI Placement Assistant. Here you see a holistic view of a student's readiness, including their current streak and progress level."* |
| **AI News** | News Popup | *"Under the hood, we are fetching real-time data from Hacker News. Observe the 'Trends Briefing'—that is not static text. Our local AI model, Llama 3, just synthesized those headlines into a professional summary."* |
| **Analytics** | Performance Chart | *"Notice the growth profile. We separate Technical and Aptitude marks into two distinct lines. This isn't just raw data; it's strictly filtered for first attempts to show the student's true learning curve."* |
| **Quiz** | Adaptive Quiz | *"The quiz engine is adaptive. As the student performs better, the questions automatically shift from Easy to Hard, mimicking real placement difficulty levels."* |

---

## ❓ 5. Anticipated Questions
- **Q: Why run AI locally?**
  - **A:** *"Scalability and Privacy. By using Ollama and Llama 3 locally, we eliminate dependency on expensive APIs and keep all student performance data inside our own server infrastructure."*
- **Q: How do you handle branch-specific questions?**
  - **A:** *"We have a mapping layer. For example, AEI students are automatically served ECE-technical questions, ensuring their preparation is branch-aligned even with common datasets."*
