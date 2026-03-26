"""
Model Deployment Module
Deploys trained models to production system
"""

import json
import shutil
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ModelDeployer:
    """Deploy trained models to production"""
    
    def __init__(self, production_models_dir: Path = None):
        self.production_models_dir = production_models_dir or Path("models/production")
        self.production_models_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.production_models_dir / "model_registry.json"
        self._load_registry()
        logger.info(f"Model Deployer initialized: {self.production_models_dir}")
    
    def _load_registry(self):
        """Load model registry"""
        if self.registry_file.exists():
            with open(self.registry_file) as f:
                self.registry = json.load(f)
        else:
            self.registry = {'models': []}
    
    def _save_registry(self):
        """Save model registry"""
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)
    
    def deploy_model(self,
                    model_path: Path,
                    model_name: str,
                    version: str,
                    metadata: Dict) -> bool:
        """
        Deploy model to production
        
        Args:
            model_path: Path to trained model file
            model_name: Name for the model (e.g., 'humanizer_v1')
            version: Version string (e.g., '1.0.0')
            metadata: Additional metadata (training metrics, etc.)
        
        Returns:
            True if deployment successful
        """
        try:
            # Create deployment directory
            deploy_dir = self.production_models_dir / f"{model_name}_{version}"
            deploy_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy model file
            deployed_model_path = deploy_dir / model_path.name
            shutil.copy2(model_path, deployed_model_path)
            
            # Create model info file
            model_info = {
                'name': model_name,
                'version': version,
                'model_file': model_path.name,
                'deployed_at': datetime.now().isoformat(),
                'metadata': metadata
            }
            
            info_file = deploy_dir / 'model_info.json'
            with open(info_file, 'w') as f:
                json.dump(model_info, f, indent=2)
            
            # Register in registry
            self.registry['models'].append({
                'name': model_name,
                'version': version,
                'path': str(deployed_model_path),
                'deployed_at': model_info['deployed_at'],
                'active': True
            })
            self._save_registry()
            
            logger.info(f"Model deployed: {model_name} v{version}")
            return True
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return False
    
    def set_active_model(self, model_name: str, version: str) -> bool:
        """Set which model version is active"""
        found = False
        for model in self.registry['models']:
            if model['name'] == model_name:
                if model['version'] == version:
                    model['active'] = True
                    found = True
                    logger.info(f"Activated: {model_name} v{version}")
                else:
                    model['active'] = False
        
        if found:
            self._save_registry()
        return found
    
    def get_active_model(self, model_name: str) -> Optional[Dict]:
        """Get active model info"""
        for model in self.registry['models']:
            if model['name'] == model_name and model.get('active', False):
                return model
        return None
    
    def list_models(self) -> list:
        """List all deployed models"""
        return self.registry['models']


def test_deployer():
    """Test the deployer"""
    print("🚀 Testing Model Deployer")
    print("=" * 60)
    
    deployer = ModelDeployer(Path("admin/models/production"))
    
    print(f"\n📁 Production directory: {deployer.production_models_dir}")
    print(f"📋 Registry file: {deployer.registry_file}")
    
    # List models
    models = deployer.list_models()
    print(f"\n📦 Deployed models: {len(models)}")
    
    for model in models:
        active = "✅" if model.get('active') else "  "
        print(f"   {active} {model['name']} v{model['version']}")
    
    print("\n✅ Deployer test complete")


if __name__ == "__main__":
    test_deployer()
