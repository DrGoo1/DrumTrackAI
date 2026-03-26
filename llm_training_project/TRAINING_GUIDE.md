# 🎓 LLM Training Guide

**Complete guide for training DrumTracKAI drummer LLM**

---

## 📊 **Training Data Summary**

### **Available Dataset:**
```
llm_training_project/training_datasets/multitask_full.jsonl
91,156 examples
110 MB
```

### **Contents:**
- **91,074** E-GMD professional pattern analyses
- **44** Public domain drum instruction
- **38** Jamstix brain concepts

---

## 🤖 **Training Options**

### **Option A: OpenAI Fine-Tuning** ⭐ EASIEST

**Best for:**
- Quick deployment
- No local GPU needed
- Production-ready API

**Cost:** ~$2-5 per training run (GPT-4.1)

**Steps:**

1. **Install OpenAI CLI:**
```bash
pip install openai
```

2. **Set API Key:**
```bash
set OPENAI_API_KEY=your-api-key-here
```

3. **Prepare Data (already done):**
```bash
# Your file is ready: multitask_full.jsonl
```

4. **Upload and Train:**
```bash
# Upload training file
openai api fine_tunes.create \
  -t llm_training_project/training_datasets/multitask_full.jsonl \
  -m gpt-4.1-turbo \
  --suffix "drumtrackai-drummer-v1"

# Monitor training
openai api fine_tunes.follow -i <fine-tune-id>
```

5. **Use Trained Model:**
```python
import openai
response = openai.ChatCompletion.create(
    model="ft:gpt-4.1-turbo:drumtrackai-drummer-v1",
    messages=[
        {"role": "system", "content": "You are a professional drummer AI."},
        {"role": "user", "content": "Analyze this drum pattern..."}
    ]
)
```

---

### **Option B: Local LLaMA/Mixtral Training**

**Best for:**
- Full control
- No API costs
- Custom modifications
- Offline deployment

**Requirements:**
- GPU with 24GB+ VRAM (RTX 4090, A100)
- ~200GB disk space
- Python 3.10+

**Steps:**

1. **Install Dependencies:**
```bash
pip install transformers datasets torch accelerate bitsandbytes peft
```

2. **Choose Base Model:**
```bash
# Small (7B params) - Fits on 24GB GPU
meta-llama/Llama-3-8B
microsoft/Phi-3-mini-4k-instruct

# Medium (13-14B params) - Needs 40GB+ GPU
mistralai/Mixtral-8x7B-Instruct-v0.1

# Large (70B params) - Needs multi-GPU or quantization
meta-llama/Llama-3-70B
```

3. **Format Data:**
```python
# Convert JSONL to Hugging Face format
# (Script provided below)
python convert_to_hf_format.py
```

4. **Train with LoRA (efficient):**
```bash
# 4-bit quantization for consumer GPUs
python train_lora.py \
  --model_name meta-llama/Llama-3-8B \
  --data_path training_datasets/multitask_full.jsonl \
  --output_dir models/drumtrackai-llama3-8b \
  --num_epochs 3 \
  --batch_size 4 \
  --learning_rate 2e-4
```

5. **Inference:**
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model = AutoModelForCausalLM.from_pretrained(
    "models/drumtrackai-llama3-8b",
    torch_dtype=torch.float16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3-8B")

# Use model
prompt = "Analyze this drum pattern: tempo=120, hits=256..."
inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
outputs = model.generate(**inputs, max_length=512)
print(tokenizer.decode(outputs[0]))
```

---

### **Option C: Cloud Training (Replicate/Together AI)**

**Best for:**
- No local hardware
- Pay per training run
- Easy deployment

**Replicate:**
```bash
# Upload to Replicate
replicate models create drumtrackai/drummer-llm

# Train
replicate trainings create \
  --destination drumtrackai/drummer-llm \
  --model meta/llama-3-70b \
  --training_data multitask_full.jsonl
```

**Together AI:**
```bash
# Similar process via Together AI dashboard
# Upload JSONL → Select base model → Train
```

---

## 📝 **Data Format Requirements**

### **OpenAI Format:**
Already compatible! Each line is:
```json
{
  "task": "analyze_pattern",
  "input": {...},
  "output": {...}
}
```

### **Hugging Face Format:**
Need to convert to chat format:
```json
{
  "messages": [
    {"role": "system", "content": "You are a drummer AI"},
    {"role": "user", "content": "Analyze pattern with tempo=120..."},
    {"role": "assistant", "content": "Style: rock, Ghost notes: 15..."}
  ]
}
```

---

## ⚙️ **Training Configuration**

### **Recommended Hyperparameters:**

**OpenAI Fine-tuning:**
```
n_epochs: 3
batch_size: auto
learning_rate_multiplier: 0.1
```

**Local Training (LoRA):**
```
epochs: 3-5
batch_size: 4-8 (depending on GPU)
learning_rate: 2e-4
lora_r: 16
lora_alpha: 32
lora_dropout: 0.05
max_seq_length: 2048
```

---

## 🚀 **Quick Start (OpenAI)**

```bash
# 1. Install
pip install openai

# 2. Set key
set OPENAI_API_KEY=sk-...

# 3. Train
openai api fine_tunes.create \
  -t llm_training_project/training_datasets/multitask_full.jsonl \
  -m gpt-4.1-turbo \
  --suffix "drumtrackai-v1"

# 4. Wait (~30-60 min for 91K examples)

# 5. Use
openai api chat.completions.create \
  --model ft:gpt-4.1-turbo:drumtrackai-v1 \
  --messages '[{"role":"user","content":"Analyze drum pattern..."}]'
```

---

## 📈 **Expected Results**

### **After Training:**

**Pattern Analysis:**
- Accurate style classification (jazz/funk/rock/latin)
- Ghost note detection
- Accent recognition
- Swing detection

**Drum Reasoning:**
- Explain rudiments
- Apply brain concepts (priority, timing, limbs)
- Validate playability
- Suggest improvements

**Drummer Emulation:**
- Bonham, Purdie, Gadd, Porcaro styles
- Appropriate velocity profiles
- Timing feel adjustments

---

## 🐛 **Troubleshooting**

### **OpenAI Issues:**

**"File format invalid":**
```bash
# Check JSONL format
head -n 1 multitask_full.jsonl | jq .
```

**"Training stuck":**
- Check OpenAI dashboard for status
- Large datasets take time (91K examples ~ 1 hour)

### **Local Training Issues:**

**CUDA out of memory:**
```python
# Use 4-bit quantization
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    load_in_4bit=True,
    device_map="auto"
)
```

**Slow training:**
```python
# Reduce batch size or use gradient accumulation
training_args = TrainingArguments(
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4
)
```

---

## 📦 **Deliverables**

After training, you'll have:

1. **Trained Model:**
   - OpenAI: `ft:gpt-4.1-turbo:drumtrackai-v1`
   - Local: `models/drumtrackai-llama3-8b/`

2. **Model Card** (create):
   - Training data description
   - Capabilities
   - Limitations
   - Example prompts

3. **API Integration:**
   - Add to DrumTracKAI backend
   - Create `/llm/analyze` endpoint
   - Use for pattern generation

---

## 🎯 **Next Steps**

1. **Choose training option** (OpenAI recommended for ease)
2. **Run training** (multitask_full.jsonl ready)
3. **Test model** on sample patterns
4. **Integrate** into DrumTracKAI
5. **Deploy** to production

---

## 📞 **Support Files**

This directory contains:
- `multitask_full.jsonl` - Training data ✅
- `train_openai.sh` - OpenAI training script
- `train_lora.py` - Local LoRA training script
- `convert_to_hf_format.py` - Format converter
- `test_trained_model.py` - Testing script

---

**Training data ready! Choose your training method and proceed!** 🚀
