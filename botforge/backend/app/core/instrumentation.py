"""
Arize AX Tracing — centralized instrumentation.

Auto-instruments Groq, OpenAI, and LangChain calls.
Must be initialized BEFORE any LLM client is created.
"""

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


def init_tracing():
    """Initialize Arize AX tracing with auto-instrumentation.

    No-op if ARIZE_SPACE_ID or ARIZE_API_KEY are not set.
    """
    if not settings.arize_space_id or not settings.arize_api_key:
        logger.info("arize.disabled", reason="missing credentials")
        return

    try:
        from arize.otel import register
        from openinference.instrumentation.groq import GroqInstrumentor
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from openinference.instrumentation.openai import OpenAIInstrumentor

        tracer_provider = register(
            space_id=settings.arize_space_id,
            api_key=settings.arize_api_key,
            project_name=settings.arize_project_name,
        )

        GroqInstrumentor().instrument(tracer_provider=tracer_provider)
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

        logger.info(
            "arize.initialized",
            project=settings.arize_project_name,
            instrumentors=["groq", "openai", "langchain"],
        )
    except ImportError as e:
        logger.warning("arize.import_failed", error=str(e))
    except Exception as e:
        logger.warning("arize.init_failed", error=str(e))
