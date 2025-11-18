// Scheduler: lookahead scheduler that posts events into the AudioEngine or Worklet

export type ScheduledNote = {
  time: number; // seconds (AudioContext time)
  lane: string; // e.g., 'kick','snare'
  midi: number;
  velocity: number;
};

export class Scheduler {
  private lookaheadMs = 100;
  private timer: number | null = null;
  private running = false;
  private getCurrentTime: () => number;
  private onScheduleWindow: (start: number, end: number) => void;

  constructor(getCurrentTime: () => number, onScheduleWindow: (start: number, end: number) => void) {
    this.getCurrentTime = getCurrentTime;
    this.onScheduleWindow = onScheduleWindow;
  }

  start() {
    if (this.running) return;
    this.running = true;
    const tick = () => {
      if (!this.running) return;
      const start = this.getCurrentTime();
      const end = start + this.lookaheadMs / 1000;
      this.onScheduleWindow(start, end);
      this.timer = window.setTimeout(tick, this.lookaheadMs / 2);
    };
    tick();
  }

  stop() {
    this.running = false;
    if (this.timer !== null) window.clearTimeout(this.timer);
    this.timer = null;
  }
}
