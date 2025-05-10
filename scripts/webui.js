// webui.js: SecuLite WebUI Features

function updateScanStatus() {
  fetch('http://localhost:5000/status')
    .then(r => r.text())
    .then(txt => {
      const el = document.getElementById('scan-status');
      if (el) el.innerText = txt;
    })
    .catch(() => {
      const el = document.getElementById('scan-status');
      if (el) el.innerText = 'Status nicht verfügbar.';
    });
}

function triggerScan() {
  fetch('http://localhost:5000/scan', {method: 'POST'})
    .then(r => {
      if (r.status === 202) {
        alert('Scan gestartet!');
      } else if (r.status === 409) {
        alert('Scan läuft bereits!');
      } else {
        alert('Fehler beim Starten des Scans.');
      }
      updateScanStatus();
    })
    .catch(() => alert('Fehler beim Verbinden mit dem Scan-Service.'));
}

document.addEventListener('DOMContentLoaded', function() {
  const scanBtn = document.getElementById('scan-btn');
  const statusBtn = document.getElementById('status-btn');
  if (scanBtn) scanBtn.onclick = triggerScan;
  if (statusBtn) statusBtn.onclick = updateScanStatus;
  updateScanStatus();
}); 