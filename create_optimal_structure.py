"""
Create Optimal Folder Structure on E Drive
Creates organized folder hierarchy
"""

import os
from pathlib import Path

def create_folder_structure():
    """Create the optimal folder structure"""
    
    base = "E:/DrumTracKAI_Master"
    
    structure = {
        "01_MIDI_Patterns": {
            "Datasets": {
                "E-GMD": ["rock", "jazz", "funk", "metal", "pop", "latin", "edm"],
                "SoundTracksLoops": ["verse_patterns", "chorus_patterns", "fills", "loops"],
                "Rudiments": ["single_stroke", "double_stroke", "paradiddles", "flams", "drags", "rolls"]
            },
            "YouTube_Extractions": {
                "by_drummer": ["Jeff_Porcaro", "Steve_Gadd", "Tony_Williams", "Dennis_Chambers"],
                "by_song": []
            },
            "User_Generated": []
        },
        
        "02_Audio_Samples": {
            "Acoustic_Drums": {
                "Kick": ["Ludwig_1970s", "DW_5000", "Pearl_Masters", "Gretsch_USA"],
                "Snare": ["Ludwig_BlackBeauty", "Pearl_Sensitone", "DW_Collectors"],
                "Toms": ["Rack_Toms", "Floor_Toms"],
                "Hi-Hat": ["Zildjian_A", "Sabian_HHX", "Paiste_2002"],
                "Ride": ["Zildjian_K", "Paiste_2002", "Sabian_HH"],
                "Crash": ["Zildjian_A_Custom", "Meinl_Byzance", "Sabian_AAX"]
            },
            "Electronic_Drums": {
                "808": [],
                "909": [],
                "LinnDrum": [],
                "Simmons": [],
                "Modern_Electronic": []
            },
            "Sample_Libraries": {
                "Superior_Drummer_3": ["Rock_Foundry", "Metal_Foundry", "Jazz", "Pop"],
                "Steven_Slate_Drums": [],
                "Addictive_Drums": [],
                "BFD3": [],
                "EZDrummer": []
            },
            "Processed": ["compressed", "reverb", "distorted", "layered"]
        },
        
        "03_Training_Data": {
            "preprocessed": [],
            "augmented": [],
            "validation": [],
            "test": []
        },
        
        "04_Models": {
            "current": [],
            "experiments": [],
            "archived": []
        },
        
        "05_Analysis_Results": {
            "tempo_maps": [],
            "onset_detections": [],
            "feature_extractions": []
        },
        
        "06_Database": {
            "backups": [],
            "exports": []
        }
    }
    
    def create_recursive(base_path, struct):
        """Recursively create folder structure"""
        for name, contents in struct.items():
            folder_path = os.path.join(base_path, name)
            
            # Create folder
            os.makedirs(folder_path, exist_ok=True)
            
            # Create README
            readme_path = os.path.join(folder_path, "README.md")
            if not os.path.exists(readme_path):
                with open(readme_path, 'w') as f:
                    f.write(f"# {name}\n\n")
                    f.write(f"Part of DrumTracKAI Master Database\n\n")
                    f.write(f"Created: {Path(folder_path).stat().st_ctime}\n")
            
            # If contents is a dict, recurse
            if isinstance(contents, dict):
                create_recursive(folder_path, contents)
            # If contents is a list, create those folders
            elif isinstance(contents, list):
                for subfolder in contents:
                    sub_path = os.path.join(folder_path, subfolder)
                    os.makedirs(sub_path, exist_ok=True)
    
    print("🏗️  Creating Optimal Folder Structure...")
    print(f"Base: {base}")
    print("="*60)
    
    # Create main structure
    os.makedirs(base, exist_ok=True)
    
    # Create main README
    main_readme = os.path.join(base, "README.md")
    with open(main_readme, 'w') as f:
        f.write("# DrumTracKAI Master Database\n\n")
        f.write("Organized drum pattern and sample database for AI training\n\n")
        f.write("## Structure:\n\n")
        f.write("- **01_MIDI_Patterns**: All MIDI drum patterns for training\n")
        f.write("- **02_Audio_Samples**: Audio samples for playback\n")
        f.write("- **03_Training_Data**: Preprocessed data for AI\n")
        f.write("- **04_Models**: Trained AI models\n")
        f.write("- **05_Analysis_Results**: Analysis outputs\n")
        f.write("- **06_Database**: SQLite databases\n")
    
    # Create full structure
    create_recursive(base, structure)
    
    # Create Archives folder
    archives = "E:/Archives"
    os.makedirs(archives, exist_ok=True)
    os.makedirs(os.path.join(archives, "Original_Folders"), exist_ok=True)
    os.makedirs(os.path.join(archives, "Migration_Logs"), exist_ok=True)
    
    print("\n✓ Folder structure created successfully!")
    print(f"\nCreated:")
    print(f"  {base}/")
    print(f"  {archives}/")
    
    # Count total folders
    total_folders = sum([len(dirnames) for _, dirnames, _ in os.walk(base)])
    print(f"\nTotal folders: {total_folders}")
    
    print("\n📋 Next Step:")
    print("  Run: python migrate_files.py --dry-run")

if __name__ == "__main__":
    create_folder_structure()
