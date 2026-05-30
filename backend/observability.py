from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_client = None
_callback = None


def get_langfuse():
    """
    Lazy singleton for Langfuse client.
    Only initializes if API keys are configured.
    """
    global _client
    if _client is None:
        from backend.config import get_settings
        s = get_settings()
        if s.langfuse_public_key:
            try:
                from langfuse import Langfuse
                _client = Langfuse(
                    public_key=s.langfuse_public_key,
                    secret_key=s.langfuse_secret_key,
                    host=s.langfuse_host,
                )
                logger.info("[obs] Langfuse initialized: %s", s.langfuse_host)
            except ImportError:
                logger.warning("[obs] langfuse not installed, observability disabled")
                _client = False  # Mark as attempted but failed
            except Exception as exc:
                logger.warning("[obs] Langfuse init failed: %s", exc)
                _client = False
    return _client if _client is not False else None


def get_callback():
    """
    Lazy singleton for LangChain CallbackHandler.
    Returns None if Langfuse is not configured.
    """
    global _callback
    if _callback is None and get_langfuse():
        try:
            from langfuse.langchain import CallbackHandler
            _callback = CallbackHandler()
        except Exception as exc:
            logger.warning("[obs] CallbackHandler creation failed: %s", exc)
            _callback = False
    return _callback if _callback is not False else None
