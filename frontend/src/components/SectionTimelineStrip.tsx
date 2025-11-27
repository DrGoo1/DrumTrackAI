/**
 * Section Timeline Strip - Visual section representation with lock controls
 * Part of Drum Builder v2.0 UI Components
 */
import React from 'react';

export interface Section {
  id: string;
  label: string;
  startBar: number;
  endBar: number;
  startTime: number;
  endTime: number;
  color?: string;
}

export interface SectionLock {
  sectionId: string;
  locked: boolean;
  hasTrack: boolean;
}

interface SectionTimelineStripProps {
  sections: Section[];
  sectionLocks: Map<string, SectionLock>;
  selectedSectionId?: string;
  onSectionClick: (sectionId: string) => void;
  onLockToggle: (sectionId: string) => void;
  totalDuration: number;
  zoom?: number;
}

export const SectionTimelineStrip: React.FC<SectionTimelineStripProps> = ({
  sections,
  sectionLocks,
  selectedSectionId,
  onSectionClick,
  onLockToggle,
  totalDuration,
  zoom = 1.0
}) => {
  const getSectionColor = (section: Section): string => {
    if (section.color) return section.color;
    
    // Auto-assign colors based on label
    const label = section.label.toLowerCase();
    if (label.includes('intro')) return '#3B82F6';
    if (label.includes('verse')) return '#10B981';
    if (label.includes('chorus')) return '#F59E0B';
    if (label.includes('bridge')) return '#8B5CF6';
    if (label.includes('outro')) return '#6366F1';
    return '#6B7280';
  };

  const getSectionWidth = (section: Section): number => {
    const duration = section.endTime - section.startTime;
    return (duration / totalDuration) * 100;
  };

  const getSectionLeft = (section: Section): number => {
    return (section.startTime / totalDuration) * 100;
  };

  const getLockInfo = (sectionId: string): SectionLock => {
    return sectionLocks.get(sectionId) || {
      sectionId,
      locked: false,
      hasTrack: false
    };
  };

  return (
    <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-white flex items-center">
          <span className="mr-2">📊</span>
          Section Timeline
        </h3>
        <div className="flex items-center space-x-2 text-xs">
          <div className="flex items-center">
            <div className="w-3 h-3 bg-green-500 rounded-full mr-1"></div>
            <span className="text-slate-400">Has Drums</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-yellow-500 rounded-full mr-1"></div>
            <span className="text-slate-400">Locked</span>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div 
        className="relative h-20 bg-slate-800 rounded-lg overflow-hidden"
        style={{ minWidth: `${100 * zoom}%` }}
      >
        {sections.map((section) => {
          const lockInfo = getLockInfo(section.id);
          const isSelected = section.id === selectedSectionId;
          const sectionColor = getSectionColor(section);
          const width = getSectionWidth(section);
          const left = getSectionLeft(section);

          return (
            <div
              key={section.id}
              className={`absolute top-0 bottom-0 border-r border-slate-900 transition-all ${
                isSelected ? 'z-10' : 'z-0'
              }`}
              style={{
                left: `${left}%`,
                width: `${width}%`
              }}
            >
              {/* Section Background */}
              <div
                className={`h-full cursor-pointer transition-all ${
                  isSelected
                    ? 'ring-2 ring-white ring-opacity-100'
                    : 'hover:brightness-110'
                }`}
                style={{
                  backgroundColor: sectionColor,
                  opacity: lockInfo.locked ? 0.7 : 0.9
                }}
                onClick={() => onSectionClick(section.id)}
              >
                {/* Section Label */}
                <div className="p-2 h-full flex flex-col justify-between">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-xs font-bold text-white drop-shadow-lg">
                        {section.label}
                      </div>
                      <div className="text-xs text-white/80 drop-shadow">
                        Bars {section.startBar + 1}-{section.endBar + 1}
                      </div>
                    </div>
                    
                    {/* Status Indicators */}
                    <div className="flex flex-col space-y-1">
                      {lockInfo.hasTrack && (
                        <div 
                          className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-xs"
                          title="Has drum track"
                        >
                          ✓
                        </div>
                      )}
                      {lockInfo.locked && (
                        <div 
                          className="w-5 h-5 bg-yellow-500 rounded-full flex items-center justify-center text-xs"
                          title="Locked"
                        >
                          🔒
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Lock Toggle Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onLockToggle(section.id);
                    }}
                    className={`mt-auto text-xs px-2 py-1 rounded transition-all ${
                      lockInfo.locked
                        ? 'bg-yellow-600 hover:bg-yellow-500 text-white'
                        : 'bg-white/20 hover:bg-white/30 text-white'
                    }`}
                    title={lockInfo.locked ? 'Unlock section' : 'Lock section'}
                  >
                    {lockInfo.locked ? '🔒 Locked' : '🔓 Lock'}
                  </button>
                </div>
              </div>

              {/* Selected Indicator */}
              {isSelected && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-white"></div>
              )}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
        <div>
          {sections.length} sections • {totalDuration.toFixed(1)}s total
        </div>
        <div>
          Click to select • Lock to preserve
        </div>
      </div>
    </div>
  );
};

export default SectionTimelineStrip;
