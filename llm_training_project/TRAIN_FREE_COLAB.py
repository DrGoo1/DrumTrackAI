"""
DrumTracKAI LLM Training - Google Colab Script
==============================================
Copy this entire script into a Google Colab cell and run it!

Steps:
1. Go to: https://colab.research.google.com/
2. Runtime → Change runtime type → GPU (T4)
3. Create new cell, paste this entire script
4. Upload multitask_full.jsonl when prompted
5. Run the cell
6. Wait 2-4 hours
7. Download trained model

Cost: $0.00
"""

# ============================================================================
# PART 1: Install Dependencies
# ============================================================================
print("📦 Installing dependencies...")
!pip install -q transformers datasets peft accelerate bitsandbytes trl torch

# ============================================================================
# PART 2: Upload Training Data
# ============================================================================
print("\n📤 Upload your training data...")
from google.colab import files
uploaded = files.upload()  # Click "Choose Files" and select multitask_full.jsonl
training_file = list(uploaded.keys())[0]
print(f"✅ Uploaded: {training_file}")

# ============================================================================
# PART 3: Prepare Dataset
# ============================================================================
print("\n🔧 Preparing dataset...")
import json
from datasets import Dataset

def load_and_format_data(jsonl_path):
    """Load JSONL and convert to chat format"""
    examples = []
    
    with open(jsonl_path, 'r') as f:
        for line in f:
            ex = json.loads(line)
            
            task = ex.get('task', '')
            inp = json.dumps(ex.get('input', {}), indent=2)
            out = json.dumps(ex.get('output', {}), indent=2)
            
            # Format as chat
            text = f"""<|system|>You are a professional drummer AI trained to analyze patterns, explain concepts, and generate drum performances.<|end|>
