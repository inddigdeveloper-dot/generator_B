"""
Fine-Tuning Pipeline — Phase 3
Uses Unsloth (fastest LoRA trainer, CPU-friendly, 2x faster than HuggingFace trainer)

Base model: Llama 3.2 3B Instruct (Meta, Apache 2.0 license, ~6GB in 4-bit)
Method:     QLoRA (4-bit quantization + LoRA adapters)
Result:     A tiny adapter (~50-100MB) that steers the base model for review generation

Requirements (install on your VPS or colab):
    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
    pip install --no-deps "xformers<0.0.27" "trl<0.9.0" peft accelerate bitsandbytes

Usage:
    python finetune.py --data training_data.jsonl --output ./review-model

After training:
    - Push adapter to HuggingFace (private repo): python finetune.py --push
    - Or convert to GGUF for Ollama: python finetune.py --export-gguf
"""

import argparse
import json
from pathlib import Path


def load_dataset(path: str):
    """Load Alpaca-format JSONL into HuggingFace Dataset."""
    from datasets import Dataset

    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Loaded {len(records)} training examples")
    return Dataset.from_list(records)


def format_prompt(example: dict, tokenizer) -> dict:
    """
    Format each example into the Alpaca chat template.
    This is what the model sees during training.
    """
    system = "You are a review generation assistant for local businesses. Write short, human-sounding Google reviews."

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"{example['instruction']}\n\n{example['input']}"},
        {"role": "assistant", "content": example["output"]},
    ]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    return {"text": text}


def train(data_path: str, output_dir: str, epochs: int = 3, batch_size: int = 2):
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments

    # ─── Load base model in 4-bit ───────────────────────────────────────────
    print("Loading Llama 3.2 3B Instruct in 4-bit...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Llama-3.2-3B-Instruct",
        max_seq_length=512,       # reviews are short, 512 is plenty
        dtype=None,               # auto-detect
        load_in_4bit=True,        # QLoRA — saves ~75% VRAM
    )

    # ─── Apply LoRA adapters ─────────────────────────────────────────────────
    # Only these layers are trained — everything else is frozen.
    # Total trainable params: ~2-5M out of 3B (0.1%)
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,                     # LoRA rank — 16 is balanced quality/size
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0.0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    # ─── Load and format dataset ─────────────────────────────────────────────
    raw_dataset = load_dataset(data_path)
    dataset = raw_dataset.map(
        lambda ex: format_prompt(ex, tokenizer),
        remove_columns=raw_dataset.column_names,
    )

    # ─── Training arguments ──────────────────────────────────────────────────
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,   # effective batch = batch_size * 4
        warmup_steps=10,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        save_strategy="epoch",
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=42,
        report_to="none",                # disable wandb/tensorboard
    )

    # ─── Train ──────────────────────────────────────────────────────────────
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=512,
        args=training_args,
    )

    print("Starting training...")
    trainer.train()

    # ─── Save LoRA adapter only (~50-100MB) ──────────────────────────────────
    adapter_path = str(Path(output_dir) / "adapter")
    model.save_pretrained(adapter_path)
    tokenizer.save_pretrained(adapter_path)
    print(f"Adapter saved → {adapter_path}")

    return model, tokenizer, adapter_path


def export_to_gguf(adapter_path: str, output_dir: str):
    """
    Merge LoRA adapter into base model and export to GGUF (Ollama format).
    After this, run:  ollama create review-gen -f Modelfile
    """
    from unsloth import FastLanguageModel

    print("Loading adapter for GGUF export...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=adapter_path,
        max_seq_length=512,
        dtype=None,
        load_in_4bit=True,
    )

    gguf_path = str(Path(output_dir) / "review-gen-q4.gguf")
    print(f"Exporting to GGUF → {gguf_path}")
    model.save_pretrained_gguf(
        output_dir,
        tokenizer,
        quantization_method="q4_k_m",   # 4-bit, best quality/size tradeoff
    )
    print(f"GGUF saved → {gguf_path}")

    # Write the Ollama Modelfile
    modelfile = f"""FROM {gguf_path}
SYSTEM "You are a review generation assistant. Write short, human-sounding Google reviews."
PARAMETER temperature 0.8
PARAMETER top_p 0.95
PARAMETER num_predict 200
PARAMETER stop "\\n\\n"
"""
    modelfile_path = Path(output_dir) / "Modelfile"
    modelfile_path.write_text(modelfile)
    print(f"\nOllama Modelfile → {modelfile_path}")
    print("\nNext steps:")
    print("  1. Copy the GGUF and Modelfile to your VPS")
    print("  2. Run:  ollama create review-gen -f Modelfile")
    print("  3. Test: ollama run review-gen 'Write a 5-star review for a coffee shop'")
    print("  4. Set in .env:  LLM_PROVIDER=ollama  OLLAMA_MODEL=review-gen")


def push_to_huggingface(adapter_path: str, repo_id: str, token: str):
    """Push adapter to a private HuggingFace repo (optional)."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"Pushing adapter → hf.co/{repo_id}")
    model = AutoModelForCausalLM.from_pretrained(adapter_path)
    tokenizer = AutoTokenizer.from_pretrained(adapter_path)
    model.push_to_hub(repo_id, token=token, private=True)
    tokenizer.push_to_hub(repo_id, token=token, private=True)
    print("Done. Pull with:  ollama pull hf.co/{repo_id}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="training_data.jsonl")
    parser.add_argument("--output", default="./review-model")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--export-gguf", action="store_true", help="Export to GGUF after training")
    parser.add_argument("--push", help="HuggingFace repo id (e.g. yourname/review-gen)")
    parser.add_argument("--hf-token", default=None)
    args = parser.parse_args()

    model, tokenizer, adapter_path = train(
        data_path=args.data,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )

    if args.export_gguf:
        export_to_gguf(adapter_path, args.output)

    if args.push:
        token = args.hf_token or input("HuggingFace token: ")
        push_to_huggingface(adapter_path, args.push, token)


if __name__ == "__main__":
    main()
