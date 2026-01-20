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
import json

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
        self._schema_cache: Dict[str, set] = {}
        logger.info("CentralDatabaseService initialized")

    def _table_columns(self, table_name: str) -> set:
        if table_name in self._schema_cache:
            return self._schema_cache[table_name]
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
            cols = {row[1] for row in rows} if rows else set()
            self._schema_cache[table_name] = cols
            return cols
        except Exception:
            self._schema_cache[table_name] = set()
            return set()

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
                # First, honor an explicit environment override so backend
                # services and the admin GUI can share the same canonical DB
                # (e.g. the rich admin/analysis DB at admin/drumtrackai.db).
                env_path = os.getenv("DRUMTRACKAI_DB_PATH")
                if env_path:
                    db_path = env_path
                else:
                    # Prefer project-local DBs when running from a repo checkout.
                    # This prevents the admin UI from silently connecting to a
                    # fresh per-user DB with no drummers/beats.
                    try:
                        project_root = Path(__file__).resolve().parents[2]
                    except Exception:
                        project_root = None

                    candidates: List[Path] = []
                    if project_root:
                        candidates.extend([
                            project_root / "admin" / "drumtrackai.db",
                            project_root / "admin" / "admin" / "drumtrackai.db",
                            project_root / "admin" / "data" / "drum_training.db",
                            project_root / "admin" / "admin" / "data" / "drum_training.db",
                        ])

                    selected = None
                    for candidate in candidates:
                        try:
                            if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0:
                                selected = candidate
                                break
                        except Exception:
                            continue

                    if selected is not None:
                        db_path = str(selected)
                    else:
                        # Fallback to the original per-user location.
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

    def list_drummer_presets(self, profile_type: str) -> List[Dict[str, Any]]:
        try:
            profile_type = (profile_type or "").strip().lower()
            if not profile_type:
                return []

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT preset_id, profile_type, name, tier,
                       deltas_json, policies_json,
                       source_type, source_song_name, source_ref
                FROM drummer_presets
                WHERE profile_type = ?
                ORDER BY tier DESC, name
                """,
                (profile_type,),
            )
            rows = cursor.fetchall()
            out: List[Dict[str, Any]] = []
            for row in rows:
                deltas = {}
                policies = {}
                try:
                    deltas = json.loads(row[4]) if row[4] else {}
                except Exception:
                    deltas = {}
                try:
                    policies = json.loads(row[5]) if row[5] else {}
                except Exception:
                    policies = {}
                out.append(
                    {
                        "preset_id": row[0],
                        "profile_type": row[1],
                        "name": row[2],
                        "tier": row[3],
                        "deltas": deltas,
                        "policies": policies,
                        "source_type": row[6],
                        "source_song_name": row[7],
                        "source_ref": row[8],
                    }
                )
            return out
        except sqlite3.OperationalError as e:
            logger.warning(f"drummer_presets table not available: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing drummer presets: {str(e)}")
            self.database_error.emit(f"Error listing drummer presets: {str(e)}")
            return []

    def get_drummer_preset(self, preset_id: str) -> Optional[Dict[str, Any]]:
        try:
            preset_id = (preset_id or "").strip()
            if not preset_id:
                return None

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT preset_id, profile_type, name, tier,
                       deltas_json, policies_json,
                       source_type, source_song_name, source_ref
                FROM drummer_presets
                WHERE preset_id = ?
                LIMIT 1
                """,
                (preset_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            deltas = {}
            policies = {}
            try:
                deltas = json.loads(row[4]) if row[4] else {}
            except Exception:
                deltas = {}
            try:
                policies = json.loads(row[5]) if row[5] else {}
            except Exception:
                policies = {}

            return {
                "preset_id": row[0],
                "profile_type": row[1],
                "name": row[2],
                "tier": row[3],
                "deltas": deltas,
                "policies": policies,
                "source_type": row[6],
                "source_song_name": row[7],
                "source_ref": row[8],
            }
        except sqlite3.OperationalError as e:
            logger.warning(f"drummer_presets table not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting drummer preset {preset_id}: {str(e)}")
            self.database_error.emit(f"Error getting drummer preset: {str(e)}")
            return None

    def upsert_drummer_preset(
        self,
        preset_id: str,
        profile_type: str,
        name: str,
        tier: str,
        deltas: Optional[Dict[str, Any]] = None,
        policies: Optional[Dict[str, Any]] = None,
        source_type: Optional[str] = None,
        source_song_name: Optional[str] = None,
        source_ref: Optional[str] = None,
    ) -> bool:
        try:
            preset_id = (preset_id or "").strip()
            profile_type = (profile_type or "").strip().lower()
            name = (name or "").strip()
            tier = (tier or "").strip().lower()

            if not preset_id or not profile_type or not name or not tier:
                return False

            deltas_json = json.dumps(deltas or {})
            policies_json = json.dumps(policies or {})

            now = datetime.utcnow().isoformat()
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO drummer_presets (
                    preset_id, profile_type, name, tier,
                    deltas_json, policies_json,
                    source_type, source_song_name, source_ref,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(preset_id) DO UPDATE SET
                    profile_type=excluded.profile_type,
                    name=excluded.name,
                    tier=excluded.tier,
                    deltas_json=excluded.deltas_json,
                    policies_json=excluded.policies_json,
                    source_type=excluded.source_type,
                    source_song_name=excluded.source_song_name,
                    source_ref=excluded.source_ref,
                    updated_at=excluded.updated_at
                """,
                (
                    preset_id,
                    profile_type,
                    name,
                    tier,
                    deltas_json,
                    policies_json,
                    source_type,
                    source_song_name,
                    source_ref,
                    now,
                    now,
                ),
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            logger.warning(f"drummer_presets table not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error upserting drummer preset: {str(e)}")
            self.database_error.emit(f"Error upserting drummer preset: {str(e)}")
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
            # Note: drummer_personas lives in the admin DB and is created by
            # admin/tools/init_drummer_personas_table.py. We don't create it
            # here to avoid surprising frontends that use a different DB
            # layout, but we *do* provide read helpers below if it exists.

            # Admin-only mapping of public DrumTracKAI drummer categories to
            # analysis personas & default knob settings. This lives in the same
            # DB so both the admin tools and backend can share it.
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS drummer_category_mappings (
                category_id TEXT PRIMARY KEY,
                display_name TEXT,
                primary_persona_id TEXT,
                backup_persona_ids_json TEXT,
                default_humanize REAL,
                default_swing REAL,
                default_chorus_ride_pref REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS drummer_presets (
                preset_id TEXT PRIMARY KEY,
                profile_type TEXT NOT NULL,
                name TEXT NOT NULL,
                tier TEXT NOT NULL,
                deltas_json TEXT,
                policies_json TEXT,
                source_type TEXT,
                source_song_name TEXT,
                source_ref TEXT,
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
            cols = self._table_columns("drummers")
            if "display_name" in cols:
                cursor.execute('SELECT * FROM drummers ORDER BY display_name')
            elif "name" in cols:
                cursor.execute('SELECT * FROM drummers ORDER BY name')
            else:
                cursor.execute('SELECT * FROM drummers ORDER BY id')
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            if results:
                return results

            # Prefer real drummers derived from style-vector ingestion.
            # This is the authoritative "real drummers" list in v1.1.17.
            try:
                vec_cols = self._table_columns("drummer_style_vectors")
                if vec_cols and "drummer_id" in vec_cols and "drummer_name" in vec_cols:
                    cursor.execute(
                        'SELECT DISTINCT drummer_id, drummer_name FROM drummer_style_vectors '
                        'WHERE drummer_name IS NOT NULL AND TRIM(drummer_name) != "" '
                        'ORDER BY drummer_name'
                    )
                    vec_rows = cursor.fetchall()
                    if vec_rows:
                        return [
                            {
                                "id": row[0],
                                "drummer_id": row[0],
                                "display_name": row[1],
                                "name": row[1],
                                "source": "drummer_style_vectors",
                            }
                            for row in vec_rows
                        ]
            except Exception:
                pass

            # Fallback: many v1.1.x admin DBs use drummer_personas/drummer_profiles
            # instead of the simple drummers table.
            try:
                persona_cols = self._table_columns("drummer_personas")
                if persona_cols:
                    cursor.execute('SELECT persona_id, display_name, archetypes_json, style_json, created_at, updated_at FROM drummer_personas ORDER BY display_name')
                    persona_rows = cursor.fetchall()
                    return [
                        {
                            "id": row[0],
                            "drummer_id": row[0],
                            "display_name": row[1],
                            "name": row[1],
                            "archetypes_json": row[2],
                            "style_json": row[3],
                            "created_at": row[4],
                            "updated_at": row[5],
                            "source": "drummer_personas",
                        }
                        for row in persona_rows
                    ]
            except Exception:
                pass

            try:
                profile_cols = self._table_columns("drummer_profiles")
                if profile_cols:
                    cursor.execute('SELECT drummer_id, COALESCE(display_name, name) as display_name, category, era FROM drummer_profiles ORDER BY display_name')
                    profile_rows = cursor.fetchall()
                    return [
                        {
                            "id": row[0],
                            "drummer_id": row[0],
                            "display_name": row[1],
                            "name": row[1],
                            "category": row[2],
                            "era": row[3],
                            "source": "drummer_profiles",
                        }
                        for row in profile_rows
                    ]
            except Exception:
                pass

            return []
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
            cols = self._table_columns("drummers")
            if "drummer_id" in cols:
                cursor.execute('SELECT * FROM drummers WHERE drummer_id = ?', (drummer_id,))
            else:
                cursor.execute('SELECT * FROM drummers WHERE id = ?', (drummer_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)

            vec_cols = self._table_columns("drummer_style_vectors")
            if vec_cols and "drummer_id" in vec_cols and "drummer_name" in vec_cols:
                cursor.execute(
                    'SELECT DISTINCT drummer_id, drummer_name FROM drummer_style_vectors WHERE drummer_id = ? LIMIT 1',
                    (drummer_id,),
                )
                vrow = cursor.fetchone()
                if vrow:
                    return {
                        "id": vrow[0],
                        "drummer_id": vrow[0],
                        "display_name": vrow[1],
                        "name": vrow[1],
                        "source": "drummer_style_vectors",
                    }

            persona_cols = self._table_columns("drummer_personas")
            if persona_cols:
                cursor.execute(
                    'SELECT persona_id, display_name, archetypes_json, style_json, created_at, updated_at FROM drummer_personas WHERE persona_id = ?',
                    (drummer_id,),
                )
                prow = cursor.fetchone()
                if prow:
                    return {
                        "id": prow[0],
                        "drummer_id": prow[0],
                        "display_name": prow[1],
                        "name": prow[1],
                        "archetypes_json": prow[2],
                        "style_json": prow[3],
                        "created_at": prow[4],
                        "updated_at": prow[5],
                        "source": "drummer_personas",
                    }

            profile_cols = self._table_columns("drummer_profiles")
            if profile_cols:
                cursor.execute(
                    'SELECT drummer_id, COALESCE(display_name, name) as display_name, category, era, styles FROM drummer_profiles WHERE drummer_id = ?',
                    (drummer_id,),
                )
                pr = cursor.fetchone()
                if pr:
                    return {
                        "id": pr[0],
                        "drummer_id": pr[0],
                        "display_name": pr[1],
                        "name": pr[1],
                        "category": pr[2],
                        "era": pr[3],
                        "styles": pr[4],
                        "source": "drummer_profiles",
                    }

            return None
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

            cols = self._table_columns("drummers")
            if "name" in cols:
                cursor.execute(
                    'INSERT INTO drummers (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
                    (drummer_id, name, description, now, now)
                )
            elif "display_name" in cols and "drummer_id" in cols:
                cursor.execute(
                    'INSERT INTO drummers (drummer_id, display_name) VALUES (?, ?)',
                    (drummer_id, name)
                )
            else:
                raise RuntimeError("Unsupported drummers table schema")
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
            cols = self._table_columns("drummers")
            if "name" in cols:
                valid_fields = {'name', 'description'}
            else:
                valid_fields = {'display_name', 'real_name', 'tagline', 'bio', 'youtube_channel', 'photo_url', 'source'}
            update_data = {k: v for k, v in data.items() if k in valid_fields}
            
            if not update_data:
                logger.warning("No valid fields to update for drummer")
                return False
                
            # Add updated_at timestamp
            if "updated_at" in cols:
                update_data['updated_at'] = datetime.now().isoformat()
            
            # Build the SQL query
            field_str = ', '.join([f"{field} = ?" for field in update_data.keys()])
            values = list(update_data.values()) + [drummer_id]
            
            conn = self._get_connection()
            cursor = conn.cursor()
            if "drummer_id" in cols:
                cursor.execute(f"UPDATE drummers SET {field_str} WHERE drummer_id = ?", values)
            else:
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
            cols = self._table_columns("drummers")
            if "drummer_id" in cols:
                cursor.execute('DELETE FROM drummers WHERE drummer_id = ?', (drummer_id,))
            else:
                cursor.execute('DELETE FROM drummers WHERE id = ?', (drummer_id,))
            conn.commit()
            
            self.data_changed.emit('drummers', 'delete')
            logger.info(f"Deleted drummer ID: {drummer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting drummer {drummer_id}: {str(e)}")
            self.database_error.emit(f"Error deleting drummer: {str(e)}")
            return False

    # ---- Drummer personas (admin DB integration) ---------------------

    def get_drummer_persona(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Load a single drummer persona by ID from drummer_personas.

        Returns a dict with keys:
        - persona_id
        - display_name
        - archetypes (list[str])
        - style (dict of aggregated style metrics)
        or None if not found or table missing.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT persona_id, display_name, archetypes_json, style_json
                FROM drummer_personas
                WHERE persona_id = ?
                """,
                (persona_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            archetypes = json.loads(row["archetypes_json"]) if row["archetypes_json"] else []
            style = json.loads(row["style_json"]) if row["style_json"] else {}
            return {
                "persona_id": row["persona_id"],
                "display_name": row["display_name"],
                "archetypes": archetypes,
                "style": style,
            }
        except sqlite3.OperationalError as e:
            # Likely table does not exist in this DB; fail soft.
            logger.warning(f"drummer_personas table not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting drummer persona {persona_id}: {str(e)}")
            self.database_error.emit(f"Error getting drummer persona: {str(e)}")
            return None

    def get_all_drummer_personas(self) -> List[Dict[str, Any]]:
        """Return all drummer personas as a list of dicts.

        See get_drummer_persona for the dict shape.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT persona_id, display_name, archetypes_json, style_json
                FROM drummer_personas
                ORDER BY display_name
                """
            )
            rows = cursor.fetchall()
            personas: List[Dict[str, Any]] = []
            for row in rows:
                archetypes = json.loads(row["archetypes_json"]) if row["archetypes_json"] else []
                style = json.loads(row["style_json"]) if row["style_json"] else {}
                personas.append(
                    {
                        "persona_id": row["persona_id"],
                        "display_name": row["display_name"],
                        "archetypes": archetypes,
                        "style": style,
                    }
                )
            return personas
        except sqlite3.OperationalError as e:
            logger.warning(f"drummer_personas table not available: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting drummer personas: {str(e)}")
            self.database_error.emit(f"Error getting drummer personas: {str(e)}")
            return []

    # ---- Drummer category mappings (admin-only) ----------------------

    def get_drummer_category_mapping(self, category_id: str) -> Optional[Dict[str, Any]]:
        """Return mapping for a public drummer category, if defined.

        Shape:
          {
            "category_id": str,
            "display_name": str,
            "primary_persona_id": str,
            "backup_persona_ids": [str],
            "default_humanize": float | None,
            "default_swing": float | None,
            "default_chorus_ride_pref": float | None,
          }
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT category_id, display_name, primary_persona_id,
                          backup_persona_ids_json, default_humanize,
                          default_swing, default_chorus_ride_pref
                   FROM drummer_category_mappings
                   WHERE category_id = ?''',
                (category_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            backups = []
            if row[3]:
                try:
                    backups = json.loads(row[3])
                except Exception:
                    backups = []
            return {
                "category_id": row[0],
                "display_name": row[1],
                "primary_persona_id": row[2],
                "backup_persona_ids": backups,
                "default_humanize": row[4],
                "default_swing": row[5],
                "default_chorus_ride_pref": row[6],
            }
        except sqlite3.OperationalError as e:
            logger.warning(f"drummer_category_mappings table not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting drummer category mapping {category_id}: {str(e)}")
            self.database_error.emit(f"Error getting drummer category mapping: {str(e)}")
            return None

    def upsert_drummer_category_mapping(
        self,
        category_id: str,
        display_name: str,
        primary_persona_id: str,
        backup_persona_ids: Optional[List[str]] = None,
        default_humanize: Optional[float] = None,
        default_swing: Optional[float] = None,
        default_chorus_ride_pref: Optional[float] = None,
    ) -> bool:
        """Insert or update a mapping from category_id -> persona + defaults."""
        try:
            now = datetime.now().isoformat()
            backups_json = json.dumps(backup_persona_ids or [])

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO drummer_category_mappings (
                       category_id, display_name, primary_persona_id,
                       backup_persona_ids_json, default_humanize,
                       default_swing, default_chorus_ride_pref,
                       created_at, updated_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(category_id) DO UPDATE SET
                       display_name = excluded.display_name,
                       primary_persona_id = excluded.primary_persona_id,
                       backup_persona_ids_json = excluded.backup_persona_ids_json,
                       default_humanize = excluded.default_humanize,
                       default_swing = excluded.default_swing,
                       default_chorus_ride_pref = excluded.default_chorus_ride_pref,
                       updated_at = excluded.updated_at
                ''',
                (
                    category_id,
                    display_name,
                    primary_persona_id,
                    backups_json,
                    default_humanize,
                    default_swing,
                    default_chorus_ride_pref,
                    now,
                    now,
                ),
            )
            conn.commit()
            logger.info(f"Upserted drummer_category_mapping for {category_id} -> {primary_persona_id}")
            return True
        except Exception as e:
            logger.error(f"Error upserting drummer category mapping for {category_id}: {str(e)}")
            self.database_error.emit(f"Error upserting drummer category mapping: {str(e)}")
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
                
            cols = self._table_columns("drum_beats")
            query += ' ORDER BY name' if 'name' in cols else ' ORDER BY id'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            if results:
                return results

            # Fallback: if drum_beats table is empty, show beats from the local DrumBeats folder
            try:
                project_root = Path(__file__).resolve().parents[2]
                beats_dir = project_root / "DrumBeats"
                if beats_dir.exists() and beats_dir.is_dir():
                    synthetic: List[Dict[str, Any]] = []
                    for wav in sorted(beats_dir.glob("*.wav")):
                        synthetic.append({
                            "id": wav.stem,
                            "name": wav.stem.replace("_", " "),
                            "description": "(filesystem)",
                            "file_path": str(wav),
                            "song_id": None,
                            "drummer_id": None,
                            "bpm": None,
                            "time_signature": None,
                            "complexity": None,
                            "energy": None,
                        })
                    return synthetic
            except Exception:
                pass

            return []
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
