"""
Manual integration test for LLM Router

Run with: uv run python tests/manual/test_llm_router_integration.py

This demonstrates:
1. Primary provider (Groq) is called first
2. Circuit breaker opens after 5 failures
3. Fallback to OpenAI when Groq circuit is open
4. Graceful degradation when all providers are down
5. State transitions are logged
"""

import asyncio
import os

from app.core.llm_router import LLMRouter

# Set test API keys (invalid keys to trigger failures)
os.environ["GROQ_API_KEY"] = "invalid-groq-key"
os.environ["OPENAI_API_KEY"] = "invalid-openai-key"


async def test_circuit_breaker():
    """Test circuit breaker behavior"""
    print("\n=== Testing Circuit Breaker ===\n")

    router = LLMRouter()

    messages = [{"role": "user", "content": "Hello, how are you?"}]

    # Test 1: Initial state - both circuits CLOSED
    print("1. Initial state:")
    print(f"   Groq circuit: {router.groq_circuit.state}")
    print(f"   OpenAI circuit: {router.openai_circuit.state}")

    # Test 2: Trigger 5 failures to open Groq circuit
    print("\n2. Triggering Groq failures (5x) to open circuit...")
    for i in range(5):
        try:
            result = await router.complete(messages, stream=False)
        except Exception as e:
            print(f"   Attempt {i + 1}: {type(e).__name__}")

    print(f"   Groq circuit state: {router.groq_circuit.state}")
    print(f"   Groq failures: {len(router.groq_circuit.failures)}")

    # Test 3: Next request should skip Groq (circuit OPEN), try OpenAI
    print("\n3. Next request should skip Groq, try OpenAI...")
    try:
        result = await router.complete(messages, stream=False)
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Error: {type(e).__name__}: {e}")

    # Test 4: Trigger OpenAI failures to open that circuit too
    print("\n4. Triggering OpenAI failures (5x) to open circuit...")
    for i in range(5):
        try:
            result = await router.complete(messages, stream=False)
        except Exception as e:
            print(f"   Attempt {i + 1}: {type(e).__name__}")

    print(f"   OpenAI circuit state: {router.openai_circuit.state}")

    # Test 5: All providers down - should get graceful fallback
    print("\n5. All providers down - graceful degradation:")
    result = await router.complete(messages, stream=False)
    print(f"   Provider: {result['provider']}")
    print(f"   Message: {result['content'][:100]}...")

    print("\n=== Test Complete ===\n")
    print("Expected behavior:")
    print("✓ Groq circuit opens after 5 failures")
    print("✓ OpenAI circuit opens after 5 failures")
    print("✓ Graceful fallback message when all providers down")
    print("✓ State transitions logged to console")

    await router.close()


if __name__ == "__main__":
    asyncio.run(test_circuit_breaker())
