"""
DrumTracKAI Category-Based Drummer System
Maps 12 real drummers into 7 fictional categories with numbered profiles
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# 7 Main Categories with Individual Drummers
DRUMMER_CATEGORIES = {
    "studio_session_masters": {
        "id": "studio_session_masters",
        "display_name": "Studio Session Masters",
        "icon": "🎩",
        "color": "#4F46E5",
        "tagline": "Precision pocket players with legendary studio chops",
        "description": "Masters of versatility and sophistication. Perfect for session work, jazz fusion, and knowing exactly what the song needs.",
        "genre_tags": ["Jazz Fusion", "Pop", "Rock", "Session Work"],
        "difficulty": "Advanced",
        "drummers": [
            {
                "id": "studio_session_1",
                "display_name": "Drummer #1",
                "description": "Legendary pocket player with sophisticated ghost notes and half-time shuffle mastery",
                "source_drummer": "jeff_porcaro",
                "best_for": ["Steely Dan style", "Toto grooves", "Jazz fusion", "Sophisticated pop"],
                "signature_techniques": ["Half-time shuffle", "Ghost note mastery", "Ride cymbal work", "Linear fills"],
                "difficulty": "Advanced"
            }
            # Future: studio_session_2 (steve_gadd), studio_session_3 (vinnie_colaiuta)
        ]
    },
    
    "progressive_masters": {
        "id": "progressive_masters",
        "display_name": "Progressive Masters",
        "icon": "🎼",
        "color": "#7C3AED",
        "tagline": "Complex rhythms and orchestral arrangements",
        "description": "Masters of odd time signatures and mathematical precision. Orchestral approach to drumming with technical mastery.",
        "genre_tags": ["Progressive Rock", "Progressive Metal", "Math Rock", "Technical Music"],
        "difficulty": "Expert",
        "drummers": [
            {
                "id": "progressive_1",
                "display_name": "Drummer #1",
                "description": "Precision-focused progressive metal mastery with double bass expertise and orchestral approach",
                "source_drummer": "mike_portnoy",
                "best_for": ["Dream Theater style", "Technical prog metal", "Complex arrangements", "Odd time signatures"],
                "signature_techniques": ["Odd time signatures", "Double bass precision", "Orchestral approach", "Technical fills"],
                "difficulty": "Expert"
            },
            {
                "id": "progressive_2",
                "display_name": "Drummer #2",
                "description": "Tribal polyrhythmic approach with dynamic swells and unconventional patterns",
                "source_drummer": "danny_carey",
                "best_for": ["Tool style", "Polyrhythmic grooves", "7/8 and 5/4 time", "Tribal feels"],
                "signature_techniques": ["Polyrhythms", "Tribal feel", "Dynamic swells", "Unconventional patterns"],
                "difficulty": "Expert"
            }
        ]
    },
    
    "metal_precision_masters": {
        "id": "metal_precision_masters",
        "display_name": "Metal Precision Masters",
        "icon": "⚡",
        "color": "#DC2626",
        "tagline": "Extreme precision and technical metal mastery",
        "description": "Inhuman precision meets extreme metal intensity. Masters of speed, double bass, and technical complexity.",
        "genre_tags": ["Death Metal", "Thrash Metal", "Nu Metal", "Technical Metal", "Extreme Metal"],
        "difficulty": "Expert",
        "drummers": [
            {
                "id": "metal_precision_1",
                "display_name": "Drummer #1",
                "description": "Atomic clock precision with blast beat mastery and double bass perfection",
                "source_drummer": "gene_hoglan",
                "best_for": ["Death metal", "Thrash metal", "Technical metal", "Extreme tempos"],
                "signature_techniques": ["Blast beats", "Double bass precision", "Extreme speed", "Complex fills"],
                "difficulty": "Expert"
            },
            {
                "id": "metal_chaos_1",
                "display_name": "Drummer #2",
                "description": "Tribal intensity meets industrial aggression with lightning-fast double bass",
                "source_drummer": "joey_jordison",
                "best_for": ["Slipknot style", "Nu metal", "Industrial metal", "Aggressive styles"],
                "signature_techniques": ["Fast double bass", "Tribal rhythms", "Percussive elements", "Unconventional patterns"],
                "difficulty": "Advanced"
            }
        ]
    },
    
    "funk_soul_masters": {
        "id": "funk_soul_masters",
        "display_name": "Funk & Soul Masters",
        "icon": "🕺",
        "color": "#F59E0B",
        "tagline": "Infectious grooves and pocket supremacy",
        "description": "Deep pocket masters who make people move. Gospel chops, funk foundation, and knowing when NOT to play.",
        "genre_tags": ["Funk", "R&B", "Soul", "Gospel", "Neo-Soul"],
        "difficulty": "Advanced",
        "drummers": [
            {
                "id": "funk_soul_1",
                "display_name": "Drummer #1",
                "description": "Lightning-fast singles with deep groove foundation and gospel mastery",
                "source_drummer": "dennis_chambers",
                "best_for": ["P-Funk style", "Gospel", "Neo-soul", "Fusion funk"],
                "signature_techniques": ["Funk grooves", "Gospel chops", "Linear fills", "Pocket mastery"],
                "difficulty": "Advanced"
            }
            # Future: funk_soul_2 (clyde_stubblefield), funk_soul_3 (bernard_purdie)
        ]
    },
    
    "jazz_innovators": {
        "id": "jazz_innovators",
        "display_name": "Jazz Innovators",
        "icon": "🎷",
        "color": "#10B981",
        "tagline": "Polyrhythmic pioneers and conversational players",
        "description": "Conversational and interactive masters. The drums sing and respond to other musicians with polyrhythmic complexity.",
        "genre_tags": ["Jazz", "Bebop", "Fusion", "Avant-garde", "Free Jazz"],
        "difficulty": "Expert",
        "drummers": [
            {
                "id": "jazz_1",
                "display_name": "Drummer #1",
                "description": "Polyrhythmic mastery with rolling triplets and dynamic intensity",
                "source_drummer": "elvin_jones",
                "best_for": ["Bebop", "Free jazz", "Classic jazz", "Polyrhythmic playing"],
                "signature_techniques": ["Polyrhythmic playing", "Rolling triplets", "Dynamic swells", "Independence"],
                "difficulty": "Expert"
            },
            {
                "id": "jazz_2",
                "display_name": "Drummer #2",
                "description": "Interactive fusion pioneer with innovative ride cymbal work and dynamic control",
                "source_drummer": "tony_williams",
                "best_for": ["Jazz fusion", "Miles Davis style", "Interactive playing", "Free time"],
                "signature_techniques": ["Ride mastery", "Interactive listening", "Dynamic swells", "Free time feel"],
                "difficulty": "Expert"
            }
        ]
    },
    
    "rock_powerhouses": {
        "id": "rock_powerhouses",
        "display_name": "Rock Powerhouses",
        "icon": "🔨",
        "color": "#EF4444",
        "tagline": "Raw energy and thunderous grooves",
        "description": "Power with pocket. Making every hit count with raw energy, groove mastery, and thunderous dynamics.",
        "genre_tags": ["Rock", "Hard Rock", "Alternative Rock", "Grunge", "Blues Rock"],
        "difficulty": "Intermediate",
        "drummers": [
            {
                "id": "rock_power_1",
                "display_name": "Drummer #1",
                "description": "Thunderous single bass drum virtuosity with triplet mastery and massive dynamics",
                "source_drummer": "john_bonham",
                "best_for": ["Led Zeppelin style", "Classic rock", "Blues rock", "Heavy grooves"],
                "signature_techniques": ["Triplet patterns", "Heavy foot technique", "Huge dynamics", "Groove-oriented"],
                "difficulty": "Intermediate"
            },
            {
                "id": "rock_alt_1",
                "display_name": "Drummer #2",
                "description": "Simple effectiveness with raw power and primal energy",
                "source_drummer": "dave_grohl",
                "best_for": ["Nirvana style", "Grunge", "Alternative rock", "Punk energy"],
                "signature_techniques": ["Power playing", "Simple effectiveness", "Raw energy", "Song-first approach"],
                "difficulty": "Intermediate"
            }
        ]
    },
    
    "world_fusion_hiphop": {
        "id": "world_fusion_hiphop",
        "display_name": "World Fusion & Hip-Hop",
        "icon": "🌍",
        "color": "#14B8A6",
        "tagline": "Global rhythms meet modern styles",
        "description": "World influences, reggae grooves, and hip-hop foundation. Minimalism with maximum impact and global perspective.",
        "genre_tags": ["World Music", "Reggae", "Hip-Hop", "Neo-Soul", "New Wave"],
        "difficulty": "Advanced",
        "drummers": [
            {
                "id": "world_fusion_1",
                "display_name": "Drummer #1",
                "description": "Reggae and world music fusion with hi-hat mastery and linear patterns",
                "source_drummer": "stewart_copeland",
                "best_for": ["Police style", "Reggae rock", "New wave", "World fusion"],
                "signature_techniques": ["Reggae influences", "Hi-hat mastery", "Splash cymbals", "Linear patterns"],
                "difficulty": "Advanced"
            },
            {
                "id": "hiphop_1",
                "display_name": "Drummer #2",
                "description": "The human MPC with minimalist pocket and sample-based playing mastery",
                "source_drummer": "questlove",
                "best_for": ["Roots style", "Neo-soul", "Boom-bap", "Live hip-hop"],
                "signature_techniques": ["Sample-based playing", "Pocket mastery", "Minimalist approach", "Human MPC"],
                "difficulty": "Advanced"
            }
            # Future: world_fusion_2 (phil_collins for pop/gated reverb)
        ]
    }
}


class DrummerCategoryService:
    """Service for category-based drummer organization"""
    
    def __init__(self):
        logger.info("DrummerCategoryService initialized")
    
    def list_categories(self) -> List[Dict]:
        """Get list of all drummer categories"""
        categories = []
        for category_id, category_data in DRUMMER_CATEGORIES.items():
            categories.append({
                "id": category_data["id"],
                "display_name": category_data["display_name"],
                "icon": category_data["icon"],
                "color": category_data["color"],
                "tagline": category_data["tagline"],
                "description": category_data["description"],
                "genre_tags": category_data["genre_tags"],
                "difficulty": category_data["difficulty"],
                "drummer_count": len(category_data["drummers"])
            })
        return categories
    
    def get_category(self, category_id: str) -> Optional[Dict]:
        """Get specific category details"""
        if category_id not in DRUMMER_CATEGORIES:
            logger.warning(f"Unknown category_id: {category_id}")
            return None
        
        return DRUMMER_CATEGORIES[category_id]
    
    def list_drummers_in_category(self, category_id: str) -> List[Dict]:
        """Get list of drummers in a category"""
        category = self.get_category(category_id)
        if not category:
            return []
        
        # Return drummer list without exposing source_drummer (keep internal)
        drummers = []
        for drummer in category["drummers"]:
            drummers.append({
                "id": drummer["id"],
                "display_name": drummer["display_name"],
                "description": drummer["description"],
                "best_for": drummer["best_for"],
                "signature_techniques": drummer["signature_techniques"],
                "difficulty": drummer["difficulty"]
            })
        
        return drummers
    
    def get_drummer(self, drummer_id: str) -> Optional[Dict]:
        """Get specific drummer details by ID"""
        # Search all categories for this drummer
        for category_id, category_data in DRUMMER_CATEGORIES.items():
            for drummer in category_data["drummers"]:
                if drummer["id"] == drummer_id:
                    return {
                        "id": drummer["id"],
                        "display_name": drummer["display_name"],
                        "description": drummer["description"],
                        "source_drummer": drummer["source_drummer"],  # Internal use only
                        "best_for": drummer["best_for"],
                        "signature_techniques": drummer["signature_techniques"],
                        "difficulty": drummer["difficulty"],
                        "category": {
                            "id": category_id,
                            "display_name": category_data["display_name"],
                            "icon": category_data["icon"]
                        }
                    }
        
        logger.warning(f"Unknown drummer_id: {drummer_id}")
        return None
    
    def get_source_drummer_id(self, drummer_id: str) -> Optional[str]:
        """
        Get the real drummer ID for a DrumTracKAI drummer
        Used internally by AI generator
        """
        drummer = self.get_drummer(drummer_id)
        if drummer:
            return drummer["source_drummer"]
        return None
    
    def list_all_drummers(self) -> List[Dict]:
        """Get flat list of all drummers across all categories"""
        all_drummers = []
        for category_id, category_data in DRUMMER_CATEGORIES.items():
            for drummer in category_data["drummers"]:
                all_drummers.append({
                    "id": drummer["id"],
                    "display_name": drummer["display_name"],
                    "description": drummer["description"],
                    "category_name": category_data["display_name"],
                    "category_icon": category_data["icon"],
                    "difficulty": drummer["difficulty"]
                })
        return all_drummers


# Singleton instance
_category_service = None

def get_category_service() -> DrummerCategoryService:
    """Get singleton category service"""
    global _category_service
    if _category_service is None:
        _category_service = DrummerCategoryService()
    return _category_service
