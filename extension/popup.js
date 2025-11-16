const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const serverUrlInput = document.getElementById('serverUrl');
const asrProvider = document.getElementById('asrProvider');
const consent = document.getElementById('consent');
const statusDiv = document.getElementById('status');

let currentTabId = null;
let isRecording = false;

// Load saved settings
chrome.storage.local.get(['serverUrl', 'asrProvider'], (result) => {
  if (result.serverUrl) serverUrlInput.value = result.serverUrl;
  if (result.asrProvider) asrProvider.value = result.asrProvider;
});

// Save settings on change
serverUrlInput.addEventListener('change', () => {
  chrome.storage.local.set({ serverUrl: serverUrlInput.value });
});

asrProvider.addEventListener('change', () => {
  chrome.storage.local.set({ asrProvider: asrProvider.value });
});

// Check if recording is already active when popup opens
chrome.runtime.sendMessage({ type: 'GET_STATUS' }, (response) => {
  if (response?.tabId) {
    currentTabId = response.tabId;
    isRecording = true;
    updateUI();
  }
});

function updateUI() {
  if (isRecording) {
    startBtn.disabled = true;
    stopBtn.disabled = false;
    statusDiv.textContent = 'Status: Recording';
    statusDiv.classList.add('running');
  } else {
    startBtn.disabled = false;
    stopBtn.disabled = true;
    statusDiv.textContent = 'Status: Ready';
    statusDiv.classList.remove('running');
  }
}

startBtn.onclick = async () => {
  if (!consent.checked) {
    statusDiv.textContent = 'Status: Please check consent';
    statusDiv.classList.add('error');
    return;
  }

  const serverUrl = serverUrlInput.value.trim();
  if (!serverUrl) {
    statusDiv.textContent = 'Status: Enter server URL';
    statusDiv.classList.add('error');
    return;
  }

  statusDiv.textContent = 'Status: Starting...';
  statusDiv.classList.remove('error', 'running');

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    currentTabId = tab.id;
    
    console.log('[Popup] Active tab ID:', currentTabId);

    // Inject content script
    try {
      await chrome.scripting.executeScript({
        target: { tabId: currentTabId },
        files: ['content.js']
      });
      console.log('[Popup] Content script injected');
    } catch (err) {
      console.error('[Popup] Failed to inject content script:', err);
    }

    // Wait for content script
    await new Promise(resolve => setTimeout(resolve, 500));

    // Send START message
    const response = await chrome.runtime.sendMessage({
      type: 'START_CAPTURE',
      tabId: currentTabId,
      serverUrl: serverUrl,
      asrProvider: asrProvider.value
    });

    if (response?.error) {
      statusDiv.textContent = 'Status: Error - ' + response.error;
      statusDiv.classList.add('error');
      isRecording = false;
    } else {
      isRecording = true;
      statusDiv.textContent = 'Status: Recording';
      statusDiv.classList.add('running');
    }
    
    updateUI();
  } catch (err) {
    console.error('Error starting capture:', err);
    statusDiv.textContent = 'Status: Error - ' + err.message;
    statusDiv.classList.add('error');
    isRecording = false;
    updateUI();
  }
};

stopBtn.onclick = async () => {
  statusDiv.textContent = 'Status: Stopping...';
  statusDiv.classList.remove('running', 'error');

  try {
    if (!currentTabId) {
      throw new Error('No active recording');
    }
    
    const response = await chrome.runtime.sendMessage({
      type: 'STOP_CAPTURE',
      tabId: currentTabId
    });

    if (response?.error) {
      statusDiv.textContent = 'Status: Error - ' + response.error;
      statusDiv.classList.add('error');
    } else {
      statusDiv.textContent = 'Status: Stopped';
    }
    
    isRecording = false;
    currentTabId = null;
    updateUI();
  } catch (err) {
    console.error('Error stopping capture:', err);
    statusDiv.textContent = 'Status: Error - ' + err.message;
    statusDiv.classList.add('error');
  }
};

// Update UI on load
updateUI();
