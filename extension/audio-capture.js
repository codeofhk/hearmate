// audio-capture.js
export async function startAudioStream(serverUrl, wsProtocol = 'hear-mate-v1', onStatus = () => {}, onError = () => {}) {
  // Try tabCapture first
  const constraints = { audio: true, video: false };
  let stream = null;

  try {
    stream = await new Promise((resolve, reject) => {
      // attempt tabCapture (chrome API in content script isn't available; use chrome.tabCapture via background)
      // Instead request content script consumer to call chrome.tabCapture in privileged context.
      // As a fallback, use getUserMedia
      navigator.mediaDevices.getUserMedia({ audio: true }).then(resolve).catch(reject);
    });
  } catch (err) {
    onError('Could not capture audio: ' + err.message);
    throw err;
  }

  // create WebSocket
  const ws = new WebSocket(serverUrl, wsProtocol);
  ws.binaryType = 'arraybuffer';

  ws.onopen = () => {onStatus('ws-open'); console.log("[HearMate] WebSocket Connected: ",serverUrl)};
  ws.onclose = () => onStatus('ws-closed');
  ws.onerror = (e) => onError(e);

  // use MediaRecorder to produce small opus blobs
  const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus', audioBitsPerSecond: 128000 });
  recorder.ondataavailable = (ev) => {
    if (ev.data && ev.data.size > 0 && ws.readyState === WebSocket.OPEN) {
      console.log("[HearMate] Sending chunk:", ev.data.size, "bytes");
      ev.data.arrayBuffer().then(buffer => ws.send(buffer));
    }
  };
  recorder.onerror = (e) => onError(e);

  recorder.start(200); // emit every 200ms

  return {
    stop: () => {
      try { recorder.stop(); } catch(e) {}
      stream.getTracks().forEach(t => t.stop());
      try { ws.close(); } catch(e) {}
    },
    ws
  };
}
