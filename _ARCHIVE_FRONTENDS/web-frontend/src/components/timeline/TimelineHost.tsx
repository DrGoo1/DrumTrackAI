// Timeline Host - React wrapper for waveform-playlist
// Integrates open source timeline with our existing infrastructure

import React, { useEffect, useRef, useState } from 'react'
import * as Tone from 'tone'
import { useDawStore } from '../../state/dawStore'
import { useMidi } from '../../midi/midiStore'

// TypeScript shim for waveform-playlist
declare global {
  interface Window {
    WaveformPlaylist: any
  }
}

interface TimelineHostProps {
  className?: string
}

export default function TimelineHost({ className = '' }: TimelineHostProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const playlistRef = useRef<any>(null)
  const [isLoaded, setIsLoaded] = useState(false)
  
  // DAW state
  const { project, pxPerSecond, cursorSec, playing } = useDawStore()
  const { song: midiSong } = useMidi()
  
  // Initialize waveform-playlist
  useEffect(() => {
    if (!containerRef.current || isLoaded) return
    
    const initPlaylist = async () => {
      try {
        console.log('Initializing waveform-playlist...')
        
        // Dynamically import waveform-playlist with better error handling
        const WaveformPlaylistModule = await import('waveform-playlist')
        console.log('Waveform-playlist module loaded:', WaveformPlaylistModule)
        
        // Handle different export patterns
        let WaveformPlaylist
        if (WaveformPlaylistModule.default) {
          WaveformPlaylist = WaveformPlaylistModule.default
        } else if (typeof WaveformPlaylistModule === 'function') {
          WaveformPlaylist = WaveformPlaylistModule
        } else {
          throw new Error('Could not find WaveformPlaylist constructor')
        }
        
        console.log('Creating playlist with container:', containerRef.current)
        
        const playlist = WaveformPlaylist({
          container: containerRef.current,
          timescale: true,
          mono: false,
          fadeType: 'logarithmic',
          exclSolo: false,
          emptyText: "Drag audio files here or use upload button",
          barWidth: 3,
          barGap: 1,
          controls: {
            show: true,
            width: 200
          },
          colors: {
            waveOutlineColor: '#374151',
            waveProgressColor: '#3b82f6',
            timeColor: '#9ca3af',
            fadeColor: 'rgba(59, 130, 246, 0.1)'
          },
          seekStyle: 'line',
          waveHeight: 80,
          collapsedWaveHeight: 30,
          zoomLevels: [500, 1000, 3000, 5000]
        })
        
        console.log('Playlist created:', playlist)
        
        // Set up event listeners
        if (playlist && typeof playlist.on === 'function') {
          playlist.on('select', (start: number, end: number) => {
            console.log('Selection:', start, end)
          })
          
          playlist.on('timeupdate', (seconds: number) => {
            useDawStore.getState().setCursor(seconds)
          })
          
          playlist.on('finished', () => {
            useDawStore.getState().pause()
          })
        }
        
        playlistRef.current = playlist
        setIsLoaded(true)
        
        console.log('Timeline host initialized successfully')
        
      } catch (error) {
        console.error('Failed to initialize timeline host:', error)
        console.error('Error details:', error.message, error.stack)
        
        // Fallback: show basic timeline without waveform-playlist
        setIsLoaded(true)
      }
    }
    
    initPlaylist()
    
    return () => {
      if (playlistRef.current && typeof playlistRef.current.destroy === 'function') {
        playlistRef.current.destroy()
      }
    }
  }, [isLoaded])
  
  // Sync with DAW transport
  useEffect(() => {
    if (!playlistRef.current) return
    
    if (playing) {
      playlistRef.current.play()
    } else {
      playlistRef.current.pause()
    }
  }, [playing])
  
  // Sync cursor position
  useEffect(() => {
    if (!playlistRef.current) return
    
    const currentTime = playlistRef.current.getCurrentTime()
    if (Math.abs(currentTime - cursorSec) > 0.1) {
      playlistRef.current.seekTo(cursorSec)
    }
  }, [cursorSec])
  
  // Load audio tracks from project
  useEffect(() => {
    if (!playlistRef.current || !project?.tracks) return
    
    const loadTracks = async () => {
      try {
        // Clear existing tracks
        playlistRef.current.clear()
        
        // Load up to 6 audio stems
        const audioTracks = project.tracks.slice(0, 6)
        
        for (const track of audioTracks) {
          if (track.fileKey) {
            // Get presigned URL for audio file
            const response = await fetch(`/api/files/download-url/${track.fileKey}`)
            const { downloadUrl } = await response.json()
            
            // Load track into playlist
            await playlistRef.current.load([{
              src: downloadUrl,
              name: track.name || `Track ${track.id}`,
              gain: Math.pow(10, (track.gainDb || 0) / 20), // Convert dB to linear
              muted: track.mute || false,
              soloed: track.solo || false
            }])
          }
        }
        
        console.log(`Loaded ${audioTracks.length} audio tracks`)
        
      } catch (error) {
        console.error('Failed to load audio tracks:', error)
      }
    }
    
    loadTracks()
  }, [project?.tracks])
  
  // Update zoom level
  useEffect(() => {
    if (!playlistRef.current) return
    
    // Convert our pxPerSecond to waveform-playlist zoom
    const zoomLevel = Math.max(500, Math.min(5000, pxPerSecond * 10))
    playlistRef.current.setZoom(zoomLevel)
  }, [pxPerSecond])
  
  // Handle file drops
  const handleDrop = async (event: React.DragEvent) => {
    event.preventDefault()
    
    if (!playlistRef.current) return
    
    const files = Array.from(event.dataTransfer.files)
    const audioFiles = files.filter(file => file.type.startsWith('audio/'))
    
    if (audioFiles.length === 0) return
    
    try {
      // Upload and add files to timeline
      for (const file of audioFiles.slice(0, 6)) { // Max 6 tracks
        const formData = new FormData()
        formData.append('file', file)
        
        const uploadResponse = await fetch('/api/files/upload', {
          method: 'POST',
          body: formData
        })
        
        const { fileKey } = await uploadResponse.json()
        
        // Add track to DAW store
        const trackId = useDawStore.getState().addTrack(file.name)
        useDawStore.getState().setTrackFileKey(trackId, fileKey)
        
        // Load into playlist
        const url = URL.createObjectURL(file)
        await playlistRef.current.load([{
          src: url,
          name: file.name,
          gain: 1,
          muted: false,
          soloed: false
        }])
      }
      
    } catch (error) {
      console.error('Failed to upload and load files:', error)
    }
  }
  
  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault()
  }

  // Handle file input uploads
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    const audioFiles = Array.from(files).filter(file => file.type.startsWith('audio/'))
    if (audioFiles.length === 0) return

    try {
      // Create simple waveform visualization for each file
      for (const file of audioFiles.slice(0, 6)) { // Max 6 tracks
        const trackId = useDawStore.getState().addTrack(file.name)
        
        // Create audio context and analyze file
        const audioContext = new AudioContext()
        const arrayBuffer = await file.arrayBuffer()
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
        
        // Generate simple waveform data
        const channelData = audioBuffer.getChannelData(0)
        const samples = 1000 // Sample points for visualization
        const blockSize = Math.floor(channelData.length / samples)
        const waveformData = []
        
        for (let i = 0; i < samples; i++) {
          let sum = 0
          for (let j = 0; j < blockSize; j++) {
            sum += Math.abs(channelData[i * blockSize + j] || 0)
          }
          waveformData.push(sum / blockSize)
        }
        
        // Store waveform data and file info
        useDawStore.getState().setTrackWaveform(trackId, {
          sr: audioBuffer.sampleRate,
          peaks: waveformData,
          samples: channelData.length
        })
        useDawStore.getState().setTrackFileKey(trackId, URL.createObjectURL(file))
        
        console.log(`Loaded audio file: ${file.name}, duration: ${audioBuffer.duration}s`)
      }
      
    } catch (error) {
      console.error('Failed to load audio files:', error)
    }
  }
  
  if (!isLoaded) {
    return (
      <div className={`flex items-center justify-center h-64 bg-slate-900 rounded-lg ${className}`}>
        <div className="text-slate-400">Loading timeline...</div>
      </div>
    )
  }
  
  return (
    <div 
      className={`timeline-host bg-slate-900 rounded-lg overflow-hidden relative ${className}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
    >
      <div ref={containerRef} className="w-full h-full min-h-[300px]" />
      
      {/* Fallback UI if waveform-playlist failed to load */}
      {!playlistRef.current && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-800/90">
          <div className="text-slate-300 text-lg mb-4">Timeline Ready</div>
          <div className="text-slate-400 text-sm mb-4">Drag audio files here to get started</div>
          <input
            type="file"
            accept="audio/*"
            multiple
            className="hidden"
            id="audio-upload"
            onChange={handleFileUpload}
          />
          <label
            htmlFor="audio-upload"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg cursor-pointer transition-colors"
          >
            Upload Audio Files
          </label>
        </div>
      )}
      
      {/* Overlay for bars/beats ruler */}
      <div className="absolute top-0 left-0 right-0 h-8 pointer-events-none">
        <BarsBeatsRuler />
      </div>
      
      {/* Overlay for arrangement sections */}
      <div className="absolute top-8 left-0 right-0 h-6 pointer-events-none">
        <ArrangementOverlay />
      </div>
      
      {/* Overlay for MIDI markers */}
      <div className="absolute top-14 left-0 right-0 h-4 pointer-events-none">
        <MidiMarkersOverlay />
      </div>
    </div>
  )
}

// Bars/Beats Ruler Component
function BarsBeatsRuler() {
  const { project, pxPerSecond } = useDawStore()
  const { tempoMap, timeSig } = useMidi(state => ({ 
    tempoMap: state.song.tempoMap, 
    timeSig: state.song.timeSig 
  }))
  
  if (!project || !tempoMap.length) return null
  
  const [numerator, denominator] = timeSig
  const beatsPerBar = numerator
  const beatUnit = 4 / denominator // Quarter note = 1
  
  const rulers: React.ReactElement[] = []
  const projectLength = project.lengthSec || 60
  
  // Generate beat markers
  let currentTime = 0
  let beatCount = 0
  
  while (currentTime < projectLength) {
    const x = currentTime * pxPerSecond
    const isBarStart = beatCount % beatsPerBar === 0
    const barNumber = Math.floor(beatCount / beatsPerBar) + 1
    const beatInBar = (beatCount % beatsPerBar) + 1
    
    rulers.push(
      <div
        key={`beat-${beatCount}`}
        className={`absolute top-0 ${isBarStart ? 'h-8 border-slate-400' : 'h-4 border-slate-600'} border-l`}
        style={{ left: x }}
      >
        {isBarStart && (
          <span className="absolute top-0 left-1 text-xs text-slate-400 font-mono">
            {barNumber}
          </span>
        )}
      </div>
    )
    
    // Calculate next beat time based on current tempo
    const currentBpm = getCurrentBpm(tempoMap, currentTime)
    const beatDuration = 60 / currentBpm * beatUnit
    currentTime += beatDuration
    beatCount++
  }
  
  return <div className="relative w-full h-full">{rulers}</div>
}

// Arrangement Sections Overlay
function ArrangementOverlay() {
  const { pxPerSecond } = useDawStore()
  const { sections } = useMidi(state => ({ sections: state.song.sections }))
  
  if (!sections.length) return null
  
  return (
    <div className="relative w-full h-full">
      {sections.map((section, index) => {
        const startX = section.startSec * pxPerSecond
        const width = (section.endSec - section.startSec) * pxPerSecond
        
        return (
          <div
            key={`section-${index}`}
            className="absolute top-0 h-full bg-blue-500/10 border-l border-r border-blue-500/30"
            style={{ left: startX, width }}
          >
            <span className="absolute top-0 left-1 text-xs text-blue-400 font-medium">
              {section.label}
            </span>
          </div>
        )
      })}
    </div>
  )
}

// MIDI Markers Overlay
function MidiMarkersOverlay() {
  const { pxPerSecond } = useDawStore()
  const { tracks } = useMidi(state => ({ tracks: state.song.tracks }))
  
  const allNotes = tracks.flatMap(track => 
    track.clips.flatMap(clip => 
      clip.notes.map(note => ({ ...note, trackKind: track.kind }))
    )
  )
  
  if (!allNotes.length) return null
  
  return (
    <div className="relative w-full h-full">
      {allNotes.slice(0, 100).map((note, index) => { // Limit for performance
        const x = (note.t0 / 480) * pxPerSecond // Rough conversion
        const color = note.trackKind === 'drums' ? 'red' : 
                     note.trackKind === 'bass' ? 'green' : 'blue'
        
        return (
          <div
            key={`note-${index}`}
            className={`absolute top-0 w-1 h-full bg-${color}-500/60`}
            style={{ left: x }}
          />
        )
      })}
    </div>
  )
}

// Helper function to get current BPM at a given time
function getCurrentBpm(tempoMap: any[], time: number): number {
  let currentBpm = 120
  
  for (const point of tempoMap) {
    if (point.tSec <= time) {
      currentBpm = point.bpm
    } else {
      break
    }
  }
  
  return currentBpm
}
