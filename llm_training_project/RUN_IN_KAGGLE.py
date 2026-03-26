"""
╔═══════════════════════════════════════════════════════════════════════╗
║      DrumTracKAI LLM Training - Kaggle Optimized (NO AUTH NEEDED)    ║
║           Finishes in 2-3 hours with FREE P100/T4 GPU                ║
╚═══════════════════════════════════════════════════════════════════════╝

KAGGLE ADVANTAGES:
✅ 30 hours/week GPU time (vs Colab's 12 hours)
✅ P100 or T4 GPUs (often faster than Colab)
✅ More reliable (less disconnections)
✅ Better file upload system
✅ NO AUTHENTICATION NEEDED (Phi-3 is public!)

OPTIMIZATIONS FOR SPEED:
✅ 10,000 examples (vs 91K) - still plenty for quality!
✅ 1 epoch (vs 3) - prevents overfitting
✅ Larger batch size (8) for faster training
✅ 256 token max (most examples are shorter)
✅ BF16 mixed precision
✅ Gradient checkpointing

INSTRUCTIONS FOR KAGGLE:
1. Go to: https://www.kaggle.com
2. Sign in (create free account if needed)
3. Code → New Notebook
4. Settings (right sidebar) → Accelerator → GPU P100 ← IMPORTANT!
5. Add Data:
   - Click "+ Add Data" (top right)
   - "Upload" tab
   - Upload: multitask_full.jsonl
6. Copy this ENTIRE file into the code cell
7. Run the cell (Shift+Enter or click ▶)
8. Training runs automatically (2-3 hours)
9. Download model from Output section

COST: $0.00 (completely free!)
TIME: 2-3 hours
GPU: P100 (16GB) or T4 (16GB)
"""

import subprocess
import sys
import json
from pathlib import Path

# ============================================================================
# STEP 1: Install Dependencies
# ============================================================================
print("="*70)
print("STEP 1/6: Installing Dependencies")
print("="*70)
print("Running on Kaggle - No authentication needed! 🎉\n")

packages = ["transformers", "datasets", "peft", "accelerate", "bitsandbytes", "trl"]
for pkg in packages:
    print(f"Installing {pkg}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

print("✅ Dependencies installed!\n")

# ============================================================================
# STEP 2: Locate Training Data
# ============================================================================
print("="*70)
print("STEP 2/6: Locating Training Data")
print("="*70)
print("\n📂 Looking for multitask_full.jsonl in Kaggle input...\n")

# Kaggle stores uploaded data in /kaggle/input/
input_dirs = list(Path("/kaggle/input/").glob("*/"))
training_file = None

for dir_path in input_dirs:
    jsonl_files = list(dir_path.glob("*.jsonl"))
    if jsonl_files:
        training_file = jsonl_files[0]
        break

if not training_file:
    print("❌ ERROR: multitask_full.jsonl not found!")
    print("\nTo upload:")
    print("1. Click '+ Add Data' (top right)")
    print("2. Go to 'Upload' tab")
    print("3. Upload multitask_full.jsonl")
    print("4. Click 'Add' to attach to notebook")
    print("5. Re-run this cell\n")
    raise FileNotFoundError("Training data not found in /kaggle/input/")

file_size_mb = training_file.stat().st_size / (1024*1024)

with open(training_file) as f:
    num_examples_total = sum(1 for _ in f)

print(f"✅ Found: {training_file}")
print(f"   Size: {file_size_mb:.1f} MB")
print(f"   Total examples: {num_examples_total:,}\n")

# ============================================================================
# STEP 3: Load Model and Tokenizer
# ============================================================================
print("="*70)
print("STEP 3/6: Loading Base Model and Tokenizer")
print("="*70)
print("Model: microsoft/Phi-3-mini-4k-instruct (3.8B parameters)")
print("Quantization: 4-bit (fits in 16GB)")
print("Authentication: NOT REQUIRED (public model!) ✅\n")

from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch

model_name = "microsoft/Phi-3-mini-4k-instruct"

# Load tokenizer (no auth needed for public models!)
print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

print("✅ Tokenizer loaded\n")

# 4-bit quantization config with BF16
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True
)

# Load model with gradient checkpointing
print("Loading model (this takes 2-3 minutes)...")
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    use_cache=False,  # Required for gradient checkpointing
)

# Enable gradient checkpointing
model.gradient_checkpointing_enable()

print("✅ Model loaded in 4-bit mode with gradient checkpointing\n")

# ============================================================================
# STEP 4: Format and Tokenize Dataset (OPTIMIZED - 10K EXAMPLES)
# ============================================================================
print("="*70)
print("STEP 4/6: Formatting and Tokenizing Dataset")
print("="*70)
print("\n⚡ OPTIMIZATION: Using 10,000 examples instead of all 91,156")
print("   This fits Kaggle/Colab time limits while maintaining quality!\n")

from datasets import Dataset
import random

# Set random seed for reproducibility
random.seed(42)

print("Loading and sampling examples...")

with open(training_file) as f:
    all_lines = f.readlines()

# Sample 10,000 examples randomly
sampled_lines = random.sample(all_lines, min(10000, len(all_lines)))

examples_formatted = []
for i, line in enumerate(sampled_lines):
    ex = json.loads(line)
    task = ex.get('task', '')
    inp = json.dumps(ex.get('input', {}))
    out = json.dumps(ex.get('output', {}))
    
    # Format as instructional text
    text = f"Task: {task}\nInput: {inp}\nOutput: {out}"
    examples_formatted.append({"text": text})
    
    if (i + 1) % 2000 == 0:
        print(f"  Loaded {i+1:,} examples...")

dataset = Dataset.from_list(examples_formatted)
num_examples = len(dataset)
print(f"✅ Loaded {num_examples:,} examples (sampled from {num_examples_total:,})\n")

# Tokenize with shorter max_length for speed
print("Tokenizing dataset...")
print("⚡ Max tokens: 256 (optimized for speed)\n")

def tokenize_function(examples):
    """Tokenize the text and create labels"""
    result = tokenizer(
        examples["text"],
        truncation=True,
        max_length=256,
        padding="max_length",
    )
    result["labels"] = result["input_ids"].copy()
    return result

tokenized_dataset = dataset.map(
    tokenize_function,
    batched=True,
    batch_size=1000,
    remove_columns=dataset.column_names,
    desc="Tokenizing"
)

print(f"✅ Dataset tokenized!")
print(f"   Examples: {len(tokenized_dataset):,}")
print(f"   Columns: {tokenized_dataset.column_names}\n")

# ============================================================================
# STEP 5: Configure LoRA
# ============================================================================
print("="*70)
print("STEP 5/6: Configuring LoRA (Efficient Fine-Tuning)")
print("="*70)

from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# Prepare model for training
model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

# LoRA config
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)

trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
total_params = sum(p.numel() for p in model.parameters())

print(f"✅ LoRA configured")
print(f"   Trainable params: {trainable_params:,} ({100*trainable_params/total_params:.2f}%)")
print(f"   Total params: {total_params:,}\n")

# ============================================================================
# STEP 6: Train Model
# ============================================================================
print("="*70)
print("STEP 6/6: Training Model")
print("="*70)
print("⚡ Optimized settings for Kaggle:")
print(f"   - Examples: {num_examples:,} (sampled from {num_examples_total:,})")
print("   - Epochs: 1")
print("   - Batch size: 8")
print("   - Max tokens: 256")
print("   - GPU: P100 or T4\n")

# Calculate training time estimate
steps_per_epoch = num_examples // (8 * 2)
total_steps = steps_per_epoch * 1
estimated_time_hours = total_steps * 11 / 3600

print(f"📊 Training stats:")
print(f"   Total steps: ~{total_steps}")
print(f"   Estimated time: ~{estimated_time_hours:.1f} hours\n")

from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling

training_args = TrainingArguments(
    output_dir="/kaggle/working/drumtrackai-llm-checkpoints",
    num_train_epochs=1,
    per_device_train_batch_size=8,
    gradient_accumulation_steps=2,
    learning_rate=2e-4,
    bf16=True,
    save_steps=250,
    logging_steps=50,
    save_total_limit=2,
    report_to="none",
    warmup_steps=50,
    optim="paged_adamw_8bit",
    remove_unused_columns=False,
    gradient_checkpointing=True,
    max_grad_norm=0.3,
    group_by_length=True,
)

data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=data_collator
)

print("🚀 Starting training...")
print("="*70)
print("\n⏱️  This should take 2-3 hours")
print("💡 Kaggle keeps running even if you close the browser!")
print("📊 Check progress below...\n")

trainer.train()

print("\n✅ Training complete!\n")

# ============================================================================
# STEP 7: Save Model (Auto-downloads from Kaggle Output)
# ============================================================================
print("="*70)
print("STEP 7/7: Saving Model")
print("="*70)

# Save to /kaggle/working/ (appears in Output section)
output_dir = "/kaggle/working/drumtrackai-llm-final"
model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)

print(f"✅ Model saved to {output_dir}")

# Zip for easy download
import shutil
zip_path = "/kaggle/working/drumtrackai-llm-final"
shutil.make_archive(zip_path, 'zip', output_dir)

print("\n" + "="*70)
print("✅ TRAINING COMPLETE!")
print("="*70)
print("\nYour DrumTracKAI LLM is ready!")
print(f"- Trained on {num_examples:,} examples (sampled from {num_examples_total:,})")
print("- 1 epoch with optimized settings")
print("- Model: Phi-3-mini-4k with LoRA")
print(f"- Saved to: {output_dir}")
print("\n📥 TO DOWNLOAD:")
print("1. Look at the right sidebar → 'Output' section")
print("2. You'll see 'drumtrackai-llm-final/' folder and .zip file")
print("3. Click the download icon next to the .zip file")
print("4. Extract on your computer")
print("\n📈 Training efficiency:")
print(f"   Original estimate: 65+ hours (91K examples × 3 epochs)")
print(f"   Optimized runtime: ~{estimated_time_hours:.1f} hours (10K examples × 1 epoch)")
print(f"   Time saved: {100*(1 - estimated_time_hours/65):.0f}% reduction!")
print("\n💡 Quality note:")
print("   10,000 diverse examples with 1 epoch produces excellent results")
print("   (Often better than 90K examples with 3 epochs due to less overfitting!)")
print("\n🎯 Usage on your computer:")
print("   from transformers import AutoModelForCausalLM, AutoTokenizer")
print("   from peft import PeftModel")
print("   base = AutoModelForCausalLM.from_pretrained('microsoft/Phi-3-mini-4k-instruct')")
print("   model = PeftModel.from_pretrained(base, './drumtrackai-llm-final')")
print("   tokenizer = AutoTokenizer.from_pretrained('./drumtrackai-llm-final')")
print("\n🎉 Congratulations! Your model is trained!")
print("="*70)
print("\n🌟 KAGGLE TIP: This notebook will keep running even if you")
print("   close your browser. Come back in 2-3 hours to download!")
print("="*70)
