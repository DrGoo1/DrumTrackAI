#!/usr/bin/env python3
"""
Combine All Training Datasets
==============================
Combines E-GMD, public domain, and Jamstix brain datasets into multitask training file
"""
import json
from pathlib import Path

def combine_datasets():
    """Combine all training datasets"""
    
    datasets = {
        "E-GMD Patterns": Path("llm_training_project/training_datasets/egmd_pattern_train.jsonl"),
        "E-GMD Phrase Select": Path("llm_training_project/training_datasets/egmd_phrase_select_train.jsonl"),
        "Rudiment Fragments": Path("llm_training_project/training_datasets/rudiment_fragments_train.jsonl"),
        "Public Domain": Path("llm_training_project/training_datasets/public_domain_train.jsonl"),
        "Jamstix Brain": Path("llm_training_project/training_datasets/jamstix_brain_train.jsonl"),
        "Signature Grooves": Path("llm_training_project/training_datasets/signature_groove_train.jsonl"),
    }
    
    output_file = Path("llm_training_project/training_datasets/multitask_full.jsonl")
    
    print("=" * 70)
    print("COMBINING TRAINING DATASETS")
    print("=" * 70)
    
    total_examples = 0
    by_source = {}
    by_task = {}
    
    with output_file.open('w', encoding='utf-8') as f_out:
        for name, dataset_path in datasets.items():
            if not dataset_path.exists():
                print(f"\n⚠️  {name}: Not found, skipping")
                continue
            
            count = 0
            with dataset_path.open('r', encoding='utf-8') as f_in:
                for line in f_in:
                    example = json.loads(line)
                    f_out.write(line)
                    count += 1
                    total_examples += 1
                    
                    # Track statistics
                    source = example.get('meta', {}).get('source', 'unknown')
                    task = example.get('task', 'unknown')
                    by_source[source] = by_source.get(source, 0) + 1
                    by_task[task] = by_task.get(task, 0) + 1
            
            print(f"\n✅ {name}: {count:,} examples")
    
    print(f"\n" + "=" * 70)
    print(f"COMBINED TRAINING DATASET")
    print("=" * 70)
    print(f"\n📊 Total Examples: {total_examples:,}")
    print(f"   Output: {output_file}")
    print(f"   Size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")
    
    print(f"\n📊 By Source:")
    for source, count in sorted(by_source.items(), key=lambda x: x[1], reverse=True):
        print(f"   {source}: {count:,} ({count/total_examples*100:.1f}%)")
    
    print(f"\n📊 By Task Type:")
    for task, count in sorted(by_task.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {task}: {count:,} ({count/total_examples*100:.1f}%)")
    
    print(f"\n" + "=" * 70)
    print("✅ READY FOR LLM TRAINING")
    print("=" * 70)
    
    print(f"\n🚀 Next Steps:")
    print(f"   1. Use multitask_full.jsonl for training")
    print(f"   2. Fine-tune GPT-4.1 or LLaMA/Mixtral")
    print(f"   3. Trained LLM will understand:")
    print(f"      - Pattern analysis ({by_source.get('egmd_dataset', 0):,} examples)")
    print(f"      - Drum concepts ({by_source.get('public_domain', 0)} + {by_source.get('jamstix_brain', 0)} examples)")
    print(f"      - Brain logic and reasoning")
    print(f"      - Limb constraints")
    print(f"      - Drummer personalities")

if __name__ == "__main__":
    combine_datasets()
