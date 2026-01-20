"""
DrumTrackAI Drummer Mapping Service

Bridges admin database (real drummer analysis) to user app (fictional DrumTrackAI drummers)

Admin DB: Real names, actual analysis, training data
User App: Fictional names, legal protection, user-friendly

Architecture:
    Admin DB → Mapping Layer → User App API → Frontend
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Fictional drummer definitions mapped to real drummer analysis
DRUMTRACKAI_DRUMMERS = {
    "default_neutral": {
        "display_name": "Default (Preserve Style)",
        "tagline": "Neutral drummer that preserves the selected groove",
        "genre_tags": ["All"],
        "difficulty": "Beginner",
        "icon": "🎯",
        "color": "#64748B",
        "description": "A neutral drummer profile intended for validation and groove preservation. Minimal humanization and no stylistic embellishments.",
        "best_for": ["Verifying groove selection", "Preserving EGMD Basic Drum Style", "Neutral playback"],
        "signature_techniques": ["None"],
        "source_drummers": ["jeff_porcaro"],
        "blend_weights": [1.0],
    },
    "studio_groove_master": {
        "display_name": "Studio Groove Master",
        "tagline": "Precision pocket playing with legendary studio chops",
        "genre_tags": ["Jazz Fusion", "Pop", "Rock", "Session Work"],
        "difficulty": "Advanced",
        "icon": "🎩",
        "color": "#4F46E5",
        "description": "Master of the pocket with impeccable timing. Known for sophisticated ghost notes, half-time feels, and knowing exactly what the song needs. Perfect for jazz fusion, pop, and session work.",
        "best_for": ["Steely Dan style", "Toto grooves", "Sophisticated pop", "Jazz fusion"],
        "signature_techniques": ["Half-time shuffle", "Ghost note mastery", "Ride cymbal work", "Linear fills"],
        # Map to real drummer(s) in admin database
        "source_drummers": ["jeff_porcaro"],
        "blend_weights": [1.0]  # 100% Jeff Porcaro characteristics
    },
    "metal_atomic_clock": {
        "display_name": "Metal Atomic Clock",
        "tagline": "Inhuman precision meets extreme metal intensity",
        "genre_tags": ["Death Metal", "Thrash", "Technical Metal"],
        "difficulty": "Expert",
        "icon": "⚡",
        "color": "#DC2626",
        "description": "Relentless precision and speed. Master of blast beats, double bass, and complex time signatures. Mechanical consistency with human feel.",
        "best_for": ["Extreme metal", "Technical death metal", "Thrash", "Fast tempos"],
        "signature_techniques": ["Blast beats", "Double bass precision", "Complex fills", "Odd time signatures"],
        "source_drummers": ["gene_hoglan"],
        "blend_weights": [1.0]
    },
    "progressive_polymath": {
        "display_name": "Progressive Polymath",
        "tagline": "Complex rhythms and orchestral arrangements",
        "genre_tags": ["Progressive Rock", "Progressive Metal", "Math Rock"],
        "difficulty": "Expert",
        "icon": "🎼",
        "color": "#7C3AED",
        "description": "Master of odd time signatures and complex arrangements. Approaches drums like an orchestral composer with mathematical precision.",
        "best_for": ["Dream Theater style", "Tool rhythms", "Prog metal", "Complex arrangements"],
        "signature_techniques": ["Odd time signatures", "Polyrhythms", "Orchestral approach", "Dynamic control"],
        "source_drummers": ["mike_portnoy", "danny_carey"],
        "blend_weights": [0.6, 0.4]  # 60% Portnoy, 40% Carey blend
    },
    "funk_machine": {
        "display_name": "Funk Machine",
        "tagline": "Infectious grooves and pocket supremacy",
        "genre_tags": ["Funk", "R&B", "Soul", "Gospel"],
        "difficulty": "Advanced",
        "icon": "🕺",
        "color": "#F59E0B",
        "description": "The pocket is home. Master of funk grooves, gospel chops, and making people move. Lightning-fast singles with deep groove foundation.",
        "best_for": ["P-Funk style", "Gospel", "Neo-soul", "R&B"],
        "signature_techniques": ["Funk grooves", "Gospel chops", "Linear fills", "Pocket playing"],
        "source_drummers": ["dennis_chambers"],
        "blend_weights": [1.0]
    },
    "jazz_innovator": {
        "display_name": "Jazz Innovator",
        "tagline": "Polyrhythmic pioneer with avant-garde edge",
        "genre_tags": ["Jazz", "Bebop", "Fusion", "Avant-garde"],
        "difficulty": "Expert",
        "icon": "🎷",
        "color": "#10B981",
        "description": "Conversational and interactive. Master of polyrhythmic playing, dynamic swells, and responding to other musicians. The drums sing.",
        "best_for": ["Jazz standards", "Bebop", "Free jazz", "Interactive playing"],
        "signature_techniques": ["Polyrhythmic playing", "Rolling triplets", "Dynamic swells", "Interactive listening"],
        "source_drummers": ["elvin_jones", "tony_williams"],
        "blend_weights": [0.5, 0.5]  # 50/50 blend
    },
    "rock_powerhouse": {
        "display_name": "Rock Powerhouse",
        "tagline": "Raw energy and thunderous grooves",
        "genre_tags": ["Rock", "Hard Rock", "Blues Rock"],
        "difficulty": "Intermediate",
        "icon": "🔨",
        "color": "#EF4444",
        "description": "Thunderous and groovy. Master of single bass drum virtuosity, triplet patterns, and making every hit count. Power with pocket.",
        "best_for": ["Led Zeppelin style", "Classic rock", "Blues rock", "Groove-heavy rock"],
        "signature_techniques": ["Triplet patterns", "Heavy foot", "Dynamic range", "Groove-oriented"],
        "source_drummers": ["john_bonham"],
        "blend_weights": [1.0]
    },
    "alternative_innovator": {
        "display_name": "Alternative Innovator",
        "tagline": "Simple effectiveness with raw power",
        "genre_tags": ["Grunge", "Alternative Rock", "Punk"],
        "difficulty": "Intermediate",
        "icon": "🤘",
        "color": "#6366F1",
        "description": "Less is more with maximum impact. Raw energy, simple patterns executed with devastating effectiveness. The song comes first.",
        "best_for": ["Grunge", "Alternative rock", "Punk", "Garage rock"],
        "signature_techniques": ["Power playing", "Simple effectiveness", "Energetic style", "Primal energy"],
        "source_drummers": ["dave_grohl"],
        "blend_weights": [1.0]
    },
    "world_fusion_master": {
        "display_name": "World Fusion Master",
        "tagline": "Global rhythms meet modern rock",
        "genre_tags": ["World Music", "Reggae", "New Wave", "Fusion"],
        "difficulty": "Advanced",
        "icon": "🌍",
        "color": "#14B8A6",
        "description": "Master of world rhythms blended with rock sensibility. Reggae, African, and Latin influences create unique hybrid grooves.",
        "best_for": ["Police style", "Reggae rock", "World fusion", "New wave"],
        "signature_techniques": ["Reggae influences", "Hi-hat mastery", "Splash cymbals", "World music fusion"],
        "source_drummers": ["stewart_copeland"],
        "blend_weights": [1.0]
    },
    "hip_hop_architect": {
        "display_name": "Hip-Hop Architect",
        "tagline": "Minimalist pocket with maximum groove",
        "genre_tags": ["Hip-Hop", "Neo-Soul", "R&B"],
        "difficulty": "Advanced",
        "icon": "🎤",
        "color": "#8B5CF6",
        "description": "The human MPC. Master of sample-based playing, deep pocket, and knowing when NOT to play. Hip-hop grooves with live feel.",
        "best_for": ["Roots style", "Neo-soul", "Boom-bap", "Live hip-hop"],
        "signature_techniques": ["Sample-based playing", "Pocket mastery", "Minimalist approach", "Human MPC"],
        "source_drummers": ["questlove"],
        "blend_weights": [1.0]
    },
    "metal_chaos_master": {
        "display_name": "Metal Chaos Master",
        "tagline": "Tribal intensity meets industrial aggression",
        "genre_tags": ["Nu Metal", "Industrial", "Alternative Metal"],
        "difficulty": "Advanced",
        "icon": "💀",
        "color": "#991B1B",
        "description": "Aggressive and unconventional. Master of fast double bass, tribal rhythms, and percussive elements. Chaos with control.",
        "best_for": ["Slipknot style", "Industrial metal", "Nu metal", "Aggressive styles"],
        "signature_techniques": ["Fast double bass", "Tribal rhythms", "Percussive elements", "Unconventional patterns"],
        "source_drummers": ["joey_jordison"],
        "blend_weights": [1.0]
    },
}


class DrummerMappingService:
    """
    Maps DrumTrackAI fictional drummers to real drummer analysis in admin database
    """
    
    def __init__(self, admin_db_path: str = None):
        if admin_db_path is None:
            admin_db_path = Path(__file__).parent / "admin" / "drumtrackai.db"
        self.admin_db_path = str(admin_db_path)
        logger.info(f"DrummerMappingService initialized with DB: {self.admin_db_path}")
    
    def list_drummers(self) -> List[Dict[str, Any]]:
        """
        Get list of DrumTrackAI drummers for user app
        Returns user-friendly data without exposing real names
        """
        drummers = []
        for drummer_id, drummer_data in DRUMTRACKAI_DRUMMERS.items():
            style = self.map_to_rust_style(drummer_id)
            drummers.append({
                "id": drummer_id,
                "display_name": drummer_data["display_name"],
                "tagline": drummer_data["tagline"],
                "genre_tags": drummer_data["genre_tags"],
                "style": style,
                "profileType": style,
                "difficulty": drummer_data["difficulty"],
                "icon": drummer_data["icon"],
                "color": drummer_data["color"],
                "description": drummer_data["description"],
                "best_for": drummer_data["best_for"],
                "signature_techniques": drummer_data["signature_techniques"]
            })
        
        return drummers
    
    def get_drummer_characteristics(self, drummer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get quantified characteristics for a DrumTrackAI drummer
        Pulls from admin database and blends if multiple sources
        """
        if drummer_id not in DRUMTRACKAI_DRUMMERS:
            logger.warning(f"Unknown drummer_id: {drummer_id}")
            return None
        
        drummer_def = DRUMTRACKAI_DRUMMERS[drummer_id]
        source_drummers = drummer_def["source_drummers"]
        blend_weights = drummer_def["blend_weights"]
        
        # Load characteristics from admin database
        characteristics = {}
        
        try:
            conn = sqlite3.connect(self.admin_db_path)
            c = conn.cursor()
            
            # For each source drummer, get their style vector
            for i, source_id in enumerate(source_drummers):
                weight = blend_weights[i]
                
                # Query admin database for this drummer's characteristics
                c.execute("""
                    SELECT style_vector_json, confidence_score 
                    FROM drummer_style_vectors 
                    WHERE drummer_id = ? 
                    ORDER BY version DESC 
                    LIMIT 1
                """, (source_id,))
                
                row = c.fetchone()
                if row:
                    style_vector_json, confidence = row
                    style_data = json.loads(style_vector_json)
                    
                    # Blend characteristics with weight
                    for key, value in style_data.items():
                        if isinstance(value, (int, float)):
                            if key not in characteristics:
                                characteristics[key] = 0.0
                            characteristics[key] += value * weight
                else:
                    # Fallback to basic profile data if no style vector yet
                    logger.warning(f"No style vector for {source_id}, using fallback")
                    characteristics = self._get_fallback_characteristics(source_id)
            
            conn.close()
            
            # Add metadata
            characteristics["_metadata"] = {
                "drummer_id": drummer_id,
                "display_name": drummer_def["display_name"],
                "source_drummers": source_drummers,
                "blend_weights": blend_weights
            }
            
            return characteristics
            
        except Exception as e:
            logger.error(f"Error loading characteristics for {drummer_id}: {e}")
            return self._get_fallback_characteristics(source_drummers[0])
    
    def _get_fallback_characteristics(self, drummer_id: str) -> Dict[str, float]:
        """
        Fallback characteristics based on basic profile data
        Used when admin database doesn't have full analysis yet
        """
        # Load from profiles.json
        profiles_path = Path(__file__).parent / "admin" / "data" / "drummers" / "profiles.json"
        
        try:
            with open(profiles_path, 'r') as f:
                profiles_data = json.load(f)
            
            for profile in profiles_data.get("profiles", []):
                if profile["id"] == drummer_id:
                    # Map profile data to basic characteristics
                    styles = profile.get("styles", [])
                    techniques = profile.get("techniques", [])
                    
                    # Infer characteristics from styles and techniques
                    characteristics = {
                        "ghost_note_density": 0.5,
                        "ride_preference": 0.5,
                        "kick_syncopation": 0.5,
                        "snare_backbeat_strength": 0.8,
                        "fill_frequency": 0.3,
                        "swing_comfort": 0.5,
                        "technical_precision": 0.7,
                        "dynamics_range": 0.7,
                        "groove_pocket": 0.7,
                    }
                    
                    # Adjust based on styles
                    if "Jazz" in styles or "Fusion" in styles:
                        characteristics["swing_comfort"] = 0.9
                        characteristics["ride_preference"] = 0.9
                        characteristics["ghost_note_density"] = 0.8
                    
                    if "Metal" in " ".join(styles):
                        characteristics["technical_precision"] = 0.95
                        characteristics["kick_syncopation"] = 0.9
                        characteristics["swing_comfort"] = 0.2
                    
                    if "Funk" in " ".join(styles):
                        characteristics["groove_pocket"] = 0.95
                        characteristics["ghost_note_density"] = 0.85
                    
                    # Adjust based on techniques
                    if "Ghost notes" in techniques:
                        characteristics["ghost_note_density"] = 0.8
                    if "Double bass" in techniques:
                        characteristics["kick_syncopation"] = 0.9
                    if "Polyrhythms" in techniques:
                        characteristics["technical_precision"] = 0.95
                    
                    return characteristics
        
        except Exception as e:
            logger.error(f"Error loading fallback for {drummer_id}: {e}")
        
        # Ultimate fallback
        return {
            "ghost_note_density": 0.5,
            "ride_preference": 0.5,
            "kick_syncopation": 0.5,
            "snare_backbeat_strength": 0.8,
            "fill_frequency": 0.3,
            "swing_comfort": 0.5,
            "technical_precision": 0.7,
            "dynamics_range": 0.7,
            "groove_pocket": 0.7,
        }
    
    def map_to_rust_style(self, drummer_id: str) -> str:
        """
        Map DrumTrackAI drummer to Rust Style enum
        Returns: "rock", "funk", "edm", "hiphop", "jazz", "pop"
        """
        if drummer_id not in DRUMTRACKAI_DRUMMERS:
            return "rock"  # Default
        
        drummer_def = DRUMTRACKAI_DRUMMERS[drummer_id]
        genres = drummer_def["genre_tags"]
        
        # Map genre tags to Rust styles
        if any(g in ["Jazz", "Jazz Fusion", "Bebop", "Fusion"] for g in genres):
            return "jazz"
        elif any(g in ["Funk", "Soul", "Gospel"] for g in genres):
            return "funk"
        elif any(g in ["Hip-Hop", "Neo-Soul", "R&B"] for g in genres):
            return "hiphop"
        elif any(g in ["EDM", "Electronic", "Dance"] for g in genres):
            return "edm"
        elif any(g in ["Pop", "Session Work"] for g in genres):
            return "pop"
        else:
            return "rock"
    
    def get_generation_parameters(self, drummer_id: str, song_analysis: Dict = None) -> Dict[str, Any]:
        """
        Get generation parameters for Rust generator
        Combines drummer characteristics with song analysis
        """
        characteristics = self.get_drummer_characteristics(drummer_id)
        if not characteristics:
            characteristics = {}
        
        # Base parameters from drummer
        params = {
            "style": self.map_to_rust_style(drummer_id),
            "swing_preset": self._map_swing_preset(characteristics.get("swing_comfort", 0.5)),
            "vel_preset": self._map_velocity_preset(drummer_id),
            "fill_preset": self._map_fill_preset(drummer_id),
            "density": characteristics.get("ghost_note_density", 0.5),
            "humanize": 1.0 - characteristics.get("technical_precision", 0.7),
        }
        
        # Adjust with song analysis if provided
        if song_analysis:
            # If song has swing, match it
            if "swing_amount" in song_analysis:
                params["swing"] = song_analysis["swing_amount"]
            
            # Match density to song
            if "note_density" in song_analysis:
                song_density = song_analysis["note_density"]
                if song_density == "sparse":
                    params["density"] *= 0.7
                elif song_density == "dense":
                    params["density"] *= 1.3
        
        return params
    
    def _map_swing_preset(self, swing_comfort: float) -> str:
        """Map swing comfort to Rust SwingPreset"""
        if swing_comfort > 0.8:
            return "heavy"
        elif swing_comfort > 0.5:
            return "light"
        else:
            return "off"
    
    def _map_velocity_preset(self, drummer_id: str) -> str:
        """Map drummer to Rust VelPreset"""
        drummer_def = DRUMTRACKAI_DRUMMERS.get(drummer_id, {})
        genres = drummer_def.get("genre_tags", [])
        
        if "Funk" in genres:
            return "funk16"
        else:
            return "accent24"
    
    def _map_fill_preset(self, drummer_id: str) -> str:
        """Map drummer to Rust FillPreset"""
        drummer_def = DRUMTRACKAI_DRUMMERS.get(drummer_id, {})
        techniques = drummer_def.get("signature_techniques", [])
        
        if "Linear fills" in techniques:
            return "tomrun"
        else:
            return "random"


# Singleton instance
_drummer_service = None

def get_drummer_service() -> DrummerMappingService:
    """Get singleton drummer mapping service"""
    global _drummer_service
    if _drummer_service is None:
        _drummer_service = DrummerMappingService()
    return _drummer_service
