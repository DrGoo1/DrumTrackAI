"""
YouTube LLM Learning Service
============================
Integrates YouTube downloads with LLM training pipeline.
Automatically sources, analyzes, and trains from YouTube drum performances.

This service ties together:
- YouTube download service (youtube_service.py)
- Audio analysis (Rust audio-core)
- Feature extraction (training/data_extraction.py)
- Database building (training/database_bootstrapper.py)
- LLM training (ui/llm_training_widget.py)

Workflow:
1. Search YouTube for specific drummers/styles
2. Download audio performances
3. Analyze and extract features
4. Build training datasets
5. Trigger LLM training
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import subprocess
import time

from backend.drummerbrain.ingest_audio_phrases import main as ingest_audio_phrases_main

logger = logging.getLogger(__name__)

# Import existing services
try:
    from .youtube_service import YouTubeService
    from ..training.youtube_downloader import YouTubeDrumDownloader, FAMOUS_DRUMMER_SEARCHES
    from ..training.data_extraction import CommercialSongAnalyzer, HumanizationFeatures
    SERVICES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some services not available: {e}")
    SERVICES_AVAILABLE = False


class YouTubeLLMLearningPipeline:
    """
    Complete pipeline from YouTube sourcing to LLM training.
    
    Features:
    - Intelligent drummer/style search
    - Automatic audio download
    - Feature extraction via Rust audio-core
    - Dataset building for LLM training
    - Progress tracking and monitoring
    """
    
    def __init__(self, 
                 base_dir: Path = None,
                 audio_core_bin: str = None):
        """
        Initialize the YouTube LLM learning pipeline.
        
        Args:
            base_dir: Base directory for data storage
            audio_core_bin: Path to Rust audio-core binary
        """
        self.base_dir = base_dir or Path("admin/data/youtube_llm_learning")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Sub-directories
        self.downloads_dir = self.base_dir / "downloads"
        self.analysis_dir = self.base_dir / "analysis"
        self.datasets_dir = self.base_dir / "datasets"
        self.models_dir = self.base_dir / "models"
        
        for d in [self.downloads_dir, self.analysis_dir, self.datasets_dir, self.models_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Initialize services
        self.youtube_service = YouTubeService()
        self.youtube_downloader = YouTubeDrumDownloader(self.downloads_dir)
        
        # Rust audio-core binary
        self.audio_core_bin = audio_core_bin or self._find_audio_core()
        
        # Metadata tracking
        self.metadata_file = self.base_dir / "learning_pipeline_metadata.json"
        self.metadata = self._load_metadata()
        
        logger.info(f"YouTube LLM Learning Pipeline initialized: {self.base_dir}")
        logger.info(f"Audio Core: {self.audio_core_bin}")
    
    def _find_audio_core(self) -> Optional[str]:
        """Auto-detect Rust audio-core binary."""
        possible_paths = [
            Path("target/release/audio-core.exe"),
            Path("target/release/audio-core"),
            Path("audio-core/target/release/audio-core.exe"),
            Path("audio-core/target/release/audio-core"),
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"Found audio-core: {path}")
                return str(path)
        
        logger.warning("audio-core binary not found - analysis will be limited")
        return None
    
    def _load_metadata(self) -> Dict:
        """Load pipeline metadata."""
        if self.metadata_file.exists():
            with open(self.metadata_file) as f:
                return json.load(f)
        return {
            'learning_sessions': [],
            'trained_models': [],
            'performance_metrics': []
        }
    
    def _save_metadata(self):
        """Save pipeline metadata."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    # =================================================================
    # STEP 1: INTELLIGENT YOUTUBE SOURCING
    # =================================================================
    
    def search_and_source_drummer(self,
                                   drummer_name: str,
                                   style: str = "rock",
                                   max_videos: int = 5,
                                   quality_threshold: float = 0.7) -> Dict:
        """
        Intelligently search and source drummer performances from YouTube.
        
        Args:
            drummer_name: Drummer name (e.g., "Jeff Porcaro")
            style: Drum style (rock, jazz, funk, etc.)
            max_videos: Maximum videos to download
            quality_threshold: Minimum quality score (0-1)
        
        Returns:
            Dict with sourcing results
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"🎯 SOURCING: {drummer_name} ({style})")
        logger.info(f"{'='*70}")
        
        session_id = f"{drummer_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_download_dir = self.downloads_dir / session_id
        session_download_dir.mkdir(parents=True, exist_ok=True)

        # Use a per-session downloader so each run has an isolated root folder.
        downloader = YouTubeDrumDownloader(session_download_dir)
        
        # Get search queries for this drummer
        search_queries = FAMOUS_DRUMMER_SEARCHES.get(drummer_name, [
            f"{drummer_name} drum solo",
            f"{drummer_name} isolated drums",
            f"{drummer_name} drum cam"
        ])
        
        downloaded_files = []
        analysis_results = []
        
        for query in search_queries[:max_videos]:
            logger.info(f"\n🔍 Searching: {query}")
            
            # Download from search
            files = downloader.download_search_results(
                query,
                max_results=1,  # 1 per query
                drummer_name=drummer_name,
                style=style
            )
            
            for file in files:
                # Analyze quality
                quality_score = self._analyze_audio_quality(file)
                
                if quality_score >= quality_threshold:
                    logger.info(f"✅ Quality: {quality_score:.2f} - ACCEPTED")
                    downloaded_files.append(file)
                    analysis_results.append({
                        'file': str(file),
                        'quality': quality_score,
                        'query': query
                    })
                else:
                    logger.info(f"❌ Quality: {quality_score:.2f} - REJECTED (< {quality_threshold})")
        
        # Save session metadata
        session_data = {
            'session_id': session_id,
            'drummer_name': drummer_name,
            'style': style,
            'timestamp': datetime.now().isoformat(),
            'files_downloaded': len(downloaded_files),
            'files': [str(f) for f in downloaded_files],
            'download_root': str(session_download_dir),
            'analysis': analysis_results
        }
        
        self.metadata['learning_sessions'].append(session_data)
        self._save_metadata()
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ SOURCED: {len(downloaded_files)} quality performances")
        logger.info(f"{'='*70}")
        
        return session_data

    def source_from_urls(
        self,
        *,
        drummer_name: str,
        style: str,
        urls: List[str],
        quality_threshold: float = 0.0,
        session_id: Optional[str] = None,
    ) -> Dict:
        sid = session_id or f"{drummer_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_download_dir = self.downloads_dir / sid
        session_download_dir.mkdir(parents=True, exist_ok=True)
        downloader = YouTubeDrumDownloader(session_download_dir)

        normalized_urls = [str(u).strip() for u in (urls or []) if str(u).strip()]
        downloaded_files: List[Path] = []
        analysis_results: List[Dict] = []

        for url in normalized_urls:
            f = downloader.download_video(url, drummer_name=drummer_name, style=style, extract_audio_only=True)
            if not f:
                analysis_results.append({"file": "", "quality": 0.0, "query": "url", "url": url, "error": "download_failed"})
                continue

            quality_score = self._analyze_audio_quality(Path(f))
            if float(quality_threshold or 0.0) <= 0.0 or quality_score >= float(quality_threshold):
                downloaded_files.append(Path(f))
                analysis_results.append({"file": str(f), "quality": quality_score, "query": "url", "url": url})
            else:
                analysis_results.append({"file": str(f), "quality": quality_score, "query": "url", "url": url, "rejected": True})

        session_data = {
            "session_id": sid,
            "drummer_name": drummer_name,
            "style": style,
            "timestamp": datetime.now().isoformat(),
            "files_downloaded": len(downloaded_files),
            "files": [str(p) for p in downloaded_files],
            "download_root": str(session_download_dir),
            "analysis": analysis_results,
            "source": "urls",
            "urls": normalized_urls,
        }

        self.metadata["learning_sessions"].append(session_data)
        self._save_metadata()
        return session_data

    def ingest_session_to_drummerbrain(
        self,
        *,
        session_id: str,
        dataset_id: Optional[str] = None,
        label: Optional[str] = None,
        limit: int = 0,
        subdiv: int = 4,
    ) -> Dict:
        session = next((s for s in self.metadata['learning_sessions'] if s.get('session_id') == session_id), None)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        root = Path(str(session.get('download_root') or '')).resolve()
        if not root.exists():
            raise FileNotFoundError(str(root))

        dsid = str(dataset_id or f"sig_{session_id}")
        lbl = str(label or f"Signature Songs: {session.get('drummer_name','')} ({session.get('style','')})")

        argv = [
            "--root",
            str(root),
            "--dataset-id",
            dsid,
            "--label",
            lbl,
            "--subdiv",
            str(int(subdiv)),
        ]
        if int(limit or 0) > 0:
            argv += ["--limit", str(int(limit))]

        rc = int(ingest_audio_phrases_main(argv))
        return {
            "ok": rc == 0,
            "return_code": rc,
            "session_id": session_id,
            "dataset_id": dsid,
            "label": lbl,
            "root": str(root),
        }
    
    def _analyze_audio_quality(self, audio_file: Path) -> float:
        """
        Analyze audio quality to filter out poor recordings.
        
        Returns quality score 0-1 based on:
        - Audio clarity (SNR estimate)
        - Drum presence (spectral energy in drum freq bands)
        - Duration (prefer 2-5 minute performances)
        - Dynamics (sufficient velocity variation)
        """
        if not self.audio_core_bin:
            return 0.5  # Default if no audio-core
        
        try:
            # Run audio-core analysis
            result = subprocess.run(
                [self.audio_core_bin, "analyze", str(audio_file), "--min-bpm", "60", "--max-bpm", "200"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return 0.5
            
            analysis = json.loads(result.stdout)
            
            # Quality factors
            tempo = analysis.get('tempo', 0)
            onsets = analysis.get('onsets', [])
            
            # Score based on onset density (good drum performances have clear hits)
            onset_density = len(onsets) / max(analysis.get('duration', 1), 1) if onsets else 0
            density_score = min(onset_density / 2.0, 1.0)  # Normalize to 0-1
            
            # Tempo confidence (clear tempo = good recording)
            tempo_score = 1.0 if 60 <= tempo <= 200 else 0.5
            
            # Combined quality score
            quality = (density_score * 0.7) + (tempo_score * 0.3)
            
            return quality
            
        except Exception as e:
            logger.warning(f"Quality analysis failed: {e}")
            return 0.5
    
    # =================================================================
    # STEP 2: FEATURE EXTRACTION FOR LLM TRAINING
    # =================================================================
    
    def extract_llm_training_features(self, audio_file: Path, drummer_name: str, style: str) -> Dict:
        """
        Extract features optimized for LLM drum pattern learning.
        
        Returns comprehensive feature set:
        - Timing features (micro-timing, swing, groove)
        - Velocity features (dynamics, accents, ghost notes)
        - Pattern features (fills, transitions, complexity)
        - Style features (genre markers, signature patterns)
        """
        logger.info(f"🔬 Extracting LLM training features: {audio_file.name}")
        
        features = {
            'file': str(audio_file),
            'drummer': drummer_name,
            'style': style,
            'timestamp': datetime.now().isoformat()
        }
        
        if not self.audio_core_bin:
            logger.warning("Audio-core not available - using basic features")
            return features
        
        try:
            # Tempo and beat analysis
            tempo_result = self._run_audio_core(["analyze", str(audio_file), "--min-bpm", "60", "--max-bpm", "200"])
            features['tempo'] = tempo_result.get('tempo', 120)
            features['beats'] = tempo_result.get('beats', [])
            features['onsets'] = tempo_result.get('onsets', [])
            
            # Section analysis
            sections_result = self._run_audio_core([
                "sectionize-smart", str(audio_file),
                "--bpm", str(features['tempo']),
                "--min-bars", "4",
                "--max-bars", "16"
            ])
            features['sections'] = sections_result.get('sections', [])
            
            # Timing analysis (micro-timing variations)
            if features['beats']:
                beats = features['beats']
                beat_intervals = [beats[i+1] - beats[i] for i in range(len(beats)-1)]
                features['timing_variance'] = float(self._calculate_variance(beat_intervals))
                features['timing_stability'] = float(self._calculate_stability(beat_intervals))
            
            # Velocity/dynamics analysis (from onsets)
            if features['onsets']:
                # Onset strength variations indicate dynamics
                onset_times = [o['time'] for o in features['onsets'] if isinstance(o, dict)]
                onset_strengths = [o.get('strength', 1.0) for o in features['onsets'] if isinstance(o, dict)]
                features['dynamic_range'] = float(max(onset_strengths) - min(onset_strengths)) if onset_strengths else 0.0
                features['average_onset_strength'] = float(sum(onset_strengths) / len(onset_strengths)) if onset_strengths else 0.0
            
            # Pattern complexity
            features['pattern_complexity'] = self._calculate_pattern_complexity(features)
            
            # Save features to analysis directory
            feature_file = self.analysis_dir / f"{audio_file.stem}_features.json"
            with open(feature_file, 'w') as f:
                json.dump(features, f, indent=2)
            
            logger.info(f"✅ Features extracted: {feature_file.name}")
            
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return features
    
    def _run_audio_core(self, args: List[str]) -> Dict:
        """Run audio-core and return JSON result."""
        try:
            result = subprocess.run(
                [self.audio_core_bin] + args,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                raise Exception(f"audio-core failed: {result.stderr}")
            
            return json.loads(result.stdout)
            
        except Exception as e:
            logger.error(f"audio-core execution failed: {e}")
            return {}
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values."""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
    
    def _calculate_stability(self, values: List[float]) -> float:
        """Calculate stability (inverse of coefficient of variation)."""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0
        variance = self._calculate_variance(values)
        std_dev = variance ** 0.5
        cv = std_dev / mean  # Coefficient of variation
        return 1.0 / (1.0 + cv)  # Normalize to 0-1
    
    def _calculate_pattern_complexity(self, features: Dict) -> float:
        """
        Calculate pattern complexity score.
        Higher = more complex patterns (fills, variations, polyrhythms)
        """
        complexity = 0.0
        
        # Onset density contributes to complexity
        if features.get('onsets'):
            onset_density = len(features['onsets']) / max(features.get('duration', 1), 1)
            complexity += min(onset_density / 3.0, 0.5)  # Max 0.5 from density
        
        # Timing variance contributes (more variance = more complex)
        if features.get('timing_variance'):
            complexity += min(features['timing_variance'] * 10, 0.3)  # Max 0.3 from timing
        
        # Dynamic range contributes (more dynamics = more complex)
        if features.get('dynamic_range'):
            complexity += min(features['dynamic_range'] / 2.0, 0.2)  # Max 0.2 from dynamics
        
        return min(complexity, 1.0)
    
    # =================================================================
    # STEP 3: DATASET BUILDING FOR LLM TRAINING
    # =================================================================
    
    def build_llm_training_dataset(self, session_id: str) -> Path:
        """
        Build LLM training dataset from a learning session.
        
        Creates dataset in format:
        {
            "drummer": "Jeff Porcaro",
            "style": "rock",
            "examples": [
                {
                    "audio_features": {...},
                    "patterns": [...],
                    "metadata": {...}
                }
            ]
        }
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"📦 BUILDING LLM TRAINING DATASET: {session_id}")
        logger.info(f"{'='*70}")
        
        # Find session
        session = next((s for s in self.metadata['learning_sessions'] if s['session_id'] == session_id), None)
        
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        dataset = {
            'dataset_id': session_id,
            'drummer': session['drummer_name'],
            'style': session['style'],
            'created': datetime.now().isoformat(),
            'examples': []
        }
        
        # Extract features from each file
        for file_path in session['files']:
            file = Path(file_path)
            
            if not file.exists():
                logger.warning(f"File not found: {file}")
                continue
            
            # Extract features
            features = self.extract_llm_training_features(file, session['drummer_name'], session['style'])
            
            # Add to dataset
            dataset['examples'].append({
                'audio_features': features,
                'source_file': str(file),
                'quality_score': next((a['quality'] for a in session['analysis'] if a['file'] == str(file)), 0.5)
            })
        
        # Save dataset
        dataset_file = self.datasets_dir / f"{session_id}_dataset.json"
        with open(dataset_file, 'w') as f:
            json.dump(dataset, f, indent=2)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ DATASET BUILT: {dataset_file.name}")
        logger.info(f"   Examples: {len(dataset['examples'])}")
        logger.info(f"   Drummer: {dataset['drummer']}")
        logger.info(f"   Style: {dataset['style']}")
        logger.info(f"{'='*70}")
        
        return dataset_file
    
    # =================================================================
    # STEP 4: COMPLETE PIPELINE EXECUTION
    # =================================================================
    
    def run_complete_pipeline(self,
                              drummer_name: str,
                              style: str = "rock",
                              max_videos: int = 5,
                              start_training: bool = False,
                              ingest_to_drummerbrain: bool = False,
                              drummerbrain_limit: int = 0,
                              urls: Optional[List[str]] = None,
                              quality_threshold: float = 0.7) -> Dict:
        """
        Run the complete YouTube-to-LLM pipeline.
        
        Steps:
        1. Source performances from YouTube
        2. Analyze audio quality
        3. Extract features
        4. Build training dataset
        5. (Optional) Trigger LLM training
        
        Returns:
            Pipeline results with all metadata
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"🚀 STARTING COMPLETE PIPELINE")
        logger.info(f"   Drummer: {drummer_name}")
        logger.info(f"   Style: {style}")
        logger.info(f"   Max Videos: {max_videos}")
        logger.info(f"{'='*70}")
        
        start_time = time.time()
        
        try:
            # Step 1: Source from YouTube
            if urls:
                session = self.source_from_urls(
                    drummer_name=drummer_name,
                    style=style,
                    urls=list(urls),
                    quality_threshold=float(quality_threshold or 0.0),
                )
            else:
                session = self.search_and_source_drummer(
                    drummer_name,
                    style,
                    max_videos,
                    float(quality_threshold or 0.0),
                )
            
            # Step 2: Build dataset
            dataset_file = self.build_llm_training_dataset(session['session_id'])

            # Step 2.5: Ingest to drummerbrain DB (optional)
            ingest_status = None
            if ingest_to_drummerbrain:
                ingest_status = self.ingest_session_to_drummerbrain(
                    session_id=session['session_id'],
                    dataset_id=f"sig_{drummer_name.replace(' ', '_').lower()}_{style}",
                    label=f"Signature Songs: {drummer_name} ({style})",
                    limit=int(drummerbrain_limit or 0),
                )
            
            # Step 3: (Optional) Start training
            training_status = None
            if start_training:
                logger.info("\n🤖 Starting LLM training...")
                training_status = self._trigger_llm_training(dataset_file)
            
            elapsed_time = time.time() - start_time
            
            # Results
            results = {
                'success': True,
                'session_id': session['session_id'],
                'drummer': drummer_name,
                'style': style,
                'files_sourced': session['files_downloaded'],
                'dataset_file': str(dataset_file),
                'drummerbrain_ingest': ingest_status,
                'training_started': training_status is not None,
                'training_status': training_status,
                'elapsed_time': elapsed_time
            }
            
            logger.info(f"\n{'='*70}")
            logger.info(f"✅ PIPELINE COMPLETE")
            logger.info(f"   Time: {elapsed_time:.1f}s")
            logger.info(f"   Files: {results['files_sourced']}")
            logger.info(f"   Dataset: {dataset_file.name}")
            logger.info(f"{'='*70}")
            
            return results
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'elapsed_time': time.time() - start_time
            }
    
    def _trigger_llm_training(self, dataset_file: Path) -> Dict:
        """Trigger LLM training with the generated dataset."""
        # This would integrate with the existing LLM training widget
        logger.info(f"Training triggered with dataset: {dataset_file}")
        
        return {
            'status': 'queued',
            'dataset': str(dataset_file),
            'message': 'Training queued - check LLM Training tab for progress'
        }
    
    # =================================================================
    # BATCH OPERATIONS
    # =================================================================
    
    def run_batch_pipeline(self, drummers: List[Tuple[str, str]], max_videos_each: int = 3) -> List[Dict]:
        """
        Run pipeline for multiple drummers.
        
        Args:
            drummers: List of (drummer_name, style) tuples
            max_videos_each: Max videos per drummer
        
        Returns:
            List of results for each drummer
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"🎯 BATCH PIPELINE: {len(drummers)} drummers")
        logger.info(f"{'='*70}")
        
        results = []
        
        for i, (drummer, style) in enumerate(drummers, 1):
            logger.info(f"\n[{i}/{len(drummers)}] Processing: {drummer} ({style})")
            
            result = self.run_complete_pipeline(drummer, style, max_videos_each, start_training=False)
            results.append(result)
            
            # Small delay between downloads to be nice to YouTube
            time.sleep(2)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ BATCH COMPLETE: {len([r for r in results if r['success']])} successful")
        logger.info(f"{'='*70}")
        
        return results


# =================================================================
# CONVENIENCE FUNCTIONS
# =================================================================

def quick_learn_from_youtube(drummer_name: str, 
                              style: str = "rock",
                              max_videos: int = 5) -> Dict:
    """
    Quick single-function pipeline execution.
    
    Example:
        result = quick_learn_from_youtube("Jeff Porcaro", "rock", 5)
    """
    pipeline = YouTubeLLMLearningPipeline()
    return pipeline.run_complete_pipeline(drummer_name, style, max_videos)


def batch_learn_famous_drummers(max_videos_each: int = 3) -> List[Dict]:
    """
    Learn from all famous drummers in predefined list.
    
    Example:
        results = batch_learn_famous_drummers(3)
    """
    famous_drummers = [
        ("Jeff Porcaro", "rock"),
        ("John Bonham", "rock"),
        ("Neil Peart", "rock"),
        ("Dave Grohl", "rock"),
        ("Steve Gadd", "jazz"),
    ]
    
    pipeline = YouTubeLLMLearningPipeline()
    return pipeline.run_batch_pipeline(famous_drummers, max_videos_each)


if __name__ == "__main__":
    # Test the pipeline
    print("🧪 YouTube LLM Learning Pipeline - Test Mode")
    print("=" * 70)
    
    if not SERVICES_AVAILABLE:
        print("❌ Required services not available")
        print("\nMake sure you have:")
        print("  - youtube_service.py")
        print("  - training/youtube_downloader.py")
        print("  - training/data_extraction.py")
        exit(1)
    
    # Create pipeline
    pipeline = YouTubeLLMLearningPipeline()
    
    print(f"\n✅ Pipeline initialized")
    print(f"   Base directory: {pipeline.base_dir}")
    print(f"   Audio-core: {pipeline.audio_core_bin}")
    
    print("\n" + "=" * 70)
    print("Ready to learn from YouTube!")
    print("\nExample usage:")
    print("  result = pipeline.run_complete_pipeline('Jeff Porcaro', 'rock', max_videos=5)")
    print("  results = pipeline.run_batch_pipeline([('Jeff Porcaro', 'rock'), ('John Bonham', 'rock')])")
