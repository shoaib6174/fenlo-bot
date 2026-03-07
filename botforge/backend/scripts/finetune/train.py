"""QLoRA Fine-tuning Script for Llama 3.1 8B Instruct.

Fine-tunes a domain-specific RAG assistant using QLoRA (4-bit quantization + LoRA).
Tracks experiments with Weights & Biases.

Usage:
    python train.py [--epochs 3] [--lr 2e-4] [--wandb-project fenlo-ai-finetune]
"""

import argparse
from datetime import datetime

import torch
import wandb
from config import LoRAConfig, ModelConfig, TrainingConfig
from datasets import load_dataset
from peft import LoraConfig, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer


def main(args):
    """Run QLoRA fine-tuning."""
    model_cfg = ModelConfig()
    lora_cfg = LoRAConfig()
    train_cfg = TrainingConfig()

    # Override from CLI args
    if args.epochs:
        train_cfg.num_train_epochs = args.epochs
    if args.lr:
        train_cfg.learning_rate = args.lr
    if args.batch_size:
        train_cfg.per_device_train_batch_size = args.batch_size

    run_name = args.run_name or f"fenlo-qlora-{datetime.now():%Y%m%d-%H%M}"
    train_cfg.output_dir = f"./outputs/{run_name}"

    print(f"{'='*60}")
    print(f"  QLoRA Fine-tuning: {model_cfg.model_name}")
    print(f"  LoRA: r={lora_cfg.r}, alpha={lora_cfg.lora_alpha}")
    print(f"  Training: {train_cfg.num_train_epochs} epochs, lr={train_cfg.learning_rate}")
    print(
        f"  Batch: {train_cfg.per_device_train_batch_size} x {train_cfg.gradient_accumulation_steps} = {train_cfg.per_device_train_batch_size * train_cfg.gradient_accumulation_steps}"
    )
    print(f"  Output: {train_cfg.output_dir}")
    print(f"{'='*60}")

    # --- W&B Init ---
    wandb.init(
        project=args.wandb_project or "fenlo-ai-finetune",
        name=run_name,
        config={
            "model": model_cfg.model_name,
            "lora_r": lora_cfg.r,
            "lora_alpha": lora_cfg.lora_alpha,
            "epochs": train_cfg.num_train_epochs,
            "learning_rate": train_cfg.learning_rate,
            "batch_size": train_cfg.per_device_train_batch_size,
            "gradient_accumulation": train_cfg.gradient_accumulation_steps,
            "max_seq_length": model_cfg.max_seq_length,
        },
    )

    # --- Load Dataset ---
    print("\nLoading dataset...")
    dataset = load_dataset(
        "json",
        data_files={
            "train": "data/train.jsonl",
            "eval": "data/eval.jsonl",
        },
    )
    print(f"  Train: {len(dataset['train'])} samples")
    print(f"  Eval:  {len(dataset['eval'])} samples")

    # --- Quantization Config ---
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=model_cfg.load_in_4bit,
        bnb_4bit_compute_dtype=getattr(torch, model_cfg.bnb_4bit_compute_dtype),
        bnb_4bit_quant_type=model_cfg.bnb_4bit_quant_type,
        bnb_4bit_use_double_quant=model_cfg.use_double_quant,
    )

    # --- Load Model ---
    print(f"\nLoading {model_cfg.model_name} with 4-bit quantization...")
    model = AutoModelForCausalLM.from_pretrained(
        model_cfg.model_name,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",  # Scaled dot-product attention (PyTorch native)
    )
    model = prepare_model_for_kbit_training(model)

    # --- Load Tokenizer ---
    tokenizer = AutoTokenizer.from_pretrained(model_cfg.model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # --- LoRA Config ---
    peft_config = LoraConfig(
        r=lora_cfg.r,
        lora_alpha=lora_cfg.lora_alpha,
        lora_dropout=lora_cfg.lora_dropout,
        target_modules=lora_cfg.target_modules,
        bias=lora_cfg.bias,
        task_type=lora_cfg.task_type,
    )

    # --- Training Arguments ---
    training_args = TrainingArguments(
        output_dir=train_cfg.output_dir,
        num_train_epochs=train_cfg.num_train_epochs,
        per_device_train_batch_size=train_cfg.per_device_train_batch_size,
        per_device_eval_batch_size=train_cfg.per_device_train_batch_size,
        gradient_accumulation_steps=train_cfg.gradient_accumulation_steps,
        learning_rate=train_cfg.learning_rate,
        lr_scheduler_type=train_cfg.lr_scheduler_type,
        warmup_ratio=train_cfg.warmup_ratio,
        weight_decay=train_cfg.weight_decay,
        max_grad_norm=train_cfg.max_grad_norm,
        logging_steps=train_cfg.logging_steps,
        save_strategy=train_cfg.save_strategy,
        eval_strategy=train_cfg.eval_strategy,
        bf16=train_cfg.bf16,
        optim=train_cfg.optim,
        seed=train_cfg.seed,
        report_to=train_cfg.report_to,
        run_name=run_name,
        remove_unused_columns=False,
    )

    # --- Trainer ---
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["eval"],
        processing_class=tokenizer,
        peft_config=peft_config,
    )

    # --- Train ---
    print("\nStarting training...")
    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"  GPU: {torch.cuda.get_device_name(0)} ({gpu_mem:.0f}GB)")
    print(f"  GPU memory allocated: {torch.cuda.memory_allocated(0) / 1e9:.1f}GB")

    trainer.train()

    # --- Save ---
    print(f"\nSaving adapter to {train_cfg.output_dir}/final_adapter...")
    trainer.save_model(f"{train_cfg.output_dir}/final_adapter")
    tokenizer.save_pretrained(f"{train_cfg.output_dir}/final_adapter")

    # --- Log Final Metrics ---
    eval_results = trainer.evaluate()
    wandb.log({"final_eval_loss": eval_results["eval_loss"]})
    print(f"\nFinal eval loss: {eval_results['eval_loss']:.4f}")

    wandb.finish()
    print(f"\nDone! Adapter saved to: {train_cfg.output_dir}/final_adapter")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QLoRA fine-tuning")
    parser.add_argument("--epochs", type=int, help="Number of training epochs")
    parser.add_argument("--lr", type=float, help="Learning rate")
    parser.add_argument("--batch-size", type=int, help="Per-device batch size")
    parser.add_argument("--run-name", type=str, help="W&B run name")
    parser.add_argument("--wandb-project", type=str, help="W&B project name")
    args = parser.parse_args()
    main(args)
