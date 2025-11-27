"""
Drummer Profile Maturity System
Tracks songs analyzed, confidence scores, and profile completeness
"""

import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class ProfileMaturityTracker:
    """Track and calculate drummer profile maturity"""
    
    def __init__(self, db_path: str = "f:/DrumTracKAI_v1.1.16_Clean/admin/drumtrackai.db"):
        self.db_path = db_path
        self.ensure_tables()
    
    def ensure_tables(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drummer_profiles (
                drummer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                styles TEXT,
                era TEXT,
                category TEXT,
                drummer_number INTEGER,
                display_name TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Style vectors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drummer_style_vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drummer_id TEXT NOT NULL,
                style_vector_json TEXT NOT NULL,
                confidence_score REAL DEFAULT 0.0,
                version INTEGER DEFAULT 1,
                created_at TEXT,
                FOREIGN KEY (drummer_id) REFERENCES drummer_profiles(drummer_id)
            )
        """)
        
        # Songs analyzed table (NEW)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drummer_analyzed_songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drummer_id TEXT NOT NULL,
                song_title TEXT NOT NULL,
                artist TEXT,
                youtube_url TEXT,
                tempo_bpm REAL,
                duration_seconds REAL,
                pattern_count INTEGER,
                analysis_quality REAL DEFAULT 0.0,
                analyzed_at TEXT,
                notes TEXT,
                FOREIGN KEY (drummer_id) REFERENCES drummer_profiles(drummer_id)
            )
        """)
        
        # Profile maturity metrics table (NEW)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drummer_profile_metrics (
                drummer_id TEXT PRIMARY KEY,
                songs_analyzed INTEGER DEFAULT 0,
                total_patterns INTEGER DEFAULT 0,
                avg_confidence REAL DEFAULT 0.0,
                maturity_score REAL DEFAULT 0.0,
                maturity_level TEXT DEFAULT 'emerging',
                last_updated TEXT,
                FOREIGN KEY (drummer_id) REFERENCES drummer_profiles(drummer_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_analyzed_song(self, drummer_id: str, song_data: Dict) -> bool:
        """Add a song to the analyzed songs list"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO drummer_analyzed_songs
                (drummer_id, song_title, artist, youtube_url, tempo_bpm, 
                 duration_seconds, pattern_count, analysis_quality, analyzed_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                drummer_id,
                song_data.get('title', 'Unknown'),
                song_data.get('artist', ''),
                song_data.get('youtube_url', ''),
                song_data.get('tempo_bpm', 0.0),
                song_data.get('duration_seconds', 0.0),
                song_data.get('pattern_count', 0),
                song_data.get('quality', 0.8),
                datetime.now().isoformat(),
                song_data.get('notes', '')
            ))
            
            conn.commit()
            
            # Update metrics
            self.update_maturity_metrics(drummer_id)
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error adding song: {e}")
            conn.close()
            return False
    
    def get_analyzed_songs(self, drummer_id: str) -> List[Dict]:
        """Get list of songs analyzed for a drummer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT song_title, artist, youtube_url, tempo_bpm, 
                   duration_seconds, pattern_count, analysis_quality, analyzed_at, notes
            FROM drummer_analyzed_songs
            WHERE drummer_id = ?
            ORDER BY analyzed_at DESC
        """, (drummer_id,))
        
        songs = []
        for row in cursor.fetchall():
            songs.append({
                'title': row[0],
                'artist': row[1],
                'youtube_url': row[2],
                'tempo_bpm': row[3],
                'duration_seconds': row[4],
                'pattern_count': row[5],
                'quality': row[6],
                'analyzed_at': row[7],
                'notes': row[8]
            })
        
        conn.close()
        return songs
    
    def calculate_maturity_score(self, drummer_id: str) -> float:
        """
        Calculate maturity score (0.0 to 1.0)
        
        Factors:
        - Number of songs analyzed (0-10 = 0.0-0.4)
        - Total patterns extracted (0-1000 = 0.0-0.3)
        - Average confidence (0.0-0.3)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get song count
        cursor.execute("""
            SELECT COUNT(*) FROM drummer_analyzed_songs WHERE drummer_id = ?
        """, (drummer_id,))
        song_count = cursor.fetchone()[0]
        
        # Get total patterns
        cursor.execute("""
            SELECT SUM(pattern_count) FROM drummer_analyzed_songs WHERE drummer_id = ?
        """, (drummer_id,))
        result = cursor.fetchone()[0]
        total_patterns = result if result else 0
        
        # Get average confidence
        cursor.execute("""
            SELECT AVG(confidence_score) FROM drummer_style_vectors WHERE drummer_id = ?
        """, (drummer_id,))
        result = cursor.fetchone()[0]
        avg_confidence = result if result else 0.0
        
        conn.close()
        
        # Calculate components (max 1.0)
        song_score = min(song_count / 10.0, 1.0) * 0.4  # 40% weight
        pattern_score = min(total_patterns / 1000.0, 1.0) * 0.3  # 30% weight
        confidence_score = avg_confidence * 0.3  # 30% weight
        
        total_score = song_score + pattern_score + confidence_score
        
        return round(total_score, 3)
    
    def get_maturity_level(self, score: float) -> str:
        """Convert score to maturity level"""
        if score >= 0.8:
            return "mature"
        elif score >= 0.6:
            return "developing"
        elif score >= 0.3:
            return "emerging"
        else:
            return "initial"
    
    def update_maturity_metrics(self, drummer_id: str):
        """Update all maturity metrics for a drummer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute("""
            SELECT COUNT(*), SUM(pattern_count)
            FROM drummer_analyzed_songs
            WHERE drummer_id = ?
        """, (drummer_id,))
        row = cursor.fetchone()
        song_count = row[0]
        total_patterns = row[1] if row[1] else 0
        
        # Get avg confidence
        cursor.execute("""
            SELECT AVG(confidence_score)
            FROM drummer_style_vectors
            WHERE drummer_id = ?
        """, (drummer_id,))
        result = cursor.fetchone()[0]
        avg_confidence = result if result else 0.0
        
        # Calculate maturity
        maturity_score = self.calculate_maturity_score(drummer_id)
        maturity_level = self.get_maturity_level(maturity_score)
        
        # Update or insert metrics
        cursor.execute("""
            INSERT OR REPLACE INTO drummer_profile_metrics
            (drummer_id, songs_analyzed, total_patterns, avg_confidence, 
             maturity_score, maturity_level, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            drummer_id,
            song_count,
            total_patterns,
            avg_confidence,
            maturity_score,
            maturity_level,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_profile_maturity(self, drummer_id: str) -> Dict:
        """Get complete maturity info for a drummer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get metrics
        cursor.execute("""
            SELECT songs_analyzed, total_patterns, avg_confidence, 
                   maturity_score, maturity_level, last_updated
            FROM drummer_profile_metrics
            WHERE drummer_id = ?
        """, (drummer_id,))
        
        row = cursor.fetchone()
        
        if not row:
            # No metrics yet, return defaults
            return {
                'drummer_id': drummer_id,
                'songs_analyzed': 0,
                'total_patterns': 0,
                'avg_confidence': 0.0,
                'maturity_score': 0.0,
                'maturity_level': 'initial',
                'maturity_percentage': 0,
                'songs': [],
                'recommendations': self._get_recommendations(0, 0, 0.0)
            }
        
        # Get song list
        songs = self.get_analyzed_songs(drummer_id)
        
        conn.close()
        
        return {
            'drummer_id': drummer_id,
            'songs_analyzed': row[0],
            'total_patterns': row[1],
            'avg_confidence': round(row[2], 3),
            'maturity_score': row[3],
            'maturity_level': row[4],
            'maturity_percentage': int(row[3] * 100),
            'last_updated': row[5],
            'songs': songs,
            'recommendations': self._get_recommendations(row[0], row[1], row[3])
        }
    
    def _get_recommendations(self, song_count: int, pattern_count: int, score: float) -> List[str]:
        """Get recommendations for improving profile maturity"""
        recommendations = []
        
        if song_count < 3:
            recommendations.append(f"Add {3 - song_count} more signature songs for better coverage")
        elif song_count < 5:
            recommendations.append(f"Add {5 - song_count} more songs to reach 'developing' status")
        elif song_count < 10:
            recommendations.append(f"Add {10 - song_count} more songs for comprehensive coverage")
        
        if pattern_count < 100:
            recommendations.append("Need more pattern diversity - aim for 100+ patterns")
        elif pattern_count < 500:
            recommendations.append("Good diversity - 500+ patterns recommended for 'mature' status")
        
        if score < 0.3:
            recommendations.append("Profile is in initial stage - analyze more songs")
        elif score < 0.6:
            recommendations.append("Profile emerging - add variety of tempos and styles")
        elif score < 0.8:
            recommendations.append("Profile developing well - continue adding diverse material")
        else:
            recommendations.append("Profile mature - ready for production use!")
        
        return recommendations
    
    def get_all_maturity_stats(self) -> List[Dict]:
        """Get maturity stats for all drummers"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.drummer_id, p.name, m.songs_analyzed, m.total_patterns,
                   m.maturity_score, m.maturity_level
            FROM drummer_profiles p
            LEFT JOIN drummer_profile_metrics m ON p.drummer_id = m.drummer_id
            ORDER BY m.maturity_score DESC
        """)
        
        stats = []
        for row in cursor.fetchall():
            stats.append({
                'drummer_id': row[0],
                'name': row[1],
                'songs_analyzed': row[2] if row[2] else 0,
                'total_patterns': row[3] if row[3] else 0,
                'maturity_score': row[4] if row[4] else 0.0,
                'maturity_level': row[5] if row[5] else 'initial',
                'maturity_percentage': int((row[4] if row[4] else 0.0) * 100)
            })
        
        conn.close()
        return stats


# Helper functions
def get_maturity_tracker() -> ProfileMaturityTracker:
    """Get singleton maturity tracker"""
    return ProfileMaturityTracker()


def get_maturity_badge(level: str) -> str:
    """Get emoji badge for maturity level"""
    badges = {
        'initial': '🌱',     # Seedling
        'emerging': '🌿',    # Herb
        'developing': '🌳',  # Tree
        'mature': '🏆'       # Trophy
    }
    return badges.get(level, '❓')


def get_maturity_color(level: str) -> str:
    """Get color code for maturity level"""
    colors = {
        'initial': '#9CA3AF',      # Gray
        'emerging': '#F59E0B',     # Amber
        'developing': '#3B82F6',   # Blue
        'mature': '#10B981'        # Green
    }
    return colors.get(level, '#6B7280')
