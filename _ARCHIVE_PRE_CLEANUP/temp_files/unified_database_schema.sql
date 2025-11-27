-- DrumTracKAI Unified Database Schema v2.0
-- Comprehensive database for patterns, samples, drummers, and AI training

-- ============================================================
-- 1. DRUMMERS & PROFILES
-- ============================================================
CREATE TABLE IF NOT EXISTS drummers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drummer_id TEXT UNIQUE NOT NULL,  -- 'studio_groove_master'
    display_name TEXT NOT NULL,       -- 'Jeff Porcaro'
    real_name TEXT,                   -- 'Jeffrey Thomas Porcaro'
    tagline TEXT,
    bio TEXT,
    source TEXT,                      -- 'fictional', 'youtube', 'dataset'
    youtube_channel TEXT,
    photo_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS drummer_characteristics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drummer_id TEXT NOT NULL,
    characteristic_name TEXT NOT NULL,
    characteristic_value REAL NOT NULL,
    FOREIGN KEY (drummer_id) REFERENCES drummers(drummer_id),
    UNIQUE(drummer_id, characteristic_name)
);

CREATE TABLE IF NOT EXISTS drummer_genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drummer_id TEXT NOT NULL,
    genre TEXT NOT NULL,
    proficiency REAL DEFAULT 1.0,  -- 0.0-1.0
    FOREIGN KEY (drummer_id) REFERENCES drummers(drummer_id)
);

-- ============================================================
-- 2. DRUM PATTERNS (from MIDI datasets)
-- ============================================================
CREATE TABLE IF NOT EXISTS drum_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    dataset_source TEXT NOT NULL,     -- 'egmd', 'soundtracks', 'rudiments', 'youtube'
    
    -- Timing
    tempo_bpm REAL NOT NULL,
    time_signature TEXT NOT NULL,
    duration_bars INTEGER NOT NULL,
    duration_seconds REAL NOT NULL,
    
    -- Classification
    style TEXT,                       -- 'rock', 'jazz', 'funk', etc.
    genre TEXT,
    section_type TEXT,                -- 'verse', 'chorus', 'fill', etc.
    complexity REAL,                  -- 0.0-1.0
    density REAL,                     -- notes per beat
    energy_level REAL,                -- 0.0-1.0
    
    -- Drum hit counts
    kick_count INTEGER DEFAULT 0,
    snare_count INTEGER DEFAULT 0,
    hihat_count INTEGER DEFAULT 0,
    ride_count INTEGER DEFAULT 0,
    tom_count INTEGER DEFAULT 0,
    crash_count INTEGER DEFAULT 0,
    
    -- Pattern features (JSON)
    kick_pattern TEXT,                -- JSON array of normalized times
    snare_pattern TEXT,
    hihat_pattern TEXT,
    
    -- Attribution
    drummer_name TEXT,
    song_name TEXT,
    artist_name TEXT,
    youtube_url TEXT,
    
    -- Metadata
    quality_score REAL DEFAULT 0.5,   -- Human/AI rated quality
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_patterns_tempo ON drum_patterns(tempo_bpm);
CREATE INDEX idx_patterns_style ON drum_patterns(style);
CREATE INDEX idx_patterns_section ON drum_patterns(section_type);
CREATE INDEX idx_patterns_source ON drum_patterns(dataset_source);

-- ============================================================
-- 3. DRUM SAMPLES (audio files)
-- ============================================================
CREATE TABLE IF NOT EXISTS drum_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    
    -- Sample type
    drum_type TEXT NOT NULL,          -- 'kick', 'snare', 'hihat', 'tom', 'crash', 'ride'
    variation TEXT,                   -- 'center', 'edge', 'rim', 'open', 'closed'
    
    -- Audio properties
    sample_rate INTEGER,
    bit_depth INTEGER,
    duration_ms INTEGER,
    format TEXT,                      -- 'wav', 'mp3', 'flac'
    
    -- Classification
    category TEXT,                    -- 'acoustic', 'electronic', 'processed'
    genre TEXT,
    style TEXT,
    manufacturer TEXT,                -- 'Ludwig', 'DW', 'Roland', etc.
    kit_name TEXT,
    
    -- Audio features
    peak_amplitude REAL,
    rms_level REAL,
    frequency_range TEXT,             -- JSON: [low_freq, high_freq]
    transient_sharpness REAL,         -- 0.0-1.0
    
    -- Quality & rating
    quality_rating REAL DEFAULT 0.5,  -- 0.0-1.0
    usage_count INTEGER DEFAULT 0,
    tags TEXT,                        -- JSON array of tags
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_samples_type ON drum_samples(drum_type);
CREATE INDEX idx_samples_category ON drum_samples(category);
CREATE INDEX idx_samples_style ON drum_samples(style);

-- ============================================================
-- 4. SAMPLE COLLECTIONS (kits/packs)
-- ============================================================
CREATE TABLE IF NOT EXISTS sample_collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_name TEXT UNIQUE NOT NULL,
    description TEXT,
    manufacturer TEXT,
    category TEXT,                    -- 'full_kit', 'single_drum', 'loops'
    folder_path TEXT,
    sample_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collection_samples (
    collection_id INTEGER,
    sample_id INTEGER,
    PRIMARY KEY (collection_id, sample_id),
    FOREIGN KEY (collection_id) REFERENCES sample_collections(id),
    FOREIGN KEY (sample_id) REFERENCES drum_samples(id)
);

-- ============================================================
-- 5. YOUTUBE SOURCES (for continuous learning)
-- ============================================================
CREATE TABLE IF NOT EXISTS youtube_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    youtube_url TEXT UNIQUE NOT NULL,
    video_id TEXT UNIQUE,
    title TEXT,
    channel_name TEXT,
    channel_id TEXT,
    
    -- Drummer info
    drummer_id TEXT,                  -- Link to drummers table
    song_name TEXT,
    artist_name TEXT,
    
    -- Analysis status
    downloaded BOOLEAN DEFAULT 0,
    analyzed BOOLEAN DEFAULT 0,
    midi_extracted BOOLEAN DEFAULT 0,
    
    -- Files
    audio_file_path TEXT,
    midi_file_path TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analyzed_at TIMESTAMP,
    
    FOREIGN KEY (drummer_id) REFERENCES drummers(drummer_id)
);

-- ============================================================
-- 6. AI TRAINING DATA
-- ============================================================
CREATE TABLE IF NOT EXISTS training_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_name TEXT UNIQUE NOT NULL,
    model_version TEXT,
    pattern_count INTEGER,
    training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validation_loss REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS training_patterns (
    batch_id INTEGER,
    pattern_id INTEGER,
    PRIMARY KEY (batch_id, pattern_id),
    FOREIGN KEY (batch_id) REFERENCES training_batches(id),
    FOREIGN KEY (pattern_id) REFERENCES drum_patterns(id)
);

-- ============================================================
-- 7. GENERATED CONTENT (user generations)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    
    -- Input
    audio_file_key TEXT,
    drummer_id TEXT,
    style TEXT,
    tempo_bpm REAL,
    
    -- Output
    midi_data BLOB,
    notes_json TEXT,
    
    -- Feedback
    user_rating INTEGER,              -- 1-5 stars
    user_feedback TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (drummer_id) REFERENCES drummers(drummer_id)
);

-- ============================================================
-- 8. CROSS-REFERENCE TABLES
-- ============================================================

-- Link patterns to drummers
CREATE TABLE IF NOT EXISTS pattern_drummer_similarity (
    pattern_id INTEGER,
    drummer_id TEXT,
    similarity_score REAL,           -- 0.0-1.0
    PRIMARY KEY (pattern_id, drummer_id),
    FOREIGN KEY (pattern_id) REFERENCES drum_patterns(id),
    FOREIGN KEY (drummer_id) REFERENCES drummers(drummer_id)
);

-- Link samples to patterns (which samples sound good with which patterns)
CREATE TABLE IF NOT EXISTS pattern_sample_mapping (
    pattern_id INTEGER,
    sample_id INTEGER,
    drum_lane TEXT,                  -- 'kick', 'snare', etc.
    compatibility_score REAL,
    PRIMARY KEY (pattern_id, sample_id, drum_lane),
    FOREIGN KEY (pattern_id) REFERENCES drum_patterns(id),
    FOREIGN KEY (sample_id) REFERENCES drum_samples(id)
);
