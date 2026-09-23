import json
import os

from openai import OpenAI

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
TEXT_MODEL = os.getenv("TEXT_MODEL", "qwen2.5:0.5b")

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

SYSTEM_PROMPT = (
    "You are a strict text analyzer. Extract data from the user's text and return ONLY a JSON "
    "object, with no extra text and no markdown fences. Do not invent facts that are not implied "
    "by the text.\n"
    "Schema:\n"
    "{\n"
    '  "intent": "task" | "content_creation" | "summary",\n'
    '  "title": "short summary of the request, in the same language as the input",\n'
    '  "priority": "high" | "medium" | "low",\n'
    '  "action_platform": "notion" | "instagram" | "trello",\n'
    '  "summary_or_caption": "a detailed, helpful text related to the input, same language as input"\n'
    "}"
)


def analyze_text(user_speech_text: str) -> dict:
    """Calls the local Ollama/Qwen model and returns a validated dict.
    Never raises: on any failure it returns {"error": ...}.
    """
    try:
        response = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"User input to analyze: {user_speech_text}"},
            ],
            response_format={"type": "json_object"},
        )
        # NOTE: the original code indexed .choices.message.content directly,
        # which is a bug — .choices is a list, so it needs [0].
        content = response.choices[0].message.content
        data = json.loads(content)

        # Normalize/validate so a malformed LLM response can never crash the UI.
        if data.get("intent") not in {"task", "content_creation", "summary"}:
            data["intent"] = "summary"
        if data.get("priority") not in {"high", "medium", "low"}:
            data["priority"] = "medium"
        data.setdefault("title", user_speech_text[:60] or "بدون عنوان")
        data.setdefault("action_platform", "notion")
        data.setdefault("summary_or_caption", user_speech_text)
        return data
    except Exception as e:
        return {"error": f"حدث خطأ أثناء معالجة البيانات: {e}"}
