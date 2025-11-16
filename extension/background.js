// background.js
const connections = new Map();
let activeTabId = null;

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  const tabId = msg.tabId || sender.tab?.id;

  if (msg.type === 'GET_STATUS') {
    sendResponse({ tabId: activeTabId });
    return true;
  }

  if (!tabId) {
    console.error('[BG] Message received without tab ID:', msg);
    sendResponse({ error: 'No tab ID provided' });
    return true;
  }

  console.log('[BG] Message from tab', tabId, ':', msg.type);

  if (msg.type === 'START_CAPTURE') {
    handleStartCapture(tabId, msg.serverUrl, msg.asrProvider)
      .then(() => {
        activeTabId = tabId;
        sendResponse({ ok: true, message: 'Capture started' });
      })
      .catch(error => sendResponse({ error: error.message }));
    return true;
  }

  if (msg.type === 'STOP_CAPTURE') {
    handleStopCapture(tabId)
      .then(async () => {
        // Get server URL from storage
        chrome.storage.local.get(['serverUrl'], async (result) => {
          if (result.serverUrl) {
            try {
              // Call transcribe endpoint
              const response = await fetch(result.serverUrl.replace('/ws', '/transcribe'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
              });
              const data = await response.json();
              
              console.log('[BG] Transcription result:', data.text);
              
              // Send final text to content script
              chrome.tabs.sendMessage(tabId, {
                type: 'FINAL_TEXT',
                text: data.text
              }).catch(err => console.error('[BG] Failed to send final text:', err));
            } catch (err) {
              console.error('[BG] Transcribe request failed:', err);
            }
          }
          
          activeTabId = null;
          sendResponse({ ok: true, message: 'Capture stopped' });
        });
      })
      .catch(error => sendResponse({ error: error.message }));
    return true;
  }

  if (msg.type === 'AUDIO_CHUNK') {
    const conn = connections.get(tabId);
    if (conn && conn.ws && conn.ws.readyState === WebSocket.OPEN) {
      try {
        const chunk = new Uint8Array(msg.chunk);
        conn.ws.send(chunk);
      } catch (err) {
        console.error('[BG] Failed to send audio chunk:', err);
      }
    }
    sendResponse({ ok: true });
    return true;
  }
});

async function handleStartCapture(tabId, serverUrl, asrProvider) {
  console.log(`[BG] Starting capture for tab ${tabId}, server: ${serverUrl}`);

  if (connections.has(tabId)) {
    throw new Error('Capture already running for this tab');
  }

  const ws = new WebSocket(serverUrl);
  ws.binaryType = 'arraybuffer';

  return new Promise((resolve, reject) => {
    ws.onopen = () => {
      console.log('[BG] WebSocket connected');
      
      chrome.tabs.sendMessage(tabId, { 
        type: 'CAPTURE_READY',
        wsReady: true 
      }).catch(err => console.error('[BG] Failed to notify content script:', err));

      connections.set(tabId, { ws });
      resolve();
    };

    ws.onerror = (event) => {
      console.error('[BG] WebSocket error:', event);
      reject(new Error('WebSocket connection failed'));
    };

    ws.onclose = () => {
      console.log('[BG] WebSocket closed');
      connections.delete(tabId);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        chrome.tabs.sendMessage(tabId, {
          type: 'SERVER_MESSAGE',
          data: data
        }).catch(err => console.error('[BG] Failed to forward message:', err));
      } catch (err) {
        console.error('[BG] Failed to parse server message:', err);
      }
    };

    setTimeout(() => {
      if (ws.readyState !== WebSocket.OPEN) {
        ws.close();
        reject(new Error('WebSocket connection timeout'));
      }
    }, 5000);
  });
}

async function handleStopCapture(tabId) {
  console.log(`[BG] Stopping capture for tab ${tabId}`);
  
  const conn = connections.get(tabId);
  if (!conn) {
    throw new Error('No active capture for this tab');
  }

  if (conn.ws && conn.ws.readyState === WebSocket.OPEN) {
    conn.ws.close();
  }

  connections.delete(tabId);
}

chrome.tabs.onRemoved.addListener((tabId) => {
  if (connections.has(tabId)) {
    handleStopCapture(tabId).catch(err => console.error('[BG] Cleanup failed:', err));
    if (activeTabId === tabId) {
      activeTabId = null;
    }
  }
});
