const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

const DATA_FILE = path.join(__dirname, 'data.json');

// Read existing data
function loadData() {
  try {
    if (fs.existsSync(DATA_FILE)) {
      return JSON.parse(fs.readFileSync(DATA_FILE, 'utf-8'));
    }
  } catch (e) { console.error('Load error:', e.message); }
  return [];
}

// Save data
function saveData(data) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2), 'utf-8');
}

// Serve frontend
app.use(express.static(path.join(__dirname, 'public')));

// Submit a survey response
app.post('/api/submit', (req, res) => {
  try {
    const data = loadData();
    const submission = {
      id: Date.now().toString(36) + Math.random().toString(36).substr(2, 6),
      timestamp: new Date().toISOString(),
      answers: req.body.answers || {},
    };
    data.push(submission);
    saveData(data);
    console.log(`[OK] New submission #${data.length}, id=${submission.id}`);
    res.json({ success: true, id: submission.id, total: data.length });
  } catch (e) {
    console.error('Submit error:', e);
    res.status(500).json({ success: false, error: e.message });
  }
});

// Get all submissions (admin)
app.get('/api/submissions', (req, res) => {
  try {
    const data = loadData();
    res.json({ total: data.length, submissions: data });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// Get submission count
app.get('/api/count', (req, res) => {
  const data = loadData();
  res.json({ total: data.length });
});

// Clear all data (admin)
app.post('/api/clear', (req, res) => {
  saveData([]);
  console.log('[OK] All data cleared');
  res.json({ success: true });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Survey server running on port ${PORT}`);
  console.log(`Data file: ${DATA_FILE}`);
});
