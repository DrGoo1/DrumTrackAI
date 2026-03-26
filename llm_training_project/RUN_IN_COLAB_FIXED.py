"""
╔═══════════════════════════════════════════════════════════════════════╗
║         DrumTracKAI LLM Training - Google Colab Script (FIXED)        ║
║              Complete Ready-to-Run Training Script                    ║
╚═══════════════════════════════════════════════════════════════════════╝

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
TIME: 2-3 hours
GPU: Free Tesla T4 (16GB VRAM)

FEATURES:
- Hugging Face authentication (free token required)
- Automatic dataset tokenization
- 4-bit quantization for GPU efficiency
- LoRA fine-tuning for fast training
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
    num_examples = sum(1 for _ in f)

print(f"\n✅ File: {training_file}")
print(f"   Size: {file_size_mb:.1f} MB")
print(f"   Examples: {num_examples:,}\n")

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

# 4-bit quantization config
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True
)

# Load model
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True
)

print("✅ Model loaded in 4-bit mode\n")

# ============================================================================
# STEP 4: Format and Tokenize Dataset
# ============================================================================
print("="*70)
print("STEP 4/7: Formatting and Tokenizing Dataset")
print("="*70)

from datasets import Dataset

# Load and format examples
examples_formatted = []
print("Loading examples...")
with open(training_file) as f:
    for i, line in enumerate(f):
        ex = json.loads(line)
        task = ex.get('task', '')
        inp = json.dumps(ex.get('input', {}))
        out = json.dumps(ex.get('output', {}))
        
        # Format as instructional text
        text = f"Task: {task}\nInput: {inp}\nOutput: {out}"
        examples_formatted.append({"text": text})
        
        if (i + 1) % 10000 == 0:
            print(f"  Loaded {i+1:,} examples...")

dataset = Dataset.from_list(examples_formatted)
print(f"✅ Loaded {len(dataset):,} examples\n")

# Tokenize dataset
print("Tokenizing dataset (this may take 5-10 minutes)...")

def tokenize_function(examples):
    """Tokenize the text and create labels"""
    # Tokenize
    result = tokenizer(
        examples["text"],
        truncation=True,
        max_length=512,
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
print(f"   Columns: {tokenized_dataset.column_names}")
print(f"   Features: {tokenized_dataset.features}\n")

# ============================================================================
# STEP 5: Configure LoRA
# ============================================================================
print("="*70)
print("STEP 5/7: Configuring LoRA (Efficient Fine-Tuning)")
print("="*70)

from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# Prepare model for training
model = prepare_model_for_kbit_training(model)

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
# STEP 6: Train Model
# ============================================================================
print("="*70)
print("STEP 6/7: Training Model")
print("="*70)
print("This will take 2-3 hours. You can monitor progress below.")
print(f"Training with {num_examples:,} examples over 3 epochs\n")

from transformers import TrainingArguments, Trainer, DataCollatorForLanguageModeling

training_args = TrainingArguments(
    output_dir="./drumtrackai-llm-checkpoints",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    fp16=True,
    save_steps=500,
    logging_steps=100,
    save_total_limit=3,
    report_to="none",
    warmup_steps=100,
    optim="paged_adamw_8bit",
    remove_unused_columns=False,  # Keep all columns
)

# Data collator for causal language modeling
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False  # We're doing causal LM, not masked LM
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,  # Use tokenized dataset!
    data_collator=data_collator
)

print("🚀 Starting training...")
print("="*70)

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
print(f"- Trained on {num_examples:,} examples")
print("- Model: Phi-3-mini-4k with LoRA")
print("- Downloaded: drumtrackai-llm-final.zip")
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
