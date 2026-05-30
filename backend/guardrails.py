import logging
import re

logger = logging.getLogger(__name__)

BLOCKED_PATTERNS = [
    r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",  # UUIDs
    r"(?i)(ignore|disregard).*(previous|prior|above).*(instruction|prompt|rule)",
    r"(?i)system.?prompt",
    r"(?i)you.?are.?an?.?(assistant|ai|model|language.?model)",  # Model self-reference
]


def validate_llm_output(text: str) -> bool:
    """
    Check LLM output for leaked secrets, jailbreak attempts, or unsafe content.
    Returns False if output should be blocked.
    """
    if not text:
        return True

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text):
            logger.warning("[guardrail] BLOCKED output matching pattern %r", pattern)
            return False

    return True


def wrap_data(content: str, tag: str) -> str:
    """
    Wrap untrusted content in <data type="..."> XML tags.
    This creates a clear boundary between instructions and data for the LLM.
    """
    # Escape any existing </data> tags to prevent tag injection
    escaped = content.replace("</data>", "&lt;/data&gt;")
    return f'<data type="{tag}">{escaped}</data>'
