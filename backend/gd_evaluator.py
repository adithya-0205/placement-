import json
import re
import ollama
import librosa


# ---------------------------
# SILENCE DETECTION
# ---------------------------

def is_silent_audio(audio_path: str) -> bool:
    """Check if audio file contains meaningful speech"""
    try:
        y, sr = librosa.load(audio_path, sr=None)
        intervals = librosa.effects.split(y, top_db=25)
        speech_time = sum((end - start) / sr for start, end in intervals)
        return speech_time < 1.0  # less than 1 sec speech = silent
    except Exception as e:
        print(f"Error analyzing audio: {e}")
        return True


def is_silent_transcript(transcript: str) -> bool:
    """Check if transcript contains meaningful content"""
    if not transcript:
        return True
    words = transcript.strip().split()
    return len(words) < 3


# ---------------------------
# OLLAMA RUNNER
# ---------------------------

def run_ollama(prompt: str) -> str:
    """
    Call Ollama API with the given prompt.
    Returns the model's response.
    """
    try:
        response = ollama.generate(
            model='llama3',
            prompt=prompt
        )
        return response['response'].strip()
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        raise


# ---------------------------
# JSON EXTRACTION (ROBUST)
# ---------------------------

def extract_json(text: str) -> dict:
    """
    Extracts the FIRST valid JSON object from model output.
    Handles extra whitespace, newlines, or text.
    """
    # Try to find JSON object in the text
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"No JSON found in response.\nRaw output:\n{text}")

    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in response.\nRaw output:\n{text}") from e


# ---------------------------
# MAIN EVALUATION FUNCTION
# ---------------------------

def evaluate_gd(topic: str, transcript: str, audio_path: str) -> dict:
    """
    Central GD evaluation logic using Ollama.
    ALL strictness and penalties handled here.
    
    Args:
        topic: The GD topic
        transcript: Transcribed text from audio
        audio_path: Path to audio file
        
    Returns:
        dict with transcript, content_score, communication_score, feedback, ideal_answer
    """

    # ---------------------------
    # HARD FAIL: SILENCE
    # ---------------------------
    if is_silent_audio(audio_path) or is_silent_transcript(transcript):
        return {
            "transcript": transcript or "",
            "content_score": 0,
            "communication_score": 0,
            "feedback": "No meaningful speech detected. Please speak clearly and stay on topic.",
            "ideal_answer": ""
        }

    # ---------------------------
    # OLLAMA PROMPT
    # ---------------------------
    prompt = f"""
You are a strict Group Discussion evaluator.

Topic:
"{topic}"

User response:
"{transcript}"

Rules:
- Return ONLY valid JSON
- NO markdown formatting
- NO explanations outside the JSON
- NO extra text before or after the JSON

Scoring rules:
- Content score (0-10): relevance to topic, depth of analysis, logical arguments
- Communication score (0-10): fluency, clarity, confidence, articulation
- Penalize heavily for off-topic answers
- Penalize very short answers (<10 words)
- Be STRICT - average score should be 5-6/10
- Only exceptional answers deserve 9-10

Return format:
{{
  "content_score": <integer 0-10>,
  "communication_score": <integer 0-10>,
  "feedback": "<string with specific, actionable criticism>",
  "ideal_answer": "<string with a model answer for this topic>"
}}
"""

    try:
        raw_output = run_ollama(prompt)
    except Exception as e:
        return {
            "transcript": transcript,
            "content_score": 0,
            "communication_score": 0,
            "feedback": f"Evaluation failed: {str(e)}",
            "ideal_answer": ""
        }

    # ---------------------------
    # PARSE JSON
    # ---------------------------
    try:
        result = extract_json(raw_output)
    except Exception as e:
        print(f"Failed to parse Ollama response: {e}")
        print(f"Raw output: {raw_output}")
        return {
            "transcript": transcript,
            "content_score": 0,
            "communication_score": 0,
            "feedback": "Error: Could not parse evaluation results. Please try again.",
            "ideal_answer": ""
        }

    # ---------------------------
    # NORMALIZE SCORES
    # ---------------------------
    result["content_score"] = int(max(0, min(10, result.get("content_score", 0))))
    result["communication_score"] = int(max(0, min(10, result.get("communication_score", 0))))

    # ---------------------------
    # STRICT PENALTIES
    # ---------------------------

    word_count = len(transcript.split())

    # Very short answer → heavy penalty
    if word_count < 10:
        result["content_score"] = min(result["content_score"], 3)
        result["communication_score"] = min(result["communication_score"], 3)
        result["feedback"] = "Response too brief. " + result.get("feedback", "")

    # Weak communication → cap content score
    if result["communication_score"] <= 2:
        result["content_score"] = min(result["content_score"], 4)

    # ---------------------------
    # FINAL RESPONSE
    # ---------------------------
    return {
        "transcript": transcript,
        "content_score": result["content_score"],
        "communication_score": result["communication_score"],
        "feedback": result.get("feedback", "No feedback provided"),
        "ideal_answer": result.get("ideal_answer", "")
    }


# ---------------------------
# TEST FUNCTION
# ---------------------------

if __name__ == "__main__":
    # Test the evaluator
    test_topic = "Should artificial intelligence replace human decision-making?"
    test_transcript = "AI can process data faster than humans, but it lacks empathy and moral judgment. We need a balanced approach."
    test_audio = "test.wav"  # Dummy path
    
    print("Testing GD Evaluator with Ollama...")
    result = evaluate_gd(test_topic, test_transcript, test_audio)
    print(json.dumps(result, indent=2))