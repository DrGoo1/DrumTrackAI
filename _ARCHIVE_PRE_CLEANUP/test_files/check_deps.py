"""Quick dependency check"""
import sys

print("=" * 60)
print("Checking Training System Dependencies")
print("=" * 60)

# Check PyTorch
try:
    import torch
    print(f"✅ PyTorch: {torch.__version__}")
    if torch.cuda.is_available():
        print(f"   🎮 GPU Available: {torch.cuda.get_device_name(0)}")
    else:
        print(f"   💻 Using CPU (GPU not available)")
except ImportError:
    print("❌ PyTorch: NOT INSTALLED")
    print("   Install: pip install torch torchvision torchaudio")

# Check scikit-learn
try:
    import sklearn
    print(f"✅ scikit-learn: {sklearn.__version__}")
except ImportError:
    print("❌ scikit-learn: NOT INSTALLED")
    print("   Install: pip install scikit-learn")

# Check librosa
try:
    import librosa
    print(f"✅ librosa: {librosa.__version__}")
except ImportError:
    print("❌ librosa: NOT INSTALLED")
    print("   Install: pip install librosa soundfile")

# Check soundfile
try:
    import soundfile
    print(f"✅ soundfile: {soundfile.__version__}")
except ImportError:
    print("❌ soundfile: NOT INSTALLED")
    print("   Install: pip install soundfile")

# Check PySide6 (should be installed)
try:
    import PySide6
    print(f"✅ PySide6: Available")
except ImportError:
    print("❌ PySide6: NOT INSTALLED")

print("\n" + "=" * 60)

# Check if ready to train
try:
    import torch
    import sklearn
    print("\n✅ READY TO START TRAINING!")
    print("\nNext steps:")
    print("1. Run: python admin/main.py")
    print("2. Go to 'AI Training' tab")
    print("3. Start extracting training data")
except ImportError:
    print("\n⚠️ INSTALL MISSING DEPENDENCIES")
    print("\nRun: SETUP_TRAINING_SYSTEM.bat")
    print("Or manually: pip install torch scikit-learn librosa soundfile")

sys.exit(0)
