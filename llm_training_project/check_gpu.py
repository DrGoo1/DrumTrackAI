#!/usr/bin/env python3
"""
Check GPU Compatibility for LLM Training
=========================================
"""
import sys
import subprocess

print("=" * 70)
print("GPU COMPATIBILITY CHECK FOR LLM TRAINING")
print("=" * 70)
print()

# Check if torch is installed
try:
    import torch
    torch_installed = True
except ImportError:
    torch_installed = False
    print("⚠️  PyTorch not installed")
    print("   Installing torch to check GPU...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "torch", "--index-url", "https://download.pytorch.org/whl/cu121"])
        import torch
        torch_installed = True
    except:
        print("   ❌ Could not install PyTorch")
        torch_installed = False

if not torch_installed:
    print()
    print("=" * 70)
    print("Cannot check GPU without PyTorch")
    print("=" * 70)
    sys.exit(1)

# Check CUDA availability
cuda_available = torch.cuda.is_available()

print("🔍 GPU Detection:")
print("-" * 70)

if not cuda_available:
    print("❌ No CUDA-compatible GPU detected")
    print()
    print("💡 Your Options:")
    print("   1. Use Google Colab (FREE Tesla T4 GPU)")
    print("   2. Use Kaggle (FREE P100 GPU)")
    print("   3. Use Hugging Face AutoTrain")
    print()
    print("   See: FREE_TRAINING_OPTIONS.md")
    print()
    print("=" * 70)
    print("RECOMMENDATION: Use Google Colab (FREE)")
    print("=" * 70)
    sys.exit(0)

# GPU is available - get details
print("✅ CUDA GPU Detected!")
print()

num_gpus = torch.cuda.device_count()
print(f"📊 GPU Information:")
print(f"   Number of GPUs: {num_gpus}")
print()

for i in range(num_gpus):
    props = torch.cuda.get_device_properties(i)
    name = props.name
    total_memory_gb = props.total_memory / (1024**3)
    compute_capability = f"{props.major}.{props.minor}"
    
    print(f"   GPU {i}: {name}")
    print(f"   VRAM: {total_memory_gb:.1f} GB")
    print(f"   Compute Capability: {compute_capability}")
    print()
    
    # Determine suitability
    print("🎯 Training Capability:")
    print("-" * 70)
    
    if total_memory_gb >= 24:
        print("✅ EXCELLENT - Can train large models!")
        print()
        print("   Recommended models:")
        print("   - LLaMA-3-8B (full precision)")
        print("   - Mistral-7B (full precision)")
        print("   - Phi-3-mini (full precision)")
        print()
        print("   Training time: 1-2 hours")
        print("   Batch size: 8-16")
        print()
        can_train = True
        
    elif total_memory_gb >= 16:
        print("✅ GOOD - Can train with 4-bit quantization!")
        print()
        print("   Recommended models:")
        print("   - Phi-3-mini-4k (4-bit) ⭐ BEST FIT")
        print("   - Mistral-7B (4-bit)")
        print("   - TinyLlama-1.1B (full precision)")
        print()
        print("   Training time: 2-3 hours")
        print("   Batch size: 4-8")
        print()
        can_train = True
        
    elif total_memory_gb >= 12:
        print("⚠️  MARGINAL - Can train small models only")
        print()
        print("   Recommended models:")
        print("   - TinyLlama-1.1B (4-bit)")
        print("   - Phi-2 (4-bit)")
        print()
        print("   Training time: 2-4 hours")
        print("   Batch size: 2-4")
        print()
        print("   💡 Better to use Google Colab for larger models")
        can_train = True
        
    elif total_memory_gb >= 8:
        print("❌ INSUFFICIENT - Too small for effective training")
        print()
        print("   Your GPU can't train effectively.")
        print()
        print("   💡 Recommendation: Use Google Colab instead")
        print("      - FREE Tesla T4 (16GB)")
        print("      - Better than your local GPU")
        print("      - See: FREE_TRAINING_OPTIONS.md")
        print()
        can_train = False
        
    else:
        print("❌ NOT SUITABLE - VRAM too low")
        print()
        print("   Minimum 8GB needed for basic training")
        print()
        print("   💡 Use Google Colab (FREE 16GB T4 GPU)")
        print()
        can_train = False

print()
print("=" * 70)
print("RECOMMENDATION:")
print("=" * 70)

if num_gpus > 0:
    main_gpu_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    
    if main_gpu_vram >= 16:
        print()
        print("✅ Your GPU is suitable for LOCAL training!")
        print()
        print("🚀 Next Steps:")
        print("   1. Install dependencies:")
        print("      pip install transformers datasets peft accelerate bitsandbytes trl")
        print()
        print("   2. Run training:")
        print("      python llm_training_project/train_lora.py \\")
        print("        --model_name microsoft/Phi-3-mini-4k-instruct \\")
        print("        --data_path training_datasets/multitask_full.jsonl \\")
        print("        --output_dir models/drumtrackai-llm")
        print()
        print("   Expected time: 2-3 hours")
        print("   Expected cost: $0.00 (just electricity)")
        print()
        
    elif main_gpu_vram >= 12:
        print()
        print("⚠️  Your GPU can train, but Google Colab is better")
        print()
        print("   Local training:")
        print("   - Limited to small models")
        print("   - Slower training")
        print("   - 3-4 hours")
        print()
        print("   Google Colab:")
        print("   - FREE 16GB T4 GPU")
        print("   - Better models")
        print("   - 2-3 hours")
        print()
        print("   💡 RECOMMENDED: Use Google Colab")
        print("      See: FREE_TRAINING_OPTIONS.md")
        print()
        
    else:
        print()
        print("❌ Use Google Colab instead (FREE & Better)")
        print()
        print("   Your GPU: {:.1f} GB VRAM".format(main_gpu_vram))
        print("   Colab GPU: 16 GB VRAM (FREE)")
        print()
        print("   📝 See: FREE_TRAINING_OPTIONS.md")
        print()

print("=" * 70)
