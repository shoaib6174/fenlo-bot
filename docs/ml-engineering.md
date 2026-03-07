# ML Engineering — Observability, Evaluation & Fine-Tuning

## Overview

BotForge's ML engineering layer adds production-grade observability, quantitative RAG evaluation, and domain-specific fine-tuning to the conversation engine.

```
User Message
  --> Arize AX (auto-tracing)
  --> RAG Pipeline (retrieve + generate)
  --> RAGAS Evaluation (faithfulness, relevancy, precision)
  --> Response

Training Loop:
  Production Data --> Export --> QLoRA Fine-tune --> Evaluate --> Deploy
```

---

## 1. LLM Observability (Arize AX)

**Problem**: No visibility into LLM call latency, token usage, or failure patterns across providers.

**Solution**: OpenTelemetry-based auto-instrumentation via Arize AX. Zero manual decorators — every Groq, OpenAI, and LangChain call is automatically traced.

### Architecture

```
app/core/instrumentation.py          # Centralized setup (single file)
  |
  |-- GroqInstrumentor               # Auto-traces all Groq API calls
  |-- OpenAIInstrumentor             # Auto-traces all OpenAI API calls
  |-- LangChainInstrumentor          # Auto-traces RAG pipeline calls
  |
  --> OTLP export --> Arize Cloud    # Dashboard, alerts, analytics
```

### Key Design Decisions

- **Auto-instrumentation over manual**: Arize's OpenInference instrumentors patch SDK clients at import time. No `@traceable` decorators needed — every LLM call is captured automatically.
- **Graceful degradation**: If `ARIZE_SPACE_ID` is not set, tracing is a complete no-op. No imports, no overhead, no errors.
- **Init before clients**: `init_tracing()` runs in the FastAPI lifespan before `LLMRouter()` is created. This ensures the instrumentors patch the SDK classes before any client instances exist.
- **OpenTelemetry standard**: Not locked into Arize — can add Datadog, Honeycomb, or any OTLP-compatible backend as an additional exporter with zero code changes.

### What Gets Traced

| Signal | Data Captured |
|--------|---------------|
| LLM calls | Model, messages, response, tokens_in/out, latency, provider |
| RAG retrieval | Query, chunks returned, relevance scores |
| Circuit breaker | Fallback events (Groq → OpenAI), circuit state transitions |
| Pipeline steps | Per-step latency through the message pipeline |

### Files

- `app/core/instrumentation.py` — Centralized tracing setup (~50 lines)
- `app/config.py` — `ARIZE_SPACE_ID`, `ARIZE_API_KEY`, `ARIZE_PROJECT_NAME`
- `app/main.py` — Init in lifespan, before LLM router

---

## 2. RAG Evaluation (RAGAS)

**Problem**: No quantitative measure of RAG response quality. Can't tell if retrieval is returning relevant chunks or if the LLM is hallucinating beyond the context.

**Solution**: RAGAS framework computing three key metrics per response, using Groq (free) as the evaluator LLM.

### Metrics

| Metric | What It Measures | Score Range |
|--------|-----------------|-------------|
| **Faithfulness** | Is the answer grounded in the retrieved context? (no hallucination) | 0.0 – 1.0 |
| **Answer Relevancy** | Does the answer actually address the user's question? | 0.0 – 1.0 |
| **Context Precision** | Are the most relevant chunks ranked highest in retrieval? | 0.0 – 1.0 |

### Baseline Results

| Metric | Score |
|--------|-------|
| Faithfulness | **1.00** |
| Answer Relevancy | **0.93** |
| Context Precision | **1.00** |

### Architecture

```
app/core/evaluation.py               # RAGAS evaluation engine
  |
  |-- _get_evaluator_llm()           # Groq via OpenAI-compatible API (free)
  |-- _get_evaluator_embeddings()    # sentence-transformers (local, no API cost)
  |-- evaluate_dataset()             # Run metrics on sample set
  |
app/api/eval.py                      # REST API endpoints
  |
  |-- POST /eval/run                 # Evaluate from DB (admin-only)
  |-- POST /eval/run-inline          # Evaluate provided samples
  |-- GET  /eval/results             # Get all results
  |-- GET  /eval/results/latest      # Get most recent
  |
scripts/export_eval_dataset.py       # Export production data for evaluation
```

### Key Design Decisions

- **Groq as evaluator**: RAGAS needs an LLM judge. Instead of paying for OpenAI evaluations, we use Groq's free Llama 3.3 70B through the OpenAI-compatible API. Same quality, zero cost.
- **Local embeddings**: ResponseRelevancy metric needs embeddings. We reuse the project's existing `sentence-transformers/all-MiniLM-L6-v2` model — no additional API calls.
- **Async-safe**: RAGAS evaluation runs in the FastAPI event loop without blocking. Results are returned via REST API.
- **Admin-gated**: All eval endpoints require admin role — prevents abuse of the LLM-powered evaluation.

---

## 3. Fine-Tuning (QLoRA)

**Problem**: The base Llama 3.1 8B model gives generic responses. Want domain-specific behavior: always cite sources, match the RAG assistant persona, handle knowledge gaps gracefully.

**Solution**: QLoRA (4-bit quantized LoRA) fine-tuning on domain-specific instruction-response pairs. Produces a 27MB adapter that can be hot-loaded onto the base model.

### Training Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Base model | Llama 3.1 8B Instruct | Best quality-to-size ratio for fine-tuning |
| Quantization | NF4 (4-bit) | Fits 8B model in ~5GB VRAM |
| LoRA rank (r) | 16 | Good quality/efficiency balance |
| LoRA alpha | 32 | 2x rank scaling |
| Target modules | q_proj, k_proj, v_proj, o_proj | Attention layers only |
| Learning rate | 2e-4 | Standard for QLoRA |
| Scheduler | Cosine with warmup | Smooth convergence |
| Batch size | 4 x 4 (effective 16) | Gradient accumulation for stability |
| Optimizer | Paged AdamW 8-bit | Memory-efficient |
| Precision | BF16 | Native on modern GPUs |

### Training Results

| Metric | Value |
|--------|-------|
| GPU | NVIDIA RTX 5090 (32GB VRAM) |
| Training time | ~2 minutes (10 synthetic samples) |
| Final eval loss | **1.86** |
| Mean token accuracy | **66.5%** |
| Trainable parameters | 13.6M / 8.04B (**0.17%**) |
| Adapter size | **27MB** (vs 16GB full model) |

### Data Pipeline

```
Production DB
  --> scripts/export_eval_dataset.py    # Extract Q&A pairs with citations
  --> scripts/finetune/prepare_data.py  # Format as Llama 3.1 instruction tuning
  --> data/train.jsonl                  # 90% train
  --> data/eval.jsonl                   # 10% eval

Training:
  scripts/finetune/train.py             # QLoRA training with W&B tracking
  --> outputs/final_adapter/            # 27MB LoRA adapter

Deployment:
  scripts/finetune/merge_adapter.py     # Merge adapter into base model
  --> huggingface-cli upload            # Push to HuggingFace Hub
```

### Instruction Format

Each training sample follows the Llama 3.1 Instruct chat template:

```json
{
  "messages": [
    {"role": "system", "content": "You are a helpful AI assistant. Answer based on the provided context. Always cite sources."},
    {"role": "user", "content": "Context:\n[Source 1]: ...\n\nQuestion: What are your business hours?"},
    {"role": "assistant", "content": "Our business hours are Monday to Friday, 9 AM to 5 PM EST. [Source 1]"}
  ]
}
```

### Key Design Decisions

- **QLoRA over full fine-tuning**: 0.17% trainable parameters, 27MB adapter vs 16GB full model. Same quality improvement at a fraction of the compute.
- **W&B experiment tracking**: Every training run logs loss curves, learning rate schedule, GPU utilization. Enables hyperparameter comparison across runs.
- **Synthetic data fallback**: When production data isn't available, the pipeline generates domain-specific synthetic examples to validate the training pipeline end-to-end.
- **Separate from serving**: The adapter is trained offline and merged for deployment. No training code in the production backend.

### Files

```
scripts/finetune/
  config.py          # Model, LoRA, training, and W&B configuration
  prepare_data.py    # Convert conversations to instruction format
  train.py           # QLoRA training with BitsAndBytes + PEFT + TRL
  merge_adapter.py   # Merge LoRA weights into base model
  requirements.txt   # GPU server dependencies (torch, transformers, peft, etc.)
```

---

## Dependency Summary

### Backend (pyproject.toml)

```
arize-otel                              # OpenTelemetry export to Arize
openinference-instrumentation-groq      # Auto-trace Groq calls
openinference-instrumentation-openai    # Auto-trace OpenAI calls
openinference-instrumentation-langchain # Auto-trace LangChain calls
ragas                                   # RAG evaluation framework
datasets                                # HuggingFace datasets (for RAGAS)
```

### GPU Server (scripts/finetune/requirements.txt)

```
torch, transformers, peft, bitsandbytes, trl, accelerate, wandb, datasets
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ARIZE_SPACE_ID` | For tracing | Arize Space ID |
| `ARIZE_API_KEY` | For tracing | Arize API Key |
| `ARIZE_PROJECT_NAME` | No | Project name (default: `fenlo-ai`) |
| `WANDB_API_KEY` | For training | Weights & Biases API key |
