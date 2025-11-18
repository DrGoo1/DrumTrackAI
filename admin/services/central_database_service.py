"""
Central Database Service
=======================
Provides centralized database access for DrumBeats and other database operations.
Handles SQLite connection, CRUD operations, and connection pooling.
"""
import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

class CentralDatabaseService(QObject):
    """
    Central database service for DrumTracKAI.
    Provides thread-safe database access and CRUD operations.
    """
    # Define signals for database operations
    database_connected = Signal(str)  # db_path
    database_error = Signal(str)  # error_message
    data_changed = Signal(str, str)  # table_name, operation (insert, update, delete)

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        super().__init__()
        self._db_path = None
        self._connection = None
        self._connections = {}  # Thread-local connections
        self._initialized = False
        self._tables_created = False
        logger.info("CentralDatabaseService initialized")

    @classmethod
    def get_instance(cls):
        """Get the singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, db_path: str = None) -> bool:
        """
        Initialize the database with the given path or default location.
        
        Args:
            db_path: Path to SQLite database. If None, uses default path.
            
        Returns:
            bool: True if successful
        """
        try:
            if self._initialized:
                logger.warning("Database already initialized")
                return True
                
            # Set default path if not provided
            if db_path is None:
                # Use user's home directory
                home = Path.home()
                db_dir = home / "DrumTracKAI" / "database"
                db_dir.mkdir(parents=True, exist_ok=True)
                db_path = str(db_dir / "drum_tracks.db")
                
            logger.info(f"Initializing database at: {db_path}")
            self._db_path = db_path
            
            # Create initial connection
            self._get_connection()
            
            # Create tables if they don't exist
            self._create_tables()
            
            self._initialized = True
            self.database_connected.emit(db_path)
            logger.info(f"Database initialized successfully at {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            self.database_error.emit(f"Failed to initialize database: {str(e)}")
            return False

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a thread-local database connection.
        
        Returns:
            sqlite3.Connection: SQLite connection object
        """
        thread_id = threading.get_ident()
        if thread_id not in self._connections or self._connections[thread_id] is None:
            if self._db_path is None:
                raise ValueError("Database path not set. Call initialize() first.")
                
            conn = sqlite3.connect(self._db_path)
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            # Configure for dictionary results
            conn.row_factory = sqlite3.Row
            self._connections[thread_id] = conn
            
        return self._connections[thread_id]

    def _create_tables(self) -> None:
        """Create database tables if they don't exist"""
        if self._tables_created:
            return
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create drummers table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS drummers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')
            
            # Create songs table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                artist TEXT,
                album TEXT,
                year INTEGER,
                genre TEXT,
                duration REAL,
                file_path TEXT,
                drummer_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (drummer_id) REFERENCES drummers(id) ON DELETE CASCADE
            )
            ''')
            
            # Create drum_beats table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS drum_beats (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                file_path TEXT,
                song_id TEXT,
                drummer_id TEXT,
                bpm REAL,
                time_signature TEXT,
                complexity REAL,
                energy REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
                FOREIGN KEY (drummer_id) REFERENCES drummers(id) ON DELETE CASCADE
            )
            ''')
            
            # Create processing_metadata table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_metadata (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                process_type TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata TEXT,  -- JSON string
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')
            
            conn.commit()
            self._tables_created = True
            logger.info("Database tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            self.database_error.emit(f"Failed to create database tables: {str(e)}")
            raise

    # CRUD operations for drummers
    def get_drummers(self) -> List[Dict]:
        """
        Get all drummers from the database.
        
        Returns:
            List[Dict]: List of drummer records
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM drummers ORDER BY name')
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting drummers: {str(e)}")
            self.database_error.emit(f"Error getting drummers: {str(e)}")
            return []

    def get_drummer(self, drummer_id: str) -> Optional[Dict]:
        """
        Get a drummer by ID.
        
        Args:
            drummer_id: The ID of the drummer
            
        Returns:
            Dict or None: Drummer record or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM drummers WHERE id = ?', (drummer_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting drummer {drummer_id}: {str(e)}")
            self.database_error.emit(f"Error getting drummer: {str(e)}")
            return None

    def add_drummer(self, name: str, description: str = "") -> Optional[str]:
        """
        Add a new drummer to the database.
        
        Args:
            name: The name of the drummer
            description: Optional description
            
        Returns:
            str or None: The ID of the new drummer or None if failed
        """
        try:
            drummer_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO drummers (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
                (drummer_id, name, description, now, now)
            )
            conn.commit()
            
            self.data_changed.emit('drummers', 'insert')
            logger.info(f"Added new drummer: {name} (ID: {drummer_id})")
            return drummer_id
            
        except Exception as e:
            logger.error(f"Error adding drummer {name}: {str(e)}")
            self.database_error.emit(f"Error adding drummer: {str(e)}")
            return None

    def update_drummer(self, drummer_id: str, data: Dict) -> bool:
        """
        Update a drummer's information.
        
        Args:
            drummer_id: The ID of the drummer to update
            data: Dictionary with fields to update
            
        Returns:
            bool: True if successful
        """
        try:
            # Filter out invalid fields
            valid_fields = {'name', 'description'}
            update_data = {k: v for k, v in data.items() if k in valid_fields}
            
            if not update_data:
                logger.warning("No valid fields to update for drummer")
                return False
                
            # Add updated_at timestamp
            update_data['updated_at'] = datetime.now().isoformat()
            
            # Build the SQL query
            field_str = ', '.join([f"{field} = ?" for field in update_data.keys()])
            values = list(update_data.values()) + [drummer_id]
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f"UPDATE drummers SET {field_str} WHERE id = ?", values)
            conn.commit()
            
            self.data_changed.emit('drummers', 'update')
            logger.info(f"Updated drummer ID: {drummer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating drummer {drummer_id}: {str(e)}")
            self.database_error.emit(f"Error updating drummer: {str(e)}")
            return False

    def delete_drummer(self, drummer_id: str) -> bool:
        """
        Delete a drummer from the database.
        
        Args:
            drummer_id: The ID of the drummer to delete
            
        Returns:
            bool: True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM drummers WHERE id = ?', (drummer_id,))
            conn.commit()
            
            self.data_changed.emit('drummers', 'delete')
            logger.info(f"Deleted drummer ID: {drummer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting drummer {drummer_id}: {str(e)}")
            self.database_error.emit(f"Error deleting drummer: {str(e)}")
            return False

    # CRUD operations for songs
    def get_songs(self, drummer_id: Optional[str] = None) -> List[Dict]:
        """
        Get songs from the database, optionally filtered by drummer.
        
        Args:
            drummer_id: Optional drummer ID to filter by
            
        Returns:
            List[Dict]: List of song records
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if drummer_id:
                cursor.execute('SELECT * FROM songs WHERE drummer_id = ? ORDER BY title', (drummer_id,))
            else:
                cursor.execute('SELECT * FROM songs ORDER BY title')
                
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting songs: {str(e)}")
            self.database_error.emit(f"Error getting songs: {str(e)}")
            return []

    def get_song(self, song_id: str) -> Optional[Dict]:
        """
        Get a song by ID.
        
        Args:
            song_id: The ID of the song
            
        Returns:
            Dict or None: Song record or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM songs WHERE id = ?', (song_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Error getting song {song_id}: {str(e)}")
            self.database_error.emit(f"Error getting song: {str(e)}")
            return None

    def add_song(self, title: str, file_path: str = None, drummer_id: str = None, metadata: Dict = None) -> Optional[str]:
        """
        Add a new song to the database.
        
        Args:
            title: The title of the song
            file_path: Path to the audio file
            drummer_id: Optional ID of the associated drummer
            metadata: Optional additional metadata (artist, album, etc.)
            
        Returns:
            str or None: The ID of the new song or None if failed
        """
        try:
            song_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Extract metadata if provided
            if metadata is None:
                metadata = {}
                
            artist = metadata.get('artist', '')
            album = metadata.get('album', '')
            year = metadata.get('year', None)
            genre = metadata.get('genre', '')
            duration = metadata.get('duration', None)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO songs 
                   (id, title, artist, album, year, genre, duration, file_path, drummer_id, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (song_id, title, artist, album, year, genre, duration, file_path, drummer_id, now, now)
            )
            conn.commit()
            
            self.data_changed.emit('songs', 'insert')
            logger.info(f"Added new song: {title} (ID: {song_id})")
            return song_id
            
        except Exception as e:
            logger.error(f"Error adding song {title}: {str(e)}")
            self.database_error.emit(f"Error adding song: {str(e)}")
            return None

    # CRUD operations for drum beats
    def get_drum_beats(self, drummer_id: Optional[str] = None, song_id: Optional[str] = None) -> List[Dict]:
        """
        Get drum beats from the database, optionally filtered by drummer or song.
        
        Args:
            drummer_id: Optional drummer ID to filter by
            song_id: Optional song ID to filter by
            
        Returns:
            List[Dict]: List of drum beat records
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = 'SELECT * FROM drum_beats'
            params = []
            
            if drummer_id and song_id:
                query += ' WHERE drummer_id = ? AND song_id = ?'
                params = [drummer_id, song_id]
            elif drummer_id:
                query += ' WHERE drummer_id = ?'
                params = [drummer_id]
            elif song_id:
                query += ' WHERE song_id = ?'
                params = [song_id]
                
            query += ' ORDER BY name'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting drum beats: {str(e)}")
            self.database_error.emit(f"Error getting drum beats: {str(e)}")
            return []

    def get_drum_beat(self, beat_id: str) -> Optional[Dict]:
        """
        Get a drum beat by ID.
        
        Args:
            beat_id: The ID of the drum beat
            
        Returns:
            Dict or None: Drum beat record or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM drum_beats WHERE id = ?', (beat_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Error getting drum beat {beat_id}: {str(e)}")
            self.database_error.emit(f"Error getting drum beat: {str(e)}")
            return None

    def add_drum_beat(self, name: str, file_path: str = None, drummer_id: str = None, song_id: str = None, metadata: Dict = None) -> Optional[str]:
        """
        Add a new drum beat to the database.
        
        Args:
            name: The name of the drum beat
            file_path: Path to the audio file
            drummer_id: Optional ID of the associated drummer
            song_id: Optional ID of the associated song
            metadata: Optional additional metadata (bpm, complexity, etc.)
            
        Returns:
            str or None: The ID of the new drum beat or None if failed
        """
        try:
            beat_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Extract metadata if provided
            if metadata is None:
                metadata = {}
                
            description = metadata.get('description', '')
            bpm = metadata.get('bpm', None)
            time_signature = metadata.get('time_signature', '')
            complexity = metadata.get('complexity', None)
            energy = metadata.get('energy', None)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO drum_beats 
                   (id, name, description, file_path, song_id, drummer_id, bpm, time_signature, complexity, energy, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (beat_id, name, description, file_path, song_id, drummer_id, bpm, time_signature, complexity, energy, now, now)
            )
            conn.commit()
            
            self.data_changed.emit('drum_beats', 'insert')
            logger.info(f"Added new drum beat: {name} (ID: {beat_id})")
            return beat_id
            
        except Exception as e:
            logger.error(f"Error adding drum beat {name}: {str(e)}")
            self.database_error.emit(f"Error adding drum beat: {str(e)}")
            return None
            
    # Function to get the singleton instance
    @staticmethod
    def get_database():
        """Get the singleton database instance"""
        return CentralDatabaseService.get_instance()

# Singleton access function
def get_database_service() -> CentralDatabaseService:
    """Get the singleton database service instance"""
    return CentralDatabaseService.get_instance()
