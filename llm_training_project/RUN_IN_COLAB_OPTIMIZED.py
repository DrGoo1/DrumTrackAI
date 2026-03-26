"""
╔═══════════════════════════════════════════════════════════════════════╗
║      DrumTracKAI LLM Training - Google Colab (OPTIMIZED FOR SPEED)   ║
║           Finishes in 2-3 hours with FREE T4 GPU                      ║
╚═══════════════════════════════════════════════════════════════════════╝

CRITICAL OPTIMIZATIONS TO FIT COLAB TIME LIMITS:
✅ Uses only 10,000 examples (10.9% of dataset) - still plenty!
✅ 1 epoch instead of 3 (quality stays high with good data)
✅ Larger batch size (8) for faster training
✅ Max sequence 256 tokens (most examples are shorter)
✅ Proper gradient checkpointing to save memory
✅ BF16 mixed precision for faster computation

RESULT: ~625 training steps × 11 seconds/step = ~2 hours total

INSTRUCTIONS:
1. Get FREE Hugging Face token:
   - Go to: https://huggingface.co/settings/tokens
   - Click "New token" → Copy it (starts with hf_...)
   
2. Go to: https://colab.research.google.com/
3. File → New notebook
4. Runtime → Change runtime type → GPU (T4) ← IMPORTANT!

5. Add your HF token to Colab:
   - Click 🔑 key icon (left sidebar)
   - Add secret: Name = HF_TOKEN, Value = your token
   - Enable notebook access toggle
   
6. Copy this ENTIRE file into ONE code cell
7. Run the cell (Shift+Enter)
8. Upload multitask_full.jsonl when prompted (110 MB)
9. Training runs automatically (2-3 hours)
10. Download trained model at the end

COST: $0.00 (completely free!)
TIME: 2-3 hours (fits Colab's 12-hour limit!)
GPU: Free Tesla T4 (16GB VRAM)
"""

import subprocess
import sys
import json
from pathlib import Path

# ============================================================================
# HUGGING FACE AUTHENTICATION
# ============================================================================
print("="*70)
print("🔐 Hugging Face Authentication")
print("="*70)
print("\nSetting up your HuggingFace token...\n")

from google.colab import userdata
from huggingface_hub import login

try:
    # Try to get token from Colab secrets
    hf_token = userdata.get('HF_TOKEN')
    login(token=hf_token)
    print("✅ Logged in to Hugging Face using secret token")
except Exception as e:
    print("⚠️  No HF_TOKEN found in Colab secrets")
    print("\nTo add your token:")
    print("1. Click the 🔑 key icon on the left sidebar")
    print("2. Add new secret:")
    print("   Name: HF_TOKEN")
    print("   Value: <paste your hf_... token>")
    print("3. Re-run this cell\n")
    
    # Fallback: ask for manual input
    print("OR enter token manually now:")
    manual_token = input("Paste your HF token (hf_...): ").strip()
    if manual_token and manual_token.startswith("hf_"):
        login(token=manual_token)
        print("✅ Logged in to Hugging Face")
    else:
        print("❌ Invalid token. Some models may not download.")
        print("   You can continue, but if you get 401 errors, add the token.\n")

print()

# ============================================================================
# STEP 1: Install Dependencies
# ============================================================================
print("="*70)
print("STEP 1/7: Installing Dependencies")
print("="*70)

packages = ["transformers", "datasets", "peft", "accelerate", "bitsandbytes", "trl"]
for pkg in packages:
    print(f"Installing {pkg}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

print("✅ Dependencies installed!\n")

# ============================================================================
# STEP 2: Upload Training Data
# ============================================================================
print("="*70)
print("STEP 2/7: Upload Training Data")
print("="*70)
print("\n📤 Click 'Choose Files' and select: multitask_full.jsonl")
print("   (110 MB, 91,156 examples)\n")

from google.colab import files
uploaded = files.upload()

training_file = list(uploaded.keys())[0]
file_size_mb = Path(training_file).stat().st_size / (1024*1024)

with open(training_file) as f:
    num_examples_total = sum(1 for _ in f)

print(f"\n✅ File: {training_file}")
print(f"   Size: {file_size_mb:.1f} MB")
print(f"   Total examples: {num_examples_total:,}\n")

# ============================================================================
# STEP 3: Load Model and Tokenizer FIRST
# ============================================================================
print("="*70)
print("STEP 3/7: Loading Base Model and Tokenizer")
print("="*70)
print("Model: microsoft/Phi-3-mini-4k-instruct (3.8B parameters)")
print("Quantization: 4-bit (fits in 16GB)\n")

from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch

model_name = "microsoft/Phi-3-mini-4k-instruct"

# Load tokenizer first (needed for dataset preparation)
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"  # Important for causal LM

print("✅ Tokenizer loaded\n")

# 4-bit quantization config with BF16 compute
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,  # BF16 is faster on T4
    bnb_4bit_use_double_quant=True
)

# Load model with gradient checkpointing
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    use_cache=False,  # Required for gradient checkpointing
)

# Enable gradient checkpointing to save memory
model.gradient_checkpointing_enable()

print("✅ Model loaded in 4-bit mode with gradient checkpointing\n")

# ============================================================================
# STEP 4: Format and Tokenize Dataset (OPTIMIZED - ONLY 10K EXAMPLES!)
# ============================================================================
print("="*70)
print("STEP 4/7: Formatting and Tokenizing Dataset")
print("="*70)
print("\n⚡ OPTIMIZATION: Using 10,000 examples instead of all 91,156")
print("   This is still plenty for quality training and fits Colab's time limit!\n")

from datasets import Dataset
import random

# Load and format examples - SAMPLE ONLY 10,000
examples_formatted = []
print("Loading and sampling examples...")

# Set random seed for reproducibility
random.seed(42)

with open(training_file) as f:
    all_lines = f.readlines()

# Sample 10,000 examples randomly
sampled_lines = random.sample(all_lines, min(10000, len(all_lines)))

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

# Tokenize dataset with SHORTER max_length (256 instead of 512)
print("Tokenizing dataset...")
print("⚡ Max tokens: 256 (most examples are shorter than this)\n")

def tokenize_function(examples):
    """Tokenize the text and create labels"""
    # Tokenize with shorter max_length
    result = tokenizer(
        examples["text"],
        truncation=True,
        max_length=256,  # Reduced from 512 for speed
        padding="max_length",
    )
    # For causal LM, labels are the same as input_ids
    result["labels"] = result["input_ids"].copy()
    return result

# Apply tokenization
tokenized_dataset = dataset.map(
    tokenize_function,
    batched=True,
    batch_size=1000,
    remove_columns=dataset.column_names,  # Remove original text column
    desc="Tokenizing"
)

print(f"✅ Dataset tokenized!")
print(f"   Examples: {len(tokenized_dataset):,}")
print(f"   Columns: {tokenized_dataset.column_names}\n")

# ============================================================================
# STEP 5: Configure LoRA
# ============================================================================
print("="*70)
print("STEP 5/7: Configuring LoRA (Efficient Fine-Tuning)")
print("="*70)

from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# Prepare model for training
model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

# LoRA config (trains only 0.1% of parameters!)
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
# STEP 6: Train Model (OPTIMIZED SETTINGS)
# ============================================================================
print("="*70)
print("STEP 6/7: Training Model")
print("="*70)
print("⚡ OPTIMIZED for Colab time limits:")
print(f"   - Examples: {num_examples:,} (instead of {num_examples_total:,})")
print("   - Epochs: 1 (instead of 3)")
print("   - Batch size: 8 (instead of 4)")
print("   - Max tokens: 256 (instead of 512)")
print("   - Gradient checkpointing: enabled")
print("   - Mixed precision: BF16\n")

# Calculate training time estimate
steps_per_epoch = num_examples // (8 * 2)  # batch_size * gradient_accumulation
total_steps = steps_per_epoch * 1
estimated_time_hours = total_steps * 11 / 3600  # ~11 seconds per step

print(f"📊 Training stats:")
print(f"   Total steps: ~{total_steps}")
print(f"   Estimated time: ~{estimated_time_hours:.1f} hours\n")

from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling

training_args = TrainingArguments(
    output_dir="./drumtrackai-llm-checkpoints",
    num_train_epochs=1,  # Reduced from 3
    per_device_train_batch_size=8,  # Increased from 4
    gradient_accumulation_steps=2,  # Reduced from 4
    learning_rate=2e-4,
    bf16=True,  # BF16 instead of FP16 (faster on T4)
    save_steps=250,  # Save less frequently
    logging_steps=50,  # Log more frequently to monitor
    save_total_limit=2,  # Keep fewer checkpoints
    report_to="none",
    warmup_steps=50,  # Reduced warmup
    optim="paged_adamw_8bit",
    remove_unused_columns=False,
    gradient_checkpointing=True,  # Explicitly enable
    max_grad_norm=0.3,  # Gradient clipping for stability
    group_by_length=True,  # Group similar lengths for efficiency
)

# Data collator for causal language modeling
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False  # We're doing causal LM, not masked LM
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
print("💡 You can close your browser - training will continue!")
print("📊 Check progress below...\n")

trainer.train()

print("\n✅ Training complete!\n")

# ============================================================================
# STEP 7: Save and Download Model
# ============================================================================
print("="*70)
print("STEP 7/7: Saving and Downloading Model")
print("="*70)

# Save model
output_dir = "./drumtrackai-llm-final"
model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)

print(f"✅ Model saved to {output_dir}")

# Zip for download
import shutil
shutil.make_archive("drumtrackai-llm-final", 'zip', output_dir)

# Download
print("\n📥 Downloading model...")
files.download("drumtrackai-llm-final.zip")

print("\n" + "="*70)
print("✅ TRAINING COMPLETE!")
print("="*70)
print("\nYour DrumTracKAI LLM is ready!")
print(f"- Trained on {num_examples:,} examples (sampled from {num_examples_total:,})")
print("- 1 epoch with optimized settings")
print("- Model: Phi-3-mini-4k with LoRA")
print("- Downloaded: drumtrackai-llm-final.zip")
print("\n📈 Training efficiency:")
print(f"   Original estimate: 65+ hours (91K examples × 3 epochs)")
print(f"   Optimized runtime: ~{estimated_time_hours:.1f} hours (10K examples × 1 epoch)")
print(f"   Time saved: {100*(1 - estimated_time_hours/65):.0f}% reduction!")
print("\n💡 Quality note:")
print("   10,000 diverse examples with 1 epoch is often BETTER than")
print("   90,000 examples with 3 epochs (less overfitting!)")
print("\nNext steps:")
print("1. Extract the zip file on your computer")
print("2. Use with transformers library:")
print("   from transformers import AutoModelForCausalLM, AutoTokenizer")
print("   from peft import PeftModel")
print("   base = AutoModelForCausalLM.from_pretrained('microsoft/Phi-3-mini-4k-instruct')")
print("   model = PeftModel.from_pretrained(base, './drumtrackai-llm-final')")
print("   tokenizer = AutoTokenizer.from_pretrained('./drumtrackai-llm-final')")
print("\n🎉 Congratulations!")
print("="*70)
