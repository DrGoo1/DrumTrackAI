import React, { useEffect, useState } from 'react';

export interface Drummer {
  id: string;
  display_name: string;
  tagline: string;
  genre_tags: string[];
  difficulty: string;
  icon: string;
  color: string;
  description: string;
  best_for: string[];
  signature_techniques: string[];
}

interface DrummerSelectorProps {
  onSelect: (drummer: Drummer) => void;
  selectedDrummer?: Drummer | null;
}

export const DrummerSelector: React.FC<DrummerSelectorProps> = ({ onSelect, selectedDrummer }) => {
  const [drummers, setDrummers] = useState<Drummer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    fetchDrummers();
  }, []);

  const fetchDrummers = async () => {
    try {
      const API_BASE = (window as any).__API_BASE__ || process.env.REACT_APP_API_BASE || "http://localhost:8000";
      const response = await fetch(`${API_BASE}/api/drummers`);
      if (!response.ok) {
        throw new Error('Failed to fetch drummers');
      }
      const data = await response.json();
      setDrummers(data.drummers || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="drummer-selector loading">
        <p>Loading DrumTrackAI drummers...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="drummer-selector error">
        <p>Error loading drummers: {error}</p>
      </div>
    );
  }

  return (
    <div className="drummer-selector">
      <div className="drummer-selector-header">
        <h3>🥁 Select Drummer Style</h3>
        {selectedDrummer && (
          <div className="selected-drummer-badge" style={{ borderColor: selectedDrummer.color }}>
            <span className="icon">{selectedDrummer.icon}</span>
            <span className="name">{selectedDrummer.display_name}</span>
            <button 
              className="change-btn" 
              onClick={() => setExpanded(!expanded)}
              aria-label="Change drummer"
            >
              {expanded ? '▼' : '▶'}
            </button>
          </div>
        )}
        {!selectedDrummer && (
          <button 
            className="select-drummer-btn" 
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? 'Close' : 'Choose Style'}
          </button>
        )}
      </div>

      {(expanded || !selectedDrummer) && (
        <div className="drummer-grid">
          {drummers.map((drummer) => (
            <div
              key={drummer.id}
              className={`drummer-card ${selectedDrummer?.id === drummer.id ? 'selected' : ''}`}
              style={{ borderLeftColor: drummer.color }}
              onClick={() => {
                onSelect(drummer);
                setExpanded(false);
              }}
            >
              <div className="drummer-card-header">
                <span className="drummer-icon">{drummer.icon}</span>
                <div className="drummer-title">
                  <h4>{drummer.display_name}</h4>
                  <p className="tagline">{drummer.tagline}</p>
                </div>
              </div>

              <div className="drummer-tags">
                {drummer.genre_tags.map((tag, idx) => (
                  <span key={idx} className="genre-tag">
                    {tag}
                  </span>
                ))}
                <span className={`difficulty-tag ${drummer.difficulty.toLowerCase()}`}>
                  {drummer.difficulty}
                </span>
              </div>

              <p className="drummer-description">{drummer.description}</p>

              <div className="drummer-best-for">
                <strong>Best for:</strong>
                <ul>
                  {drummer.best_for.slice(0, 3).map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className="drummer-techniques">
                <strong>Signature:</strong>
                <div className="technique-chips">
                  {drummer.signature_techniques.slice(0, 3).map((tech, idx) => (
                    <span key={idx} className="technique-chip">
                      {tech}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <style>{`
        .drummer-selector {
          background: #1e1e1e;
          border: 1px solid #333;
          border-radius: 8px;
          padding: 16px;
          margin: 16px 0;
        }

        .drummer-selector-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }

        .drummer-selector-header h3 {
          margin: 0;
          color: #fff;
          font-size: 18px;
        }

        .selected-drummer-badge {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          background: #2a2a2a;
          border: 2px solid;
          border-radius: 6px;
          color: #fff;
        }

        .selected-drummer-badge .icon {
          font-size: 20px;
        }

        .selected-drummer-badge .name {
          font-weight: 600;
        }

        .selected-drummer-badge .change-btn {
          background: none;
          border: none;
          color: #aaa;
          cursor: pointer;
          padding: 4px;
          font-size: 12px;
        }

        .selected-drummer-badge .change-btn:hover {
          color: #fff;
        }

        .select-drummer-btn {
          background: #4F46E5;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 600;
        }

        .select-drummer-btn:hover {
          background: #4338CA;
        }

        .drummer-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 16px;
          max-height: 600px;
          overflow-y: auto;
        }

        .drummer-card {
          background: #2a2a2a;
          border: 2px solid #333;
          border-left-width: 4px;
          border-radius: 8px;
          padding: 16px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .drummer-card:hover {
          background: #333;
          border-color: #555;
          transform: translateY(-2px);
        }

        .drummer-card.selected {
          background: #3a3a3a;
          border-color: #4F46E5;
        }

        .drummer-card-header {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 12px;
        }

        .drummer-icon {
          font-size: 32px;
          line-height: 1;
        }

        .drummer-title h4 {
          margin: 0;
          color: #fff;
          font-size: 16px;
        }

        .drummer-title .tagline {
          margin: 4px 0 0 0;
          color: #aaa;
          font-size: 13px;
          font-style: italic;
        }

        .drummer-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-bottom: 12px;
        }

        .genre-tag {
          background: #3a3a3a;
          color: #aaa;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
        }

        .difficulty-tag {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
        }

        .difficulty-tag.intermediate {
          background: #F59E0B;
          color: #000;
        }

        .difficulty-tag.advanced {
          background: #EF4444;
          color: #fff;
        }

        .difficulty-tag.expert {
          background: #DC2626;
          color: #fff;
        }

        .drummer-description {
          color: #ccc;
          font-size: 13px;
          line-height: 1.4;
          margin: 12px 0;
        }

        .drummer-best-for {
          margin: 12px 0;
        }

        .drummer-best-for strong {
          color: #fff;
          font-size: 12px;
          display: block;
          margin-bottom: 6px;
        }

        .drummer-best-for ul {
          margin: 0;
          padding-left: 16px;
          color: #aaa;
          font-size: 12px;
        }

        .drummer-best-for li {
          margin: 2px 0;
        }

        .drummer-techniques {
          margin-top: 12px;
        }

        .drummer-techniques strong {
          color: #fff;
          font-size: 12px;
          display: block;
          margin-bottom: 6px;
        }

        .technique-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
        }

        .technique-chip {
          background: #1e1e1e;
          color: #aaa;
          padding: 3px 8px;
          border-radius: 12px;
          font-size: 11px;
          border: 1px solid #444;
        }

        .drummer-selector.loading,
        .drummer-selector.error {
          text-align: center;
          color: #aaa;
          padding: 32px;
        }

        .drummer-selector.error {
          color: #EF4444;
        }
      `}</style>
    </div>
  );
};

export default DrummerSelector;
