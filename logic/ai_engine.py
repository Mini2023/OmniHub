"""
Omni-Hub – AI Engine v4.1.1 (Hybrid: Gemini API + Ollama Local)
=================================================================
Changes in 4.1.1:
  - Switched from deprecated google.generativeai → google.genai (new SDK)
  - Backend now supports 3 modes: "ollama" | "gemini_pro" | "gemini_flash"
  - Automatic 429 (Quota Exceeded) fallback: Pro → Flash, silently
  - All network I/O is sync; UI calls these via QThreads
"""

from __future__ import annotations
import builtins
import os
import time
from typing import Literal

# ── Load configuration ────────────────────────────────────────────────────────
try:
    from config import (
        GEMINI_API_KEY, GEMINI_PRO_MODEL, GEMINI_FLASH_MODEL,
        OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_FALLBACK_MODEL,
        CONTEXT_MAX_TOKENS,
    )
except ImportError:
    GEMINI_API_KEY        = "YOUR_GEMINI_API_KEY_HERE"
    GEMINI_PRO_MODEL      = "gemini-3-pro-preview"
    GEMINI_FLASH_MODEL    = "gemini-3-flash-preview"
    OLLAMA_BASE_URL       = "http://localhost:11434"
    OLLAMA_MODEL          = "dolphin3:8b"
    OLLAMA_FALLBACK_MODEL = "dolphin3:1b"
    CONTEXT_MAX_TOKENS    = 8000

# ── Backend type ──────────────────────────────────────────────────────────────
Backend = Literal["ollama", "gemini_pro", "gemini_flash"]

SYSTEM_PROMPT = (
    "Du bist ein hilfreicher All-in-One-Assistent. "
    "Beantworte allgemeine Fragen direkt und führe Dateianalysen nur durch, "
    "wenn eine Datei bereitgestellt wurde. Verweigere niemals eine Antwort."
)

# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_file_text(filepath: str, max_chars: int = 6000) -> str:
    """Extract text from a file for AI context.

    Priority order:
      1. PyMuPDF (fitz) – for PDF: extracts real page text, not metadata
      2. MarkItDown      – for DOCX, HTML, etc.
      3. Plain-text read – final fallback
    """
    ext = os.path.splitext(filepath)[1].lower()

    # ── 1. PyMuPDF for PDFs ─────────────────────────────────────────────
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(filepath)
            pages_text: list[str] = []
            for page in doc:
                pages_text.append(page.get_text("text"))
            doc.close()
            full_text = "\n\n".join(pages_text)
            if full_text.strip():
                return full_text[:max_chars]
        except Exception:
            pass  # fall through to MarkItDown

    # ── 2. MarkItDown (DOCX, HTML, PPTX, …) ────────────────────────────
    try:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(filepath)
        if result.text_content and result.text_content.strip():
            return result.text_content[:max_chars]
    except Exception:
        pass

    # ── 3. Plain-text fallback ───────────────────────────────────────────
    try:
        with builtins.open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_chars)
    except Exception as e:
        return f"[Could not read file: {e}]"


def _count_tokens_approx(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


def _is_quota_error(exc: Exception) -> bool:
    """Detect HTTP 429 / ResourceExhausted errors from Gemini."""
    msg = str(exc).lower()
    return "429" in msg or "quota" in msg or "resource_exhausted" in msg or "rate_limit" in msg


# ─────────────────────────────────────────────────────────────────────────────
# Ollama backend
# ─────────────────────────────────────────────────────────────────────────────

def _ollama_chat(messages: list[dict], model: str | None = None) -> str:
    try:
        import ollama
        chosen_model = model or OLLAMA_MODEL
        response = ollama.chat(model=chosen_model, messages=messages)
        return response["message"]["content"]
    except Exception as e:
        return f"[Ollama Error] {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Gemini backend  (google.genai – new SDK)
# ─────────────────────────────────────────────────────────────────────────────

def _gemini_chat(
    prompt: str,
    model_id: str,
    system_instruction: str = SYSTEM_PROMPT,
) -> str:
    """Call Gemini with a given model_id. Returns the response text."""
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        return (
            "[Gemini Error] Kein API-Key konfiguriert. "
            "Bitte config.py bearbeiten und GEMINI_API_KEY eintragen."
        )
    try:
        from google import genai                  # type: ignore
        from google.genai import types            # type: ignore

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
            ),
        )
        return response.text or "(Keine Antwort erhalten)"
    except Exception as e:
        raise   # let caller handle / fallback


def _gemini_with_fallback(
    prompt: str,
    preferred_model: str,
    fallback_model: str,
    system_instruction: str = SYSTEM_PROMPT,
) -> str:
    """Try *preferred_model*; on 429 silently retry with *fallback_model*."""
    try:
        return _gemini_chat(prompt, preferred_model, system_instruction)
    except Exception as e:
        if _is_quota_error(e):
            # ── Silent Pro → Flash fallback ───────────────────────────────
            try:
                result = _gemini_chat(prompt, fallback_model, system_instruction)
                return f"[Auto-Fallback: Flash]\n{result}"
            except Exception as e2:
                return f"[Gemini Flash Error] {e2}"
        return f"[Gemini Error] {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Routing helper
# ─────────────────────────────────────────────────────────────────────────────

def _dispatch(prompt: str, backend: Backend, system: str = SYSTEM_PROMPT) -> str:
    """Route a prompt to the correct backend with automatic fallback."""
    if backend == "gemini_pro":
        return _gemini_with_fallback(prompt, GEMINI_PRO_MODEL, GEMINI_FLASH_MODEL, system)
    elif backend == "gemini_flash":
        try:
            return _gemini_chat(prompt, GEMINI_FLASH_MODEL, system)
        except Exception as e:
            return f"[Gemini Flash Error] {e}"
    else:  # ollama
        return _ollama_chat([
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ])


# ─────────────────────────────────────────────────────────────────────────────
# Public API – called by QThread workers
# ─────────────────────────────────────────────────────────────────────────────

def chat_ai(
    prompt: str,
    backend: Backend = "ollama",
    conversation_history: list[dict] | None = None,
) -> str:
    """General-purpose chat with optional conversation history."""
    if backend == "ollama":
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": prompt})
        return _ollama_chat(messages)
    else:
        # Flatten history into prompt for Gemini
        history_text = ""
        if conversation_history:
            for m in conversation_history:
                role = "User" if m["role"] == "user" else "Assistant"
                history_text += f"{role}: {m['content']}\n"
        full_prompt = history_text + f"User: {prompt}"
        return _dispatch(full_prompt, backend)


def summarize_file(filepath: str, backend: Backend = "ollama") -> str:
    """Summarize a document."""
    content = _read_file_text(filepath)
    prompt = f"Bitte fasse den folgenden Inhalt prägnant zusammen:\n\n{content}"
    return _dispatch(prompt, backend)


def explain_file(filepath: str, backend: Backend = "ollama") -> str:
    """Explain the document content in simple terms."""
    content = _read_file_text(filepath)
    prompt = (
        "Erkläre den folgenden Inhalt so einfach wie möglich, "
        "als würdest du es einem Teenager erklären:\n\n" + content
    )
    return _dispatch(prompt, backend)


def rewrite_file(filepath: str, backend: Backend = "ollama") -> str:
    """Rewrite a document for clarity and professional tone."""
    content = _read_file_text(filepath)
    prompt = (
        "Schreibe den folgenden Text professionell und klar um. "
        "Behalte alle wichtigen Informationen bei:\n\n" + content
    )
    return _dispatch(prompt, backend)


def compare_files(filepaths: list[str], backend: Backend = "ollama") -> str:
    """Compare two or more files and return structured analysis."""
    if len(filepaths) < 2:
        return "[Error] Mindestens 2 Dateien für den Vergleich erforderlich."

    sections: list[str] = []
    for i, fp in enumerate(filepaths, 1):
        text = _read_file_text(fp, max_chars=3000)
        sections.append(f"=== Datei {i}: {fp} ===\n{text}")

    combined = "\n\n".join(sections)
    prompt = (
        "Analysiere die folgenden Dokumente und erstelle einen strukturierten Bericht:\n"
        "1. Gemeinsamkeiten\n"
        "2. Unterschiede\n"
        "3. Empfehlung / Fazit\n\n"
        + combined
    )
    return _dispatch(prompt, backend)


def test_ai_connection(backend: Backend = "ollama") -> str:
    """Quick connectivity ping."""
    if backend == "ollama":
        return _ollama_chat([
            {"role": "user", "content": 'Reply only with: "Ollama verbunden ✓"'},
        ])
    elif backend == "gemini_flash":
        return _dispatch('Reply only with: "Gemini Flash verbunden ✓"', "gemini_flash")
    else:
        return _dispatch('Reply only with: "Gemini Pro verbunden ✓"', "gemini_pro")


def analyze_image(filepath: str, prompt: str, backend: Backend = "gemini_flash") -> str:
    """Analyze an image using multimodal AI (Gemini)."""
    if backend == "ollama":
        return "[Error] Ollama-Bildanalyse noch nicht integriert (erfordert Llava/InternVL)."
    
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        return "[Error] Kein Gemini API-Key vorhanden."

    try:
        from google import genai
        from google.genai import types
        import PIL.Image

        client = genai.Client(api_key=GEMINI_API_KEY)
        img = PIL.Image.open(filepath)
        
        response = client.models.generate_content(
            model=GEMINI_PRO_MODEL if backend == "gemini_pro" else GEMINI_FLASH_MODEL,
            contents=[prompt, img],
            config=types.GenerateContentConfig(
                system_instruction="Du bist ein Bild-Experte. Antworte präzise auf die Analyse-Anfrage."
            )
        )
        return response.text or "(Keine Analyse möglich)"
    except Exception as e:
        if _is_quota_error(e) and backend == "gemini_pro":
            return analyze_image(filepath, prompt, "gemini_flash")
        return f"[AI Image Error] {e}"

def get_context_fill_ratio(conversation_history: list[dict]) -> float:

    """Return 0.0–1.0 representing how full the context window is."""
    total_text = " ".join(m.get("content", "") for m in conversation_history)
    used_tokens = _count_tokens_approx(total_text)
    return min(1.0, used_tokens / CONTEXT_MAX_TOKENS)
