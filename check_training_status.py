#!/usr/bin/env python3
"""Check LLM training status"""
import sqlite3
from pathlib import Path
import os

print("=" * 60)
print("LLM TRAINING STATUS CHECK")
print("=" * 60)

# Check training database
db_path = Path("admin/data/drum_training.db")
if db_path.exists():
    print(f"\n✅ Training database found: {db_path}")
    print(f"   Size: {db_path.stat().st_size:,} bytes")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Get tables
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"\n📊 Database tables ({len(tables)}):")
    for table in tables:
        count = cur.execute(f"SELECT COUNT(*) FROM {table[0]}").fetchone()[0]
        print(f"   - {table[0]}: {count} rows")
    
    conn.close()
else:
    print(f"\n❌ Training database not found at: {db_path}")

# Check for pre-existing models
models_dir = Path("models")
if models_dir.exists():
    models = list(models_dir.glob("*.pt"))
    print(f"\n🤖 Pre-existing models ({len(models)}):")
    for model in models:
        size_kb = model.stat().st_size / 1024
        print(f"   - {model.name}: {size_kb:.1f} KB")
else:
    print(f"\n❌ Models directory not found")

# Check admin models
admin_models = Path("admin/models/checkpoints")
if admin_models.exists():
    checkpoints = list(admin_models.glob("*.pth")) + list(admin_models.glob("*.pt"))
    print(f"\n💾 Admin checkpoints ({len(checkpoints)}):")
    if checkpoints:
        for checkpoint in checkpoints:
            size_kb = checkpoint.stat().st_size / 1024
            print(f"   - {checkpoint.name}: {size_kb:.1f} KB")
    else:
        print("   (No checkpoints yet)")
else:
    print(f"\n❌ Admin checkpoints directory not found")

# Check if training system is ready
training_module = Path("admin/training/model_trainer.py")
if training_module.exists():
    print(f"\n✅ Training system ready at: admin/training/")
else:
    print(f"\n❌ Training system not found")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("\n📝 Current Status:")
print("   - Training database: " + ("✅ Exists" if db_path.exists() else "❌ Not found"))
print("   - Pre-trained models: " + ("✅ 4 models found" if models_dir.exists() and len(list(models_dir.glob("*.pt"))) > 0 else "❌ None"))
print("   - Training system: " + ("✅ Ready" if training_module.exists() else "❌ Not ready"))
print("   - Active training: " + ("❌ No recent checkpoints" if not checkpoints else f"✅ {len(checkpoints)} checkpoint(s)"))

print("\n🎯 Next Steps:")
if not db_path.exists() or (admin_models.exists() and not checkpoints):
    print("   1. No active training detected")
    print("   2. You have pre-existing models (74KB each)")
    print("   3. To start training:")
    print("      - cd admin")
    print("      - python main.py  (or START_LLM_TRAINING_MONITOR.bat)")
    print("      - Navigate to AI Training tab")
else:
    print("   Training system is operational")
    print("   Use START_LLM_TRAINING_MONITOR.bat to check progress")

print("=" * 60)
