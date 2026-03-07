"""Merge LoRA adapter weights into base model for deployment.

Takes the QLoRA adapter and merges it with the base model to produce
a standalone model that can be uploaded to HuggingFace or served directly.

Usage:
    python merge_adapter.py --adapter ./outputs/fenlo-qlora-*/final_adapter --output ./merged_model
"""

import argparse

import torch
from config import ModelConfig
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def merge(adapter_path: str, output_path: str):
    """Merge LoRA adapter into base model."""
    model_cfg = ModelConfig()

    print(f"Loading base model: {model_cfg.model_name}")
    base_model = AutoModelForCausalLM.from_pretrained(
        model_cfg.model_name,
        torch_dtype=torch.bfloat16,
        device_map="cpu",  # Merge on CPU to avoid OOM
    )

    print(f"Loading adapter: {adapter_path}")
    model = PeftModel.from_pretrained(base_model, adapter_path)

    print("Merging adapter into base model...")
    merged_model = model.merge_and_unload()

    print(f"Saving merged model to: {output_path}")
    merged_model.save_pretrained(output_path)

    tokenizer = AutoTokenizer.from_pretrained(model_cfg.model_name)
    tokenizer.save_pretrained(output_path)

    print("Done! Merged model saved.")
    print("\nTo upload to HuggingFace:")
    print(f"  huggingface-cli upload shoaib6174/fenlo-ai-llama3 {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge LoRA adapter")
    parser.add_argument("--adapter", required=True, help="Path to adapter directory")
    parser.add_argument("--output", default="./merged_model", help="Output path")
    args = parser.parse_args()
    merge(args.adapter, args.output)
