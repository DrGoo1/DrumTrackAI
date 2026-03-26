import React from 'react';

export type Section = { id: string; label: string; start: number; end: number };

type Props = {
  sections: Section[];
  onChange: (sections: Section[]) => void;
};

export const SectionEditor: React.FC<Props> = ({ sections }) => {
  return (
    <div style={{ padding: 8 }}>
      <h3>Sections</h3>
      <ul>
        {sections.map((s) => (
          <li key={s.id}>{s.label}: {s.start.toFixed(2)}s - {s.end.toFixed(2)}s</li>
        ))}
      </ul>
    </div>
  );
};
