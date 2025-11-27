#!/usr/bin/env python3
"""
Local LLM Training Script
==========================
Train LLaMA/Mixtral/Phi locally on drum training data using Hugging Face transformers
"""
import json
import os
from pathlib import Path
from typing import Optional
import logging

try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling
    )
    from datasets import load_dataset
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️  transformers not installed. Install with:")
    print("   pip install transformers datasets torch accelerate bitsandbytes")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_prompt(example: dict) -> str:
    """Format training example as chat prompt"""
    task = example.get("task", "unknown")
    input_data = example.get("input", {})
    output_data = example.get("output", {})
    
    if task == "analyze_pattern":
        tempo = input_data.get("tempo", 0)
        hits = input_data.get("total_hits", 0)
        style = output_data.get("style", "unknown")
        ghosts = output_data.get("ghost_notes", 0)
        
        prompt = f"""<|system|>You are a professional drummer AI analyzing drum patterns.<|end|>
