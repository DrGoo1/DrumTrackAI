#!/usr/bin/env python3
"""
Automated AI Backend Integration Script
Adds AI endpoints to dcsm_backend.py
"""

import re
from pathlib import Path

def integrate_ai_backend():
    """Integrate AI endpoints into existing backend"""
    backend_file = Path("dcsm_backend.py")
    
    if not backend_file.exists():
        print("❌ dcsm_backend.py not found")
        return False
    
    print("📝 Reading dcsm_backend.py...")
    content = backend_file.read_text()
    modified = False
    
    # 1. Add import at top (after drummer_mapping_service import)
    if "from backend_ai_endpoints" not in content:
        print("  Adding AI imports...")
        content = content.replace(
            "from drummer_mapping_service import get_drummer_service\n",
            "from drummer_mapping_service import get_drummer_service\n"
            "from backend_ai_endpoints import initialize_ai_generator, setup_ai_routes\n"
        )
        modified = True
        print("  ✓ Added AI imports")
    else:
        print("  ✓ AI imports already present")
    
    # 2. Add initialization in on_startup
    if "initialize_ai_generator" not in content:
        print("  Adding AI initialization...")
        # Find the on_startup function and add initialization
        content = re.sub(
            r'(async def on_startup\(_\):\s*\n\s*LOG\.info)',
            r'async def on_startup(_):\n        initialize_ai_generator()\n        LOG.info',
            content
        )
        modified = True
        print("  ✓ Added AI initialization")
    else:
        print("  ✓ AI initialization already present")
    
    # 3. Add routes in make_app (before CORS setup)
    if "setup_ai_routes" not in content:
        print("  Adding AI routes...")
        content = content.replace(
            "    ])\n\n    # CORS for dev",
            "    ])\n\n    # Setup AI routes\n    setup_ai_routes(app)\n\n    # CORS for dev"
        )
        modified = True
        print("  ✓ Added AI routes setup")
    else:
        print("  ✓ AI routes already present")
    
    if modified:
        # Backup original
        backup_file = backend_file.with_suffix('.py.backup')
        print(f"\n💾 Creating backup: {backup_file}")
        backup_file.write_text(backend_file.read_text())
        
        # Save modified version
        print(f"💾 Writing updated {backend_file}")
        backend_file.write_text(content)
        print("\n✅ Integration complete!")
        print("\n📋 Changes made:")
        print("  1. Added AI imports")
        print("  2. Added AI initialization on startup")
        print("  3. Added AI routes to app")
        print(f"\n💡 Backup saved to: {backup_file}")
    else:
        print("\n✅ AI already integrated - no changes needed")
    
    return True

if __name__ == "__main__":
    print("🚀 DrumTracKAI AI Backend Integration")
    print("="*60)
    integrate_ai_backend()
    print("\n🎯 Next steps:")
    print("  1. Test integrated backend: python dcsm_backend.py")
    print("  2. Test AI endpoint: curl http://localhost:8000/api/ai/status")
    print("  3. Generate pattern: curl -X POST http://localhost:8000/api/ai/generate \\")
    print("       -H 'Content-Type: application/json' \\")
    print("       -d '{\"tempo\":120,\"style\":\"rock\"}'")
