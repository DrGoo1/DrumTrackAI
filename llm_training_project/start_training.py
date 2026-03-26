#!/usr/bin/env python3
"""
Start OpenAI Fine-Tuning for DrumTracKAI Drummer LLM
====================================================
"""
import os
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not found")
    print("Install with: pip install openai")
    sys.exit(1)

def main():
    print("=" * 70)
    print("DrumTracKAI LLM Training - OpenAI Fine-Tuning")
    print("=" * 70)
    print()
    
    # Check API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not set")
        print()
        print("Set your API key:")
        print('  $env:OPENAI_API_KEY="sk-your-key-here"  # PowerShell')
        print('  set OPENAI_API_KEY=sk-your-key-here      # CMD')
        print()
        sys.exit(1)
    
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Check training file
    training_file = Path("training_datasets/multitask_full.jsonl")
    if not training_file.exists():
        print(f"❌ ERROR: Training file not found")
        print(f"   Expected: {training_file}")
        sys.exit(1)
    
    size_mb = training_file.stat().st_size / 1024 / 1024
    with training_file.open('r') as f:
        num_examples = sum(1 for _ in f)
    
    print(f"✅ Training file: {training_file}")
    print(f"   Examples: {num_examples:,}")
    print(f"   Size: {size_mb:.1f} MB")
    print()
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Upload training file
    print("📤 Uploading training file...")
    try:
        with training_file.open("rb") as f:
            upload_response = client.files.create(
                file=f,
                purpose="fine-tune"
            )
        
        file_id = upload_response.id
        print(f"✅ File uploaded: {file_id}")
        print()
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        sys.exit(1)
    
    # Create fine-tuning job
    print("🚀 Creating fine-tuning job...")
    print("   Model: gpt-4o-mini-2024-07-18")  # Using gpt-4o-mini for cost efficiency
    print("   Suffix: drumtrackai-drummer-v1")
    print()
    
    try:
        job = client.fine_tuning.jobs.create(
            training_file=file_id,
            model="gpt-4o-mini-2024-07-18",  # More affordable than gpt-4-turbo
            suffix="drumtrackai-drummer-v1",
            hyperparameters={
                "n_epochs": 3
            }
        )
        
        job_id = job.id
        print("=" * 70)
        print("✅ FINE-TUNING JOB CREATED!")
        print("=" * 70)
        print()
        print(f"Job ID: {job_id}")
        print(f"Status: {job.status}")
        print()
        print("📊 Training Details:")
        print(f"   - Training file: {file_id}")
        print(f"   - Examples: {num_examples:,}")
        print(f"   - Epochs: 3")
        print(f"   - Expected time: 30-60 minutes")
        print()
        print("🔍 Monitor progress:")
        print(f"   python -c \"from openai import OpenAI; c=OpenAI(); print(c.fine_tuning.jobs.retrieve('{job_id}'))\"")
        print()
        print("   Or visit: https://platform.openai.com/finetune")
        print()
        print("💰 Estimated cost: ~$2-5 for 91K examples")
        print()
        
        # Save job info
        job_info_file = Path("training_job_info.txt")
        with job_info_file.open('w') as f:
            f.write(f"Job ID: {job_id}\n")
            f.write(f"File ID: {file_id}\n")
            f.write(f"Status: {job.status}\n")
            f.write(f"Created: {job.created_at}\n")
            f.write(f"Model: gpt-4o-mini-2024-07-18\n")
            f.write(f"Suffix: drumtrackai-drummer-v1\n")
        
        print(f"📁 Job info saved to: {job_info_file}")
        print()
        print("=" * 70)
        print("Training started! Check status periodically.")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Failed to create fine-tuning job: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
