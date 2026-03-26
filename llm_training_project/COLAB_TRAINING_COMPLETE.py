"""
╔═══════════════════════════════════════════════════════════════════════╗
║  DrumTracKAI LLM Training - Google Colab Complete Script             ║
║  Copy this ENTIRE file into Google Colab and run!                    ║
╚═══════════════════════════════════════════════════════════════════════╝

INSTRUCTIONS:
1. Go to: https://colab.research.google.com/
2. File → New notebook
3. Runtime → Change runtime type → GPU (T4)
4. Copy this ENTIRE script into a code cell
5. Run the cell (Ctrl+Enter)
6. Upload multitask_full.jsonl when prompted
7. Wait 2-3 hours
8. Download trained model at the end

COST: $0.00
TIME: 2-3 hours
"""

# ============================================================================
# STEP 1: Install All Dependencies
# ============================================================================
print("=" * 70)
print("STEP 1/6: Installing Dependencies...")
print("=" * 70)

import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])

packages = [
    "transformers",
    "datasets", 
    "peft",
    "accelerate",
    "bitsandbytes",
    "trl",
    "torch"
]

for pkg in packages:
    print(f"Installing {pkg}...")
    install(pkg)

print("✅ All dependencies installed!\n")

# ============================================================================
# STEP 2: Upload Training Data
# ============================================================================
print("=" * 70)
print("STEP 2/6: Upload Training Data")
print("=" * 70)
print("\n📤 Please upload your multitask_full.jsonl file...")
print("   (Should be ~110 MB with 91,156 examples)\n")

from google.colab import files
uploaded = files.upload()

if not uploaded:
    print("❌ No file uploaded! Please run again and upload the file.")
    sys.exit(1)

training_file = list(uploaded.keys())[0]
print(f"\n✅ Uploaded: {training_file}\n")

# Verify file
import json
from pathlib import Path

file_path = Path(training_file)
file_size_mb = file_path.stat().st_size / (1024 * 1024)

with file_path.open('r') as f:
    num_lines = sum(1 for _ in f)

print(f"📊 File Info:")
print(f"   Size: {file_size_mb:.1f} MB")
print(f"   Examples: {num_lines:,}")
print()

if num_lines < 1000:
    print("⚠️  Warning: File seems too small. Expected ~91,000 examples.")
    print("   Continuing anyway...\n")

# ============================================================================
# STEP 3: Format Dataset for Training
# ============================================================================
print("=" * 70)
print("STEP 3/6: Formatting Dataset...")
print("=" * 70)

from datasets import Dataset

def format_example(example):
    """Convert DrumTracKAI format to chat format"""
    task = example.get('task', 'unknown')
    input_data = json.dumps(example.get('input', {}), indent=2)
    output_data = json.dumps(example.get('output', {}), indent=2)
    
    # Create chat-style prompt
    text = f"""<|system|>You are a professional drummer AI trained on 91,000+ patterns. You analyze drum patterns, explain concepts, and generate realistic performances.<|end|>
