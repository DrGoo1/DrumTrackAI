// Tempo conversion utilities for PPQ-based MIDI with variable BPM
// Handles piecewise-constant BPM segments from audio analysis

import { TempoPt } from './types'

/**
 * Convert seconds to MIDI ticks using variable tempo map
 * @param tempoMap Array of tempo points from audio analysis
 * @param sec Time in seconds to convert
 * @param ppq Pulses per quarter note (default 480)
 * @returns MIDI ticks
 */
export function secondsToTicks(tempoMap: TempoPt[], sec: number, ppq = 480): number {
  if (!tempoMap.length) return Math.round((sec * ppq * 120) / 60) // fallback 120 BPM
  
  let ticks = 0
  let lastTime = 0
  
  for (let i = 0; i < tempoMap.length; i++) {
    const current = tempoMap[i]
    const next = tempoMap[i + 1]
    
    // Determine segment end time
    const segmentEnd = Math.min(sec, next ? next.tSec : sec)
    const segmentDuration = Math.max(0, segmentEnd - lastTime)
    
    // Calculate ticks for this segment
    const bpm = current.bpm
    const ticksPerSecond = (ppq * bpm) / 60
    ticks += segmentDuration * ticksPerSecond
    
    // If we've reached the target time, break
    if (next && segmentEnd === next.tSec) {
      lastTime = next.tSec
      continue
    }
    break
  }
  
  return Math.round(ticks)
}

/**
 * Convert MIDI ticks to seconds using variable tempo map
 * @param tempoMap Array of tempo points from audio analysis
 * @param ticks MIDI ticks to convert
 * @param ppq Pulses per quarter note (default 480)
 * @returns Time in seconds
 */
export function ticksToSeconds(tempoMap: TempoPt[], ticks: number, ppq = 480): number {
  if (!tempoMap.length) return (ticks * 60) / (ppq * 120) // fallback 120 BPM
  
  let seconds = 0
  let remainingTicks = ticks
  
  for (let i = 0; i < tempoMap.length; i++) {
    const current = tempoMap[i]
    const next = tempoMap[i + 1]
    
    const bpm = current.bpm
    const ticksPerSecond = (ppq * bpm) / 60
    
    if (!next) {
      // Last segment - use remaining ticks
      seconds += remainingTicks / ticksPerSecond
      break
    }
    
    // Calculate ticks in this segment
    const segmentDuration = next.tSec - current.tSec
    const segmentTicks = segmentDuration * ticksPerSecond
    
    if (remainingTicks > segmentTicks) {
      // Move through this entire segment
      seconds += segmentDuration
      remainingTicks -= segmentTicks
    } else {
      // Target is within this segment
      seconds += remainingTicks / ticksPerSecond
      break
    }
  }
  
  return seconds
}

/**
 * Get BPM at a specific time
 * @param tempoMap Array of tempo points
 * @param sec Time in seconds
 * @returns BPM at that time
 */
export function getBpmAtTime(tempoMap: TempoPt[], sec: number): number {
  if (!tempoMap.length) return 120
  
  let currentBpm = tempoMap[0].bpm
  
  for (const point of tempoMap) {
    if (point.tSec <= sec) {
      currentBpm = point.bpm
    } else {
      break
    }
  }
  
  return currentBpm
}

/**
 * Quantize ticks to nearest beat subdivision
 * @param ticks Input ticks
 * @param ppq Pulses per quarter note
 * @param subdivision Beat subdivision (4=quarter, 8=eighth, 16=sixteenth, etc.)
 * @returns Quantized ticks
 */
export function quantizeTicks(ticks: number, ppq: number, subdivision: number): number {
  const ticksPerSubdivision = (ppq * 4) / subdivision
  return Math.round(ticks / ticksPerSubdivision) * ticksPerSubdivision
}

/**
 * Apply swing to quantized ticks
 * @param ticks Input ticks (should be quantized)
 * @param ppq Pulses per quarter note
 * @param swingAmount Swing amount 0-100 (50 = no swing, 67 = triplet swing)
 * @returns Swung ticks
 */
export function applySwing(ticks: number, ppq: number, swingAmount: number): number {
  const eighthNoteTicks = ppq / 2
  const beatPosition = ticks % (ppq * 2) // position within 2 beats
  const isOffBeat = Math.floor(beatPosition / eighthNoteTicks) % 2 === 1
  
  if (isOffBeat && swingAmount !== 50) {
    const swingRatio = swingAmount / 100
    const swingOffset = (swingRatio - 0.5) * eighthNoteTicks
    return ticks + swingOffset
  }
  
  return ticks
}

/**
 * Create a default tempo map for new projects
 * @param bpm Default BPM
 * @returns Single-point tempo map
 */
export function createDefaultTempoMap(bpm = 120): TempoPt[] {
  return [{ tSec: 0, bpm }]
}
