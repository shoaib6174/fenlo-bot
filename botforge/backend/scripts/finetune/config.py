"""Fine-tuning configuration for Llama 3.1 8B with QLoRA."""

from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """Base model configuration."""

    model_name: str = "NousResearch/Meta-Llama-3.1-8B-Instruct"  # No gating, same weights
    max_seq_length: int = 2048
    load_in_4bit: bool = True  # QLoRA 4-bit quantization
    bnb_4bit_compute_dtype: str = "bfloat16"
    bnb_4bit_quant_type: str = "nf4"  # NormalFloat4
    use_double_quant: bool = True  # Nested quantization


@dataclass
class LoRAConfig:
    """LoRA adapter configuration."""

    r: int = 16  # LoRA rank
    lora_alpha: int = 32  # Scaling factor
    lora_dropout: float = 0.05
    target_modules: list[str] = field(
        default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj"]
    )
    bias: str = "none"
    task_type: str = "CAUSAL_LM"


@dataclass
class TrainingConfig:
    """Training hyperparameters."""

    output_dir: str = "./outputs/fenlo-ai-llama3"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    gradient_accumulation_steps: int = 4  # Effective batch size = 16
    learning_rate: float = 2e-4
    lr_scheduler_type: str = "cosine"
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0
    logging_steps: int = 10
    save_strategy: str = "epoch"
    eval_strategy: str = "epoch"
    bf16: bool = True
    optim: str = "paged_adamw_8bit"
    seed: int = 42
    report_to: str = "wandb"


@dataclass
class DataConfig:
    """Dataset configuration."""

    train_file: str = "data/train.jsonl"
    eval_file: str = "data/eval.jsonl"
    max_samples: int | None = None  # None = use all


@dataclass
class WandbConfig:
    """Weights & Biases configuration."""

    project: str = "fenlo-ai-finetune"
    run_name: str | None = None  # Auto-generated if None
