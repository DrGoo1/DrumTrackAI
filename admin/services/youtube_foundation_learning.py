"""
YouTube Foundation Learning Service
===================================
Track A: General drumming expertise from YouTube.

This module searches for TECHNIQUES and CONCEPTS rather than specific drummers.
Builds foundational drumming knowledge before specialized drummer profiles.

Autonomous Search Capabilities:
- Generates search queries for techniques automatically
- Searches for beginner → intermediate → advanced content
- Filters for instructional/educational content
- Avoids drummer-specific content (that's Track B)
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)

# Import YouTube services
try:
    # Try relative imports first (when used as package)
    from .youtube_llm_learning_service import YouTubeLLMLearningPipeline
    from ..training.youtube_downloader import YouTubeDrumDownloader
    SERVICES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"YouTube services not available: {e}")
    # Try absolute imports (when run as script)
    try:
        import sys
        from pathlib import Path
        admin_dir = Path(__file__).parent.parent
        if str(admin_dir) not in sys.path:
            sys.path.insert(0, str(admin_dir))
        
        from services.youtube_llm_learning_service import YouTubeLLMLearningPipeline
        from training.youtube_downloader import YouTubeDrumDownloader
        SERVICES_AVAILABLE = True
        logger.info("YouTube services loaded via absolute imports")
    except ImportError as e2:
        logger.error(f"All import methods failed: {e2}")
        SERVICES_AVAILABLE = False
        YouTubeDrumDownloader = None
        YouTubeLLMLearningPipeline = None


class YouTubeFoundationLearning:
    """
    Autonomous YouTube learning for Track A (General Expertise).
    
    Features:
    - Automatic search query generation
    - Progressive difficulty (beginner → advanced)
    - Technique-focused (not drummer-focused)
    - Educational content prioritization
    """
    
    # ================================================================
    # FOUNDATION TECHNIQUE CATEGORIES
    # ================================================================
    
    TECHNIQUE_CATEGORIES = {
        'basic_beats': {
            'level': 'beginner',
            'priority': 1,
            'techniques': [
                'basic rock beat',
                'four on the floor',
                'simple jazz ride pattern',
                'basic funk groove',
                'shuffle beat',
                'half time beat',
                'double time beat'
            ]
        },
        'rudiments': {
            'level': 'intermediate',
            'priority': 2,
            'techniques': [
                'single stroke roll',
                'double stroke roll',
                'paradiddle',
                'flam',
                'drag',
                'ratamacue',
                'five stroke roll',
                'seven stroke roll'
            ]
        },
        'ghost_notes': {
            'level': 'intermediate',
            'priority': 2,
            'techniques': [
                'snare ghost notes',
                'hi-hat ghost notes',
                'ghost note groove',
                'ghost note placement',
                'ghost note dynamics'
            ]
        },
        'fills': {
            'level': 'intermediate',
            'priority': 2,
            'techniques': [
                'basic tom fill',
                'snare roll fill',
                'cymbal crash fill',
                'four bar fill',
                'eight bar fill',
                'drum fill transitions'
            ]
        },
        'advanced_timing': {
            'level': 'advanced',
            'priority': 3,
            'techniques': [
                'swing feel',
                'shuffle timing',
                'polyrhythm 3 over 4',
                'polyrhythm 5 over 4',
                'odd time signatures',
                'metric modulation',
                'displaced beats'
            ]
        },
        'dynamics': {
            'level': 'intermediate',
            'priority': 2,
            'techniques': [
                'dynamic control',
                'crescendo technique',
                'accent patterns',
                'velocity variation',
                'soft to loud dynamics'
            ]
        },
        'independence': {
            'level': 'advanced',
            'priority': 3,
            'techniques': [
                'four limb independence',
                'ostinato patterns',
                'polyrhythmic independence',
                'jazz independence',
                'linear drumming'
            ]
        },
        'styles': {
            'level': 'intermediate',
            'priority': 2,
            'techniques': [
                'rock drumming basics',
                'jazz drumming basics',
                'funk drumming basics',
                'latin drumming basics',
                'metal drumming basics',
                'reggae drumming basics',
                'electronic drumming basics'
            ]
        }
    }
    
    # ================================================================
    # SEARCH QUERY TEMPLATES
    # ================================================================
    
    SEARCH_TEMPLATES = {
        'tutorial': [
            '{technique} drum lesson',
            '{technique} drum tutorial',
            '{technique} how to play',
            '{technique} drum instruction',
            'learn {technique} drums'
        ],
        'demonstration': [
            '{technique} drum demo',
            '{technique} drum example',
            '{technique} drum breakdown',
            '{technique} explained'
        ],
        'isolated': [
            '{technique} isolated drums',
            '{technique} drum track only',
            '{technique} drums only'
        ]
    }
    
    def __init__(self, base_dir: Path = None):
        """
        Initialize foundation learning service.
        
        Args:
            base_dir: Base directory for data storage
        """
        if not SERVICES_AVAILABLE or YouTubeDrumDownloader is None:
            raise ImportError(
                "Required services not available. "
                "Make sure youtube_downloader.py exists in admin/training/ directory"
            )
        
        self.base_dir = base_dir or Path("admin/data/youtube_foundation_learning")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.downloads_dir = self.base_dir / "downloads"
        self.analysis_dir = self.base_dir / "analysis"
        self.datasets_dir = self.base_dir / "datasets"
        
        for d in [self.downloads_dir, self.analysis_dir, self.datasets_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Initialize YouTube downloader
        self.youtube_downloader = YouTubeDrumDownloader(self.downloads_dir)
        
        # Initialize main pipeline
        self.pipeline = YouTubeLLMLearningPipeline(base_dir=self.base_dir)
        
        logger.info(f"YouTube Foundation Learning initialized: {self.base_dir}")
    
    # ================================================================
    # AUTONOMOUS SEARCH QUERY GENERATION
    # ================================================================
    
    def generate_search_queries(self, technique: str, query_type: str = 'tutorial') -> List[str]:
        """
        Automatically generate search queries for a technique.
        
        Args:
            technique: Technique name (e.g., "paradiddle")
            query_type: Type of content to search for
        
        Returns:
            List of search query strings
        """
        templates = self.SEARCH_TEMPLATES.get(query_type, self.SEARCH_TEMPLATES['tutorial'])
        queries = [template.format(technique=technique) for template in templates]
        
        logger.info(f"Generated {len(queries)} search queries for: {technique}")
        return queries
    
    def get_all_foundation_queries(self, 
                                    level: str = None,
                                    priority: int = None,
                                    max_per_technique: int = 2) -> List[Dict]:
        """
        Generate ALL search queries for foundation learning.
        
        This method enables fully autonomous learning - the system
        knows what to search for without manual prompts!
        
        Args:
            level: Filter by difficulty (beginner/intermediate/advanced)
            priority: Filter by priority (1=highest)
            max_per_technique: Max queries per technique
        
        Returns:
            List of query dicts with metadata
        """
        all_queries = []
        
        for category_name, category_info in self.TECHNIQUE_CATEGORIES.items():
            # Filter by level if specified
            if level and category_info['level'] != level:
                continue
            
            # Filter by priority if specified
            if priority and category_info['priority'] != priority:
                continue
            
            # Generate queries for each technique in category
            for technique in category_info['techniques']:
                queries = self.generate_search_queries(technique, 'tutorial')[:max_per_technique]
                
                for query in queries:
                    all_queries.append({
                        'query': query,
                        'technique': technique,
                        'category': category_name,
                        'level': category_info['level'],
                        'priority': category_info['priority']
                    })
        
        logger.info(f"Generated {len(all_queries)} foundation queries")
        return all_queries
    
    # ================================================================
    # PROGRESSIVE FOUNDATION LEARNING
    # ================================================================
    
    def learn_foundation_progressive(self,
                                     max_videos_per_technique: int = 2,
                                     start_level: str = 'beginner') -> Dict:
        """
        Progressive foundation learning: beginner → intermediate → advanced.
        
        This is the main autonomous learning method!
        
        Args:
            max_videos_per_technique: Max videos to download per technique
            start_level: Starting difficulty level
        
        Returns:
            Dict with learning results
        """
        logger.info("\n" + "="*70)
        logger.info("🎓 PROGRESSIVE FOUNDATION LEARNING")
        logger.info("="*70)
        
        levels = ['beginner', 'intermediate', 'advanced']
        if start_level in levels:
            levels = levels[levels.index(start_level):]
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'levels_completed': [],
            'total_videos': 0,
            'total_techniques': 0,
            'datasets_created': []
        }
        
        for level in levels:
            logger.info(f"\n📚 Learning {level.upper()} techniques...")
            
            level_result = self.learn_foundation_level(
                level=level,
                max_videos_per_technique=max_videos_per_technique
            )
            
            results['levels_completed'].append(level_result)
            results['total_videos'] += level_result['videos_downloaded']
            results['total_techniques'] += level_result['techniques_learned']
            
            logger.info(f"✅ {level.upper()} complete: {level_result['videos_downloaded']} videos")
        
        logger.info("\n" + "="*70)
        logger.info(f"🎉 FOUNDATION LEARNING COMPLETE")
        logger.info(f"   Videos: {results['total_videos']}")
        logger.info(f"   Techniques: {results['total_techniques']}")
        logger.info("="*70)
        
        return results
    
    def learn_foundation_level(self,
                               level: str,
                               max_videos_per_technique: int = 2) -> Dict:
        """
        Learn all techniques at a specific level.
        
        Args:
            level: Difficulty level (beginner/intermediate/advanced)
            max_videos_per_technique: Max videos per technique
        
        Returns:
            Dict with level results
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"📖 LEARNING {level.upper()} LEVEL")
        logger.info(f"{'='*70}")
        
        # Get all queries for this level
        queries = self.get_all_foundation_queries(level=level, max_per_technique=max_videos_per_technique)
        
        downloaded_files = []
        techniques_learned = set()
        
        for i, query_info in enumerate(queries, 1):
            logger.info(f"\n[{i}/{len(queries)}] Searching: {query_info['query']}")
            logger.info(f"   Technique: {query_info['technique']}")
            logger.info(f"   Category: {query_info['category']}")
            
            try:
                # Download top result for this query
                files = self.youtube_downloader.download_search_results(
                    search_query=query_info['query'],
                    max_results=1,
                    style=level  # Use level as style marker
                )
                
                if files:
                    downloaded_files.extend(files)
                    techniques_learned.add(query_info['technique'])
                    logger.info(f"✅ Downloaded: {files[0].name}")
                else:
                    logger.warning(f"❌ No results for: {query_info['query']}")
                
                # Small delay to be nice to YouTube
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error downloading {query_info['query']}: {e}")
                continue
        
        # Build dataset for this level
        dataset_file = self._build_level_dataset(level, downloaded_files, techniques_learned)
        
        results = {
            'level': level,
            'videos_downloaded': len(downloaded_files),
            'techniques_learned': len(techniques_learned),
            'technique_list': sorted(list(techniques_learned)),
            'dataset_file': str(dataset_file) if dataset_file else None
        }
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ {level.upper()} LEVEL COMPLETE")
        logger.info(f"   Videos: {results['videos_downloaded']}")
        logger.info(f"   Techniques: {results['techniques_learned']}")
        logger.info(f"{'='*70}")
        
        return results
    
    # ================================================================
    # CATEGORY-SPECIFIC LEARNING
    # ================================================================
    
    def learn_category(self,
                       category_name: str,
                       max_videos_per_technique: int = 2) -> Dict:
        """
        Learn all techniques in a specific category.
        
        Example categories:
        - 'basic_beats'
        - 'rudiments'
        - 'ghost_notes'
        - 'fills'
        
        Args:
            category_name: Name of technique category
            max_videos_per_technique: Max videos per technique
        
        Returns:
            Dict with category results
        """
        if category_name not in self.TECHNIQUE_CATEGORIES:
            raise ValueError(f"Unknown category: {category_name}")
        
        category_info = self.TECHNIQUE_CATEGORIES[category_name]
        
        logger.info(f"\n{'='*70}")
        logger.info(f"📚 LEARNING CATEGORY: {category_name.upper()}")
        logger.info(f"   Level: {category_info['level']}")
        logger.info(f"   Techniques: {len(category_info['techniques'])}")
        logger.info(f"{'='*70}")
        
        downloaded_files = []
        
        for technique in category_info['techniques']:
            logger.info(f"\n🎯 Learning: {technique}")
            
            queries = self.generate_search_queries(technique, 'tutorial')[:max_videos_per_technique]
            
            for query in queries:
                try:
                    files = self.youtube_downloader.download_search_results(
                        search_query=query,
                        max_results=1,
                        style=category_name
                    )
                    
                    if files:
                        downloaded_files.extend(files)
                        logger.info(f"✅ {technique}: {files[0].name}")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue
        
        results = {
            'category': category_name,
            'level': category_info['level'],
            'videos_downloaded': len(downloaded_files),
            'techniques': category_info['techniques']
        }
        
        logger.info(f"\n✅ Category '{category_name}' complete: {len(downloaded_files)} videos")
        
        return results
    
    # ================================================================
    # DATASET BUILDING
    # ================================================================
    
    def _build_level_dataset(self, 
                             level: str, 
                             files: List[Path],
                             techniques: set) -> Optional[Path]:
        """Build training dataset for a difficulty level."""
        if not files:
            return None
        
        dataset = {
            'dataset_id': f"foundation_{level}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'track': 'A',  # Track A: General Expertise
            'level': level,
            'created': datetime.now().isoformat(),
            'techniques_covered': sorted(list(techniques)),
            'technique_count': len(techniques),
            'example_count': len(files),
            'examples': []
        }
        
        # Add basic metadata for each file
        for file_path in files:
            dataset['examples'].append({
                'file': str(file_path),
                'level': level,
                'track': 'A'
            })
        
        # Save dataset
        dataset_file = self.datasets_dir / f"{dataset['dataset_id']}.json"
        import json
        with open(dataset_file, 'w') as f:
            json.dump(dataset, f, indent=2)
        
        logger.info(f"💾 Dataset saved: {dataset_file.name}")
        
        return dataset_file
    
    # ================================================================
    # QUERY SYSTEM STATUS
    # ================================================================
    
    def get_available_techniques(self) -> Dict:
        """
        Get all available techniques the system can learn autonomously.
        
        Returns:
            Dict organized by category and level
        """
        summary = {
            'total_categories': len(self.TECHNIQUE_CATEGORIES),
            'total_techniques': sum(len(cat['techniques']) for cat in self.TECHNIQUE_CATEGORIES.values()),
            'by_level': {},
            'by_category': {}
        }
        
        # Organize by level
        for level in ['beginner', 'intermediate', 'advanced']:
            level_techniques = []
            for category_name, category_info in self.TECHNIQUE_CATEGORIES.items():
                if category_info['level'] == level:
                    level_techniques.extend(category_info['techniques'])
            summary['by_level'][level] = {
                'count': len(level_techniques),
                'techniques': level_techniques
            }
        
        # Organize by category
        for category_name, category_info in self.TECHNIQUE_CATEGORIES.items():
            summary['by_category'][category_name] = {
                'level': category_info['level'],
                'priority': category_info['priority'],
                'count': len(category_info['techniques']),
                'techniques': category_info['techniques']
            }
        
        return summary


# ================================================================
# CONVENIENCE FUNCTIONS
# ================================================================

def quick_foundation_learning(level: str = 'beginner', max_videos_per_technique: int = 2) -> Dict:
    """
    Quick start: Learn foundation techniques at specific level.
    
    Example:
        result = quick_foundation_learning('beginner', 2)
    """
    learner = YouTubeFoundationLearning()
    return learner.learn_foundation_level(level, max_videos_per_technique)


def full_foundation_curriculum(max_videos_per_technique: int = 2) -> Dict:
    """
    Learn complete foundation: beginner → intermediate → advanced.
    
    This runs autonomously with no manual prompts needed!
    
    Example:
        result = full_foundation_curriculum(2)
    """
    learner = YouTubeFoundationLearning()
    return learner.learn_foundation_progressive(max_videos_per_technique)


def show_available_techniques():
    """Show all techniques the system can learn autonomously."""
    learner = YouTubeFoundationLearning()
    summary = learner.get_available_techniques()
    
    print("\n" + "="*70)
    print("📚 AVAILABLE FOUNDATION TECHNIQUES")
    print("="*70)
    print(f"\nTotal Categories: {summary['total_categories']}")
    print(f"Total Techniques: {summary['total_techniques']}")
    
    print("\n📊 BY LEVEL:")
    for level, info in summary['by_level'].items():
        print(f"\n{level.upper()}: {info['count']} techniques")
        for tech in info['techniques'][:5]:  # Show first 5
            print(f"  - {tech}")
        if len(info['techniques']) > 5:
            print(f"  ... and {len(info['techniques']) - 5} more")
    
    print("\n📚 BY CATEGORY:")
    for category, info in summary['by_category'].items():
        print(f"\n{category}: {info['count']} techniques ({info['level']} level)")
    
    print("\n" + "="*70)
    print("The system can search for ALL of these autonomously!")
    print("="*70)


if __name__ == "__main__":
    # Test/demo the system
    print("🧪 YouTube Foundation Learning - Test Mode")
    print("=" * 70)
    
    if not SERVICES_AVAILABLE:
        print("❌ Required services not available")
        exit(1)
    
    # Show what's available
    show_available_techniques()
    
    print("\n" + "="*70)
    print("Ready for autonomous foundation learning!")
    print("\nExample usage:")
    print("  result = quick_foundation_learning('beginner', 2)")
    print("  result = full_foundation_curriculum(2)")
    print("  learner.learn_category('rudiments', 3)")
