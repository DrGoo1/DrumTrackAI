#!/usr/bin/env python3
"""
Estimate OpenAI Fine-Tuning Cost
=================================
"""
import json
from pathlib import Path

def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~1 token per 4 characters"""
    return len(text) // 4

def main():
    training_file = Path("training_datasets/multitask_full.jsonl")
    
    print("=" * 70)
    print("OPENAI FINE-TUNING COST ESTIMATOR")
    print("=" * 70)
    print()
    
    # Sample first 100 examples to get average size
    total_tokens = 0
    num_samples = 0
    max_samples = 100
    
    with training_file.open('r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= max_samples:
                break
            
            example = json.loads(line)
            
            # Format as chat message (approximate)
            task = example.get("task", "")
            input_data = json.dumps(example.get("input", {}))
            output_data = json.dumps(example.get("output", {}))
            
            # Rough formatting
            formatted = f"Task: {task}\nInput: {input_data}\nOutput: {output_data}"
            
            tokens = estimate_tokens(formatted)
            total_tokens += tokens
            num_samples += 1
    
    # Calculate average
    avg_tokens_per_example = total_tokens / num_samples
    
    # Get total examples
    with training_file.open('r') as f:
        total_examples = sum(1 for _ in f)
    
    # Total tokens
    estimated_total_tokens = int(avg_tokens_per_example * total_examples)
    estimated_total_tokens_millions = estimated_total_tokens / 1_000_000
    
    print(f"📊 Training Data Analysis:")
    print(f"   Examples sampled: {num_samples}")
    print(f"   Avg tokens/example: {avg_tokens_per_example:.1f}")
    print(f"   Total examples: {total_examples:,}")
    print(f"   Estimated total tokens: {estimated_total_tokens:,}")
    print(f"   = {estimated_total_tokens_millions:.2f}M tokens")
    print()
    
    # OpenAI gpt-4o-mini pricing (as of Nov 2024)
    # https://openai.com/api/pricing/
    TRAINING_COST_PER_M = 3.00  # $3.00 per 1M tokens
    INPUT_COST_PER_M = 0.30     # $0.30 per 1M tokens (inference)
    OUTPUT_COST_PER_M = 1.20    # $1.20 per 1M tokens (inference)
    
    # Training cost (tokens are processed multiple times during training)
    # With 3 epochs, tokens are seen 3x
    EPOCHS = 3
    training_tokens = estimated_total_tokens * EPOCHS
    training_cost = (training_tokens / 1_000_000) * TRAINING_COST_PER_M
    
    print(f"💰 Cost Breakdown (gpt-4o-mini-2024-07-18):")
    print(f"   Training rate: ${TRAINING_COST_PER_M:.2f} per 1M tokens")
    print(f"   Epochs: {EPOCHS}")
    print(f"   Training tokens: {training_tokens:,} ({training_tokens/1_000_000:.2f}M)")
    print(f"   ")
    print(f"   TRAINING COST: ${training_cost:.2f}")
    print()
    
    print(f"📊 Cost Range Estimates:")
    
    # Conservative (if avg is higher)
    conservative_multiplier = 1.5
    conservative_cost = training_cost * conservative_multiplier
    
    # Optimistic (if avg is lower)
    optimistic_multiplier = 0.7
    optimistic_cost = training_cost * optimistic_multiplier
    
    print(f"   Best case (shorter examples): ${optimistic_cost:.2f}")
    print(f"   Expected (current estimate): ${training_cost:.2f}")
    print(f"   Worst case (longer examples): ${conservative_cost:.2f}")
    print()
    
    print(f"🎯 Most Likely Cost: ${training_cost:.2f}")
    print()
    
    print(f"ℹ️  Additional Notes:")
    print(f"   - This is ONE-TIME training cost")
    print(f"   - Inference costs are separate:")
    print(f"     • Input: ${INPUT_COST_PER_M:.2f}/1M tokens")
    print(f"     • Output: ${OUTPUT_COST_PER_M:.2f}/1M tokens")
    print(f"   - Training time: 30-60 minutes")
    print(f"   - You can reuse the trained model indefinitely")
    print()
    
    print(f"💡 Comparison:")
    print(f"   - GPT-4 Turbo training: ~${training_cost * 25:.2f} (25x more expensive)")
    print(f"   - GPT-3.5 Turbo training: ~${training_cost * 0.27:.2f} (cheaper but less capable)")
    print()
    
    print("=" * 70)
    print(f"ESTIMATED COST: ${training_cost:.2f}")
    print("=" * 70)

if __name__ == "__main__":
    main()
