// MIDI Operations for WebDAW
// Quantize, Swing, and Humanize functions for real-time preview

export const applyQuantize = (notes, { strength = 1.0, grid = 0.25 }) => {
  const quantizedNotes = { ...notes };
  
  Object.keys(quantizedNotes).forEach(drum => {
    quantizedNotes[drum] = quantizedNotes[drum].map(note => {
      const currentTime = note.seconds;
      const gridTime = Math.round(currentTime / grid) * grid;
      const quantizedTime = currentTime + (gridTime - currentTime) * strength;
      
      return {
        ...note,
        seconds: Math.max(0, quantizedTime)
      };
    });
  });
  
  return quantizedNotes;
};

export const applySwing = (notes, { amount = 0.5, grid = 0.25 }) => {
  const swungNotes = { ...notes };
  
  Object.keys(swungNotes).forEach(drum => {
    swungNotes[drum] = swungNotes[drum].map(note => {
      const currentTime = note.seconds;
      const beatPosition = (currentTime % (grid * 2)) / grid;
      
      // Apply swing to off-beats (odd subdivisions)
      if (beatPosition > 0.5 && beatPosition < 1.5) {
        const swingOffset = (grid * amount * 0.1); // 10% max swing
        return {
          ...note,
          seconds: currentTime + swingOffset
        };
      }
      
      return note;
    });
  });
  
  return swungNotes;
};

export const applyHumanize = (notes, { amount = 0.2, timingVariation = 0.05, velocityVariation = 10 }) => {
  const humanizedNotes = { ...notes };
  
  Object.keys(humanizedNotes).forEach(drum => {
    humanizedNotes[drum] = humanizedNotes[drum].map(note => {
      // Random timing variation
      const timingJitter = (Math.random() - 0.5) * 2 * timingVariation * amount;
      
      // Random velocity variation
      const velocityJitter = (Math.random() - 0.5) * 2 * velocityVariation * amount;
      const newVelocity = Math.max(1, Math.min(127, (note.velocity || 100) + velocityJitter));
      
      return {
        ...note,
        seconds: Math.max(0, note.seconds + timingJitter),
        velocity: Math.round(newVelocity)
      };
    });
  });
  
  return humanizedNotes;
};

// Undo/Redo system for MIDI operations
export class MidiHistoryManager {
  constructor(maxHistorySize = 50) {
    this.history = [];
    this.currentIndex = -1;
    this.maxHistorySize = maxHistorySize;
  }

  pushState(notes, description = 'MIDI Operation') {
    // Remove any future states if we're not at the end
    if (this.currentIndex < this.history.length - 1) {
      this.history = this.history.slice(0, this.currentIndex + 1);
    }

    // Add new state
    this.history.push({
      notes: JSON.parse(JSON.stringify(notes)), // Deep copy
      description,
      timestamp: Date.now()
    });

    // Limit history size
    if (this.history.length > this.maxHistorySize) {
      this.history = this.history.slice(-this.maxHistorySize);
    }

    this.currentIndex = this.history.length - 1;
  }

  undo() {
    if (this.canUndo()) {
      this.currentIndex--;
      return this.getCurrentState();
    }
    return null;
  }

  redo() {
    if (this.canRedo()) {
      this.currentIndex++;
      return this.getCurrentState();
    }
    return null;
  }

  canUndo() {
    return this.currentIndex > 0;
  }

  canRedo() {
    return this.currentIndex < this.history.length - 1;
  }

  getCurrentState() {
    if (this.currentIndex >= 0 && this.currentIndex < this.history.length) {
      return this.history[this.currentIndex];
    }
    return null;
  }

  getHistoryInfo() {
    return {
      canUndo: this.canUndo(),
      canRedo: this.canRedo(),
      currentIndex: this.currentIndex,
      historyLength: this.history.length,
      currentDescription: this.getCurrentState()?.description
    };
  }
}

// Marquee selection utilities
export const getNotesInSelection = (notes, selectionStart, selectionEnd, drums = null) => {
  const selectedNotes = {};
  const drumsToCheck = drums || Object.keys(notes);
  
  drumsToCheck.forEach(drum => {
    if (notes[drum]) {
      selectedNotes[drum] = notes[drum].filter(note => 
        note.seconds >= selectionStart && note.seconds <= selectionEnd
      );
    }
  });
  
  return selectedNotes;
};

export const deleteNotesInSelection = (notes, selectionStart, selectionEnd, drums = null) => {
  const updatedNotes = { ...notes };
  const drumsToCheck = drums || Object.keys(notes);
  
  drumsToCheck.forEach(drum => {
    if (updatedNotes[drum]) {
      updatedNotes[drum] = updatedNotes[drum].filter(note => 
        !(note.seconds >= selectionStart && note.seconds <= selectionEnd)
      );
    }
  });
  
  return updatedNotes;
};

export const moveNotesInSelection = (notes, selectionStart, selectionEnd, timeOffset, drums = null) => {
  const updatedNotes = { ...notes };
  const drumsToCheck = drums || Object.keys(notes);
  
  drumsToCheck.forEach(drum => {
    if (updatedNotes[drum]) {
      updatedNotes[drum] = updatedNotes[drum].map(note => {
        if (note.seconds >= selectionStart && note.seconds <= selectionEnd) {
          return {
            ...note,
            seconds: Math.max(0, note.seconds + timeOffset)
          };
        }
        return note;
      });
    }
  });
  
  return updatedNotes;
};

// Grid snapping utilities
export const snapToGrid = (time, gridSize = 0.25, snapStrength = 1.0) => {
  const gridTime = Math.round(time / gridSize) * gridSize;
  return time + (gridTime - time) * snapStrength;
};

export const getGridLines = (duration, gridSize = 0.25, beatsPerBar = 4) => {
  const lines = [];
  const barLength = beatsPerBar * gridSize;
  
  for (let time = 0; time <= duration; time += gridSize) {
    const isBarLine = (time % barLength) === 0;
    const isBeatLine = (time % 1.0) === 0;
    
    lines.push({
      time,
      type: isBarLine ? 'bar' : isBeatLine ? 'beat' : 'subdivision',
      opacity: isBarLine ? 1.0 : isBeatLine ? 0.7 : 0.3
    });
  }
  
  return lines;
};
