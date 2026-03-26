// Auto-inject audio debugging
(function() {
  console.log("🔍 Audio Debugger Loading...");
  
  // Wait for page to load
  setTimeout(() => {
    const count = document.querySelectorAll("audio").length;
    console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
    console.log(`🔢 AUDIO ELEMENTS FOUND: ${count}`);
    console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n`);
    
    if (count === 0) {
      console.log("✅ No audio elements yet (will be created when you load a file)");
    } else if (count === 1) {
      console.log("✅ GOOD - Only 1 audio element");
    } else {
      console.log(`⚠️  WARNING - ${count} audio elements detected!`);
      console.log("This is likely causing the distortion.\n");
    }
    
    document.querySelectorAll("audio").forEach((a, i) => {
      console.log(`Audio #${i}:`, {
        src: a.src || "(empty)",
        paused: a.paused,
        volume: a.volume,
        muted: a.muted,
        currentTime: a.currentTime
      });
    });
    
    // Install play hook
    if (!window.__playHookInstalled) {
      window.__playHookInstalled = true;
      const origPlay = HTMLMediaElement.prototype.play;
      HTMLMediaElement.prototype.play = function() {
        console.log("\n▶️  PLAY CALLED:");
        console.log("   src:", this.src);
        console.log("   volume:", this.volume);
        console.log("   playbackRate:", this.playbackRate);
        console.log("   preservesPitch:", this.preservesPitch);
        console.log("   Stack trace:", new Error().stack);
        
        // Log properties every second during playback
        const elem = this;
        let counter = 0;
        const interval = setInterval(() => {
          if (elem.paused || counter > 3) {
            clearInterval(interval);
            return;
          }
          console.log(`\n⏱️  [${counter}s] Audio status:`, {
            currentTime: elem.currentTime.toFixed(2),
            volume: elem.volume,
            playbackRate: elem.playbackRate,
            paused: elem.paused
          });
          counter++;
        }, 1000);
        
        return origPlay.apply(this, arguments);
      };
      console.log("\n✅ Play hook installed - audio play calls will be logged");
    }
    
    // Check for Tone.js and AudioContext
    console.log("\n🔍 Checking for audio processing layers...");
    try {
      if (window.Tone) {
        console.log("⚠️  Tone.js DETECTED:");
        console.log("   Transport state:", window.Tone.Transport.state);
        console.log("   Transport.seconds:", window.Tone.Transport.seconds);
        console.log("   Context state:", window.Tone.context?.state);
        console.log("   Context.currentTime:", window.Tone.context?.currentTime);
        console.log("   Destination nodes:", window.Tone.Destination);
        
        // Check if destination has any connections
        if (window.Tone.context) {
          console.log("   AudioContext destination:", window.Tone.context.destination);
          console.log("   AudioContext.destination.channelCount:", window.Tone.context.destination.channelCount);
        }
      } else {
        console.log("✅ Tone.js not found");
      }
      
      const contexts = [];
      if (window.AudioContext) contexts.push("AudioContext");
      if (window.webkitAudioContext) contexts.push("webkitAudioContext");
      if (contexts.length > 0) {
        console.log("⚠️  Web Audio API available:", contexts.join(", "));
      }
    } catch (e) {
      console.log("Error checking audio layers:", e);
    }
    
    console.log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    console.log("Now click PLAY in the app and watch this console");
    console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
    
  }, 2000); // Wait 2 seconds for React to mount
  
})();
