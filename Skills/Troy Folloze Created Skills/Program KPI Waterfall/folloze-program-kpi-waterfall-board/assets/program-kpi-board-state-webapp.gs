const STATE_FOLDER_NAME = 'Folloze JDP Board State';

function doGet(e) {
  const params = e && e.parameter ? e.parameter : {};
  const action = params.action || 'health';
  if (action === 'load') {
    const result = loadBoardState_(params.boardKey || '');
    return jsonpResponse_(params.callback, result);
  }
  return jsonpResponse_(params.callback, {
    ok: true,
    message: 'Folloze JDP board state endpoint is running.'
  });
}

function doPost(e) {
  try {
    const params = e && e.parameter ? e.parameter : {};
    if ((params.action || 'save') !== 'save') {
      return textResponse_('Unsupported action');
    }
    const boardKey = params.boardKey || '';
    const payloadText = params.payload || '{}';
    const payload = JSON.parse(payloadText);
    saveBoardState_(boardKey, payloadText, payload);
    return textResponse_('Saved');
  } catch (err) {
    return textResponse_(`State save error: ${err && err.message ? err.message : String(err)}`);
  }
}

function saveBoardState_(boardKey, payloadText, payload) {
  if (!boardKey) throw new Error('Missing boardKey');
  const file = getOrCreateStateFile_(boardKey);
  file.setContent(payloadText);
  file.setDescription(JSON.stringify({
    boardKey,
    customerName: payload.customerName || 'Customer',
    updatedAt: payload.updatedAt || new Date().toISOString()
  }));
}

function loadBoardState_(boardKey) {
  if (!boardKey) return { ok: false, payload: null, message: 'Missing boardKey' };
  const file = findStateFile_(boardKey);
  if (!file) return { ok: true, payload: null, message: 'No state saved yet' };
  return {
    ok: true,
    payload: JSON.parse(file.getBlob().getDataAsString())
  };
}

function getOrCreateStateFile_(boardKey) {
  const existing = findStateFile_(boardKey);
  if (existing) return existing;
  const folder = getStateFolder_();
  return folder.createFile(stateFileName_(boardKey), '{}', MimeType.PLAIN_TEXT);
}

function findStateFile_(boardKey) {
  const folder = getStateFolder_();
  const files = folder.getFilesByName(stateFileName_(boardKey));
  return files.hasNext() ? files.next() : null;
}

function getStateFolder_() {
  const folders = DriveApp.getFoldersByName(STATE_FOLDER_NAME);
  return folders.hasNext() ? folders.next() : DriveApp.createFolder(STATE_FOLDER_NAME);
}

function stateFileName_(boardKey) {
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, boardKey)
    .map(byte => (byte < 0 ? byte + 256 : byte).toString(16).padStart(2, '0'))
    .join('');
  return `jdp-board-state-${digest}.json`;
}

function jsonpResponse_(callback, payload) {
  const body = callback
    ? `${callback}(${JSON.stringify(payload)});`
    : JSON.stringify(payload);
  return ContentService
    .createTextOutput(body)
    .setMimeType(callback ? ContentService.MimeType.JAVASCRIPT : ContentService.MimeType.JSON);
}

function textResponse_(body) {
  return ContentService
    .createTextOutput(body)
    .setMimeType(ContentService.MimeType.TEXT);
}
