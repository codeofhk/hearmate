// content.js (simplified for clarity)

console.log('[Content] Script loaded');

if (window.__HearMateInjected) {
  console.log('[Content] Already injected, skipping');
} else {
  window.__HearMateInjected = true;

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    console.log('[Content] Received message:', msg.type);

    if (msg.type === 'CAPTURE_READY') {
      handleCaptureReady();
      sendResponse({ ok: true });
    } else if (msg.type === 'SERVER_MESSAGE') {
      handleServerMessage(msg.data);
      sendResponse({ ok: true });
    } else if (msg.type === 'STOP_CAPTURE') {
      handleStopCapture();
      sendResponse({ ok: true });
    } else if (msg.type === 'FINAL_TEXT') {
      handleFinalText(msg.text);
      sendResponse({ ok: true });
    }
  });

  createOverlay();
  console.log('[Content] Initialization complete');
}

function createOverlay() {
  const wrapper = document.createElement('div');
  wrapper.id = 'hear-mate-overlay';
  wrapper.innerHTML = `
    <style>
      #hear-mate-overlay {
        position: fixed;
        right: 12px;
        bottom: 12px;
        z-index: 2147483647;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      }
      .hm-panel {
        background: rgba(0, 0, 0, 0.85);
        color: #fff;
        padding: 12px;
        border-radius: 8px;
        width: 360px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      }
      #hm-captions {
        background: #fff;
        color: #111;
        padding: 10px;
        border-radius: 6px;
        min-height: 60px;
        max-height: 120px;
        overflow-y: auto;
        margin-bottom: 8px;
        font-size: 14px;
        line-height: 1.4;
      }
      #hm-status {
        color: #4ade80;
        font-size: 12px;
        text-align: center;
      }
    </style>
    <div class="hm-panel">
      <div id="hm-captions" aria-live="polite">Waiting...</div>
      <div id="hm-status">Ready</div>
    </div>
  `;
  document.body.appendChild(wrapper);
  console.log('[Content] Overlay created');
}

async function handleCaptureReady() {
  console.log('[Content] Capture ready, starting audio stream');
  const captionsEl = document.getElementById('hm-captions');
  const statusEl = document.getElementById('hm-status');

  try {
    console.log('[Content] Requesting microphone access...');
    const stream = await navigator.mediaDevices.getUserMedia({ 
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false
      },
      video: false 
    });

    console.log('[Content] Audio stream acquired');
    statusEl.textContent = 'Recording...';

    // Use AudioContext to get raw PCM audio
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const sourceNode = audioContext.createMediaStreamSource(stream);
    const analyserNode = audioContext.createAnalyser();
    sourceNode.connect(analyserNode);

    // Create ScriptProcessor for raw audio
    const scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
    
    scriptProcessor.onaudioprocess = (event) => {
      const inputData = event.inputBuffer.getChannelData(0);
      
      // Convert float32 to int16
      const int16Data = new Int16Array(inputData.length);
      for (let i = 0; i < inputData.length; i++) {
        int16Data[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7fff;
      }

      // Send to background
      chrome.runtime.sendMessage({
        type: 'AUDIO_CHUNK',
        chunk: Array.from(int16Data)
      }, (response) => {
        if (chrome.runtime.lastError) {
          console.error('[Content] Send error:', chrome.runtime.lastError);
        }
      });
    };

    sourceNode.connect(scriptProcessor);
    scriptProcessor.connect(audioContext.destination);

    window.__HearMateAudioContext = audioContext;
    window.__HearMateStream = stream;

    console.log('[Content] Recording started with raw PCM audio');

  } catch (err) {
    console.error('[Content] Error:', err.message);
    captionsEl.textContent = 'Error: ' + err.message;
    statusEl.textContent = 'Failed';
  }
}

function handleServerMessage(data) {
  const captionsEl = document.getElementById('hm-captions');
  const statusEl = document.getElementById('hm-status');
  
  if (data.type === 'interim') {
    captionsEl.textContent = data.text;
  }
}

function handleFinalText(text) {
  const captionsEl = document.getElementById('hm-captions');
  const statusEl = document.getElementById('hm-status');
  
  console.log('[Content] Final text received:', text);
  
  captionsEl.innerHTML = `<div style="font-weight: bold; color: #000;">${escapeHtml(text)}</div>`;
  statusEl.textContent = 'Transcribed';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function handleStopCapture() {
  console.log('[Content] Stopping capture');
  
  if (window.__HearMateAudioContext) {
    window.__HearMateAudioContext.close();
  }
  
  if (window.__HearMateStream) {
    window.__HearMateStream.getTracks().forEach(track => {
      console.log('[Content] Stopping track:', track.kind);
      track.stop();
    });
  }

  const captionsEl = document.getElementById('hm-captions');
  const statusEl = document.getElementById('hm-status');
  if (captionsEl) captionsEl.textContent = 'Stopped';
  if (statusEl) statusEl.textContent = 'Stopped';
}
