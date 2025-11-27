"""
Real-time Training Progress Monitor
Displays live status of data preparation and model training
"""

import os
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

class TrainingMonitor:
    def __init__(self):
        self.data_dir = "E:/DrumTracKAI_Master/03_Training_Data/preprocessed"
        self.models_dir = "E:/DrumTracKAI_Master/04_Models/current"
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def check_data_prep_status(self):
        """Check if data preparation files exist"""
        files_to_check = [
            f"{self.data_dir}/train_features.npy",
            f"{self.data_dir}/val_features.npy",
            f"{self.data_dir}/test_features.npy"
        ]
        
        existing = [f for f in files_to_check if os.path.exists(f)]
        
        if len(existing) == 3:
            # Get file sizes
            train_size = os.path.getsize(f"{self.data_dir}/train_features.npy") / (1024**3)  # GB
            val_size = os.path.getsize(f"{self.data_dir}/val_features.npy") / (1024**3)
            test_size = os.path.getsize(f"{self.data_dir}/test_features.npy") / (1024**3)
            
            return {
                'status': 'complete',
                'train_size_gb': train_size,
                'val_size_gb': val_size,
                'test_size_gb': test_size,
                'total_size_gb': train_size + val_size + test_size
            }
        else:
            return {
                'status': 'in_progress',
                'files_ready': len(existing),
                'files_total': 3
            }
    
    def check_training_status(self):
        """Check model training status"""
        history_file = f"{self.models_dir}/training_history.json"
        
        if not os.path.exists(history_file):
            return {
                'status': 'not_started',
                'message': 'Waiting for data preparation to complete'
            }
        
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            if not history['epochs']:
                return {
                    'status': 'starting',
                    'message': 'Training initializing...'
                }
            
            current_epoch = history['epochs'][-1]
            train_loss = history['train_loss'][-1]
            val_loss = history['val_loss'][-1]
            lr = history['learning_rates'][-1]
            
            # Find best epoch
            best_val_loss = min(history['val_loss'])
            best_epoch = history['val_loss'].index(best_val_loss) + 1
            
            return {
                'status': 'training',
                'current_epoch': current_epoch,
                'total_epochs': 100,  # Default config
                'train_loss': train_loss,
                'val_loss': val_loss,
                'best_val_loss': best_val_loss,
                'best_epoch': best_epoch,
                'learning_rate': lr,
                'progress_pct': (current_epoch / 100) * 100
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def display_dashboard(self):
        """Display monitoring dashboard"""
        self.clear_screen()
        
        print("="*80)
        print("🤖 DRUMTRACKAI AI TRAINING MONITOR".center(80))
        print("="*80)
        print(f"⏰ Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Data Preparation Status
        print("\n📊 DATA PREPARATION STATUS")
        print("-"*80)
        data_status = self.check_data_prep_status()
        
        if data_status['status'] == 'complete':
            print("✅ Status: COMPLETE")
            print(f"   Train set:  {data_status['train_size_gb']:.2f} GB")
            print(f"   Val set:    {data_status['val_size_gb']:.2f} GB")
            print(f"   Test set:   {data_status['test_size_gb']:.2f} GB")
            print(f"   Total size: {data_status['total_size_gb']:.2f} GB")
        else:
            print("🔄 Status: IN PROGRESS")
            print(f"   Files ready: {data_status['files_ready']}/3")
            print("   Processing 91,074 MIDI patterns...")
            print("   This may take 4-5 hours")
        
        # Model Training Status
        print("\n🧠 MODEL TRAINING STATUS")
        print("-"*80)
        train_status = self.check_training_status()
        
        if train_status['status'] == 'not_started':
            print("⏳ Status: NOT STARTED")
            print(f"   {train_status['message']}")
        
        elif train_status['status'] == 'starting':
            print("🚀 Status: INITIALIZING")
            print(f"   {train_status['message']}")
        
        elif train_status['status'] == 'training':
            print("⚡ Status: TRAINING")
            print(f"   Epoch: {train_status['current_epoch']}/{train_status['total_epochs']} "
                  f"({train_status['progress_pct']:.1f}%)")
            
            # Progress bar
            bar_length = 50
            filled = int(bar_length * train_status['progress_pct'] / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f"   [{bar}]")
            
            print(f"\n   Train Loss:     {train_status['train_loss']:.4f}")
            print(f"   Val Loss:       {train_status['val_loss']:.4f}")
            print(f"   Best Val Loss:  {train_status['best_val_loss']:.4f} (epoch {train_status['best_epoch']})")
            print(f"   Learning Rate:  {train_status['learning_rate']:.6f}")
            
            # Estimate time remaining
            if train_status['current_epoch'] > 0:
                # Assume ~1-2 min per epoch on CPU, ~10-20s on GPU
                epochs_remaining = train_status['total_epochs'] - train_status['current_epoch']
                # Conservative estimate: 2 min per epoch
                time_remaining = epochs_remaining * 2  # minutes
                hours = time_remaining // 60
                mins = time_remaining % 60
                print(f"\n   Est. Time Remaining: ~{hours}h {mins}m")
        
        elif train_status['status'] == 'error':
            print("❌ Status: ERROR")
            print(f"   {train_status['message']}")
        
        # Model Checkpoints
        print("\n💾 MODEL CHECKPOINTS")
        print("-"*80)
        
        if os.path.exists(self.models_dir):
            checkpoints = list(Path(self.models_dir).glob("*.pth"))
            
            if checkpoints:
                print(f"   Found {len(checkpoints)} checkpoint(s):")
                for ckpt in sorted(checkpoints, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
                    size_mb = ckpt.stat().st_size / (1024**2)
                    mtime = datetime.fromtimestamp(ckpt.stat().st_mtime)
                    print(f"   • {ckpt.name:40s} {size_mb:6.1f} MB  {mtime.strftime('%H:%M:%S')}")
            else:
                print("   No checkpoints yet")
        else:
            print("   Models directory not created yet")
        
        # Instructions
        print("\n" + "="*80)
        print("💡 MONITORING TIPS")
        print("-"*80)
        print("   • This dashboard auto-refreshes every 30 seconds")
        print("   • Press Ctrl+C to exit")
        print("   • Data prep completes first, then training begins automatically")
        print("   • Training takes 2-3 days on CPU, 6-12 hours on GPU")
        print("   • Best model is saved automatically based on validation loss")
        print("="*80)
    
    def monitor_loop(self, refresh_interval=30):
        """Main monitoring loop"""
        print("🚀 Starting Training Monitor...")
        print(f"   Refresh interval: {refresh_interval} seconds")
        print("   Press Ctrl+C to exit")
        time.sleep(2)
        
        try:
            while True:
                self.display_dashboard()
                time.sleep(refresh_interval)
        
        except KeyboardInterrupt:
            print("\n\n👋 Monitor stopped by user")
            sys.exit(0)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor AI training progress')
    parser.add_argument('--interval', type=int, default=30, 
                       help='Refresh interval in seconds (default: 30)')
    parser.add_argument('--once', action='store_true',
                       help='Display once and exit (no loop)')
    
    args = parser.parse_args()
    
    monitor = TrainingMonitor()
    
    if args.once:
        monitor.display_dashboard()
    else:
        monitor.monitor_loop(refresh_interval=args.interval)
