# -*- coding: utf-8 -*-
"""Transform the questionnaire HTML to use server API instead of localStorage."""
import re

src = r'C:\Users\Administrator\Desktop\课设\学府路地铁站换乘衔接调查问卷系统\index.html'
dst = r'C:\Users\Administrator\Desktop\课设\survey-server\public\index.html'

with open(src, 'r', encoding='utf-8') as f:
    html = f.read()

# === 1. Replace state management block ===
old_block_start = html.find('// State Management')
old_block_end = html.find('function resetSurvey()')
if old_block_end > 0:
    # Find end of resetSurvey function
    idx = html.find('\n}', old_block_end)
    if idx > 0:
        old_block_end = idx + 2

server_api = '''// Server API (data sent to server, not localStorage)
const API_BASE = window.location.origin;

async function apiSubmit(answers) {
  const res = await fetch(API_BASE + '/api/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  });
  return res.json();
}

async function apiGetSubmissions() {
  const res = await fetch(API_BASE + '/api/submissions');
  return res.json();
}

async function apiClear() {
  const res = await fetch(API_BASE + '/api/clear', { method: 'POST' });
  return res.json();
}

// Local state only for UI (data lives on server)
const STATE_KEY = 'xuefulu_survey_state';
function loadState() {
  try { return JSON.parse(localStorage.getItem(STATE_KEY) || '{"step":"welcome","answers":{},"currentQ":0}'); }
  catch { return { step: 'welcome', answers: {}, currentQ: 0 }; }
}
function saveState(state) { localStorage.setItem(STATE_KEY, JSON.stringify(state)); }
let appState = loadState();
let responses = [];

function resetSurvey() {
  appState = { step: 'welcome', answers: {}, currentQ: 0 };
  saveState(appState);
  render();
}
'''

html = html[:old_block_start] + server_api + html[old_block_end:]
print('1. State management -> server API')

# === 2. Replace submitSurvey ===
old_submit = '''function submitSurvey() {
  const response = {
    id: Date.now().toString(36) + Math.random().toString(36).substr(2, 6),
    timestamp: new Date().toISOString(),
    answers: { ...appState.answers },
  };
  responses = loadResponses();
  responses.push(response);
  saveResponses(responses);
  appState.step = 'complete';
  appState.responseId = response.id;
  saveState(appState);
  render();
  window.scrollTo({ top: 0, behavior: 'smooth' });
  showToast('✅ 问卷提交成功！感谢您的参与！');
}'''

new_submit = '''async function submitSurvey() {
  appState.step = 'pending';
  saveState(appState);
  render();
  showToast('\u{1F4E4} 正在提交到服务器...');
  try {
    const result = await apiSubmit(appState.answers);
    if (result.success) {
      appState.step = 'complete';
      appState.responseId = result.id;
      saveState(appState);
      render();
      window.scrollTo({ top: 0, behavior: 'smooth' });
      showToast('✅ 提交成功！数据已同步到服务器 (#' + result.total + ')');
    } else {
      showToast('❌ 提交失败，请重试');
    }
  } catch(e) {
    showToast('❌ 网络错误: ' + e.message);
  }
}'''

if old_submit in html:
    html = html.replace(old_submit, new_submit)
    print('2. submitSurvey -> async API submit')
else:
    print('2. WARNING: submitSurvey not matched')

# === 3. Fix loadResponses/saveResponses references ===
html = html.replace('responses = loadResponses();', 'responses = []; // loaded from server')
html = html.replace('saveResponses(responses);', '// saved on server')
html = html.replace('saveResponses(responses)', '// saved on server')
print('3. Removed localStorage load/save calls')

# === 4. Fix openAdmin to use async ===
old_open = 'function openAdmin() {\n  adminOpen = true;\n  responses = loadResponses();'
new_open = 'async function openAdmin() {\n  adminOpen = true;\n  try {\n    const d = await apiGetSubmissions();\n    responses = d.submissions || [];\n  } catch(e) {\n    responses = [];\n    showToast(\'\\u26A0\\uFE0F 无法连接服务器\');\n    return;\n  }'
html = html.replace(old_open, new_open)
print('4. openAdmin -> async server fetch')

# === 5. Fix clearAllData ===
old_clear = '''function clearAllData() {
  if (confirm('确定要清空所有问卷数据吗？此操作不可恢复！')) {
    responses = [];
    saveResponses(responses);
    closeAdmin();
    showToast('\u{1F5D1} 所有数据已清空');
  }
}'''
new_clear = '''async function clearAllData() {
  if (confirm('确定要清空服务器上的所有问卷数据吗？此操作不可恢复！')) {
    try {
      await apiClear();
      responses = [];
      closeAdmin();
      showToast('\u{1F5D1} 服务器数据已清空');
    } catch(e) {
      showToast('❌ 操作失败');
    }
  }
}'''
if old_clear in html:
    html = html.replace(old_clear, new_clear)
    print('5. clearAllData -> API clear')
else:
    print('5. WARNING: clearAllData not matched')

# === 6. Fix completion page text ===
html = html.replace(
    '面对面发放',
    '线上发放（通过网站链接分享）'
)
html = html.replace(
    '当前已收集 <b style="color:var(--primary);">${responses.length}</b> 份问卷数据',
    '数据实时同步至服务器，管理面板可实时查看所有提交'
)
print('6. Updated completion page text')

# === 7. Add server status indicator ===
# CSS
status_css = '.server-status{position:fixed;top:10px;right:10px;z-index:400;font-size:11px;padding:4px 10px;border-radius:100px;background:white;box-shadow:0 1px 4px rgba(0,0,0,0.1)}.server-status.online{color:#0d904f}.server-status.offline{color:#d93025}'
html = html.replace(
    '/* ========== Print ========== */',
    status_css + '\n/* ========== Print ========== */'
)

# HTML element
html = html.replace(
    '<div class="app-container" id="app">',
    '<div class="server-status" id="serverStatus">🔗 连接中...</div>\n<div class="app-container" id="app">'
)

# JS init
init_js = '''
async function checkServer() {
  try {
    const r = await fetch(API_BASE + '/api/count');
    const d = await r.json();
    document.getElementById('serverStatus').textContent = '🟢 在线 · ' + d.total + '条数据';
    document.getElementById('serverStatus').className = 'server-status online';
  } catch(e) {
    document.getElementById('serverStatus').textContent = '🔴 离线';
    document.getElementById('serverStatus').className = 'server-status offline';
  }
}
checkServer();
setInterval(checkServer, 30000);
'''
html = html.replace(
    'render();\nconsole.log',
    init_js + '\nrender();\nconsole.log'
)
print('7. Added server status indicator')

# === 8. Rewrite mock data generator ===
old_mock_start = html.find('function addMockData()')
old_mock_end = html.find('function randomPick', old_mock_start) if 'function randomPick' in html[old_mock_start:] else len(html)
if old_mock_end < old_mock_start:
    old_mock_end = html.find('// ============================================================', old_mock_start + 100)

new_mock = '''async function addMockData() {
  const count = 30;
  let ok = 0;
  showToast('\\u{1F3B2} 正在生成模拟数据...');
  const pools = {
    g: ['男','女'],
    a: ['18~25岁','18~25岁','18~25岁','18~25岁','18~25岁','18~25岁','18~25岁','18~25岁','18~25岁','18~25岁','26~40岁','26~40岁','26~40岁','26~40岁','26~40岁','26~40岁','26~40岁','26~40岁','41~60岁','41~60岁','41~60岁','41~60岁','41~60岁','60岁以上','60岁以上','18岁以下','18岁以下','18~25岁','18~25岁','18~25岁'],
    o: ['学生','学生','学生','学生','学生','学生','学生','学生','学生','学生','学生','学生','上班族','上班族','上班族','上班族','上班族','上班族','上班族','上班族','上班族','上班族','自由职业','自由职业','自由职业','自由职业','退休人员','退休人员','退休人员','其他'],
    p: ['通勤（上下学/上下班）','通勤（上下学/上下班）','通勤（上下学/上下班）','通勤（上下学/上下班）','通勤（上下学/上下班）','通勤（上下学/上下班）','通勤（上下学/上下班）','通勤（上下学/上下班）','通勤（上下学/上下班）','通勤（上下学/上下班）','购物消费','购物消费','购物消费','购物消费','购物消费','购物消费','购物消费','休闲娱乐','休闲娱乐','休闲娱乐','休闲娱乐','休闲娱乐','休闲娱乐','探亲访友','探亲访友','探亲访友','探亲访友','其他','其他','其他'],
    arr: ['步行','步行','步行','步行','步行','步行','步行','常规公交','常规公交','常规公交','常规公交','常规公交','常规公交','常规公交','常规公交','常规公交','出租车/网约车','出租车/网约车','出租车/网约车','出租车/网约车','私家车（停放在附近停车场）','私家车（停放在附近停车场）','共享单车','共享单车','共享单车','共享单车','自行车/电动自行车','自行车/电动自行车','其他','其他'],
    t: ['步行','步行','步行','步行','步行','步行','步行','步行','常规公交','常规公交','常规公交','常规公交','常规公交','常规公交','常规公交','常规公交','常规公交','出租车/网约车','出租车/网约车','出租车/网约车','出租车/网约车','出租车/网约车','私家车（停车场取车）','私家车（停车场取车）','共享单车','共享单车','共享单车','共享单车','共享单车','不换乘（目的地即在站点周边）'],
    dep: ['周边高校（黑大/理工/师大附中等）','周边高校（黑大/理工/师大附中等）','周边高校（黑大/理工/师大附中等）','周边高校（黑大/理工/师大附中等）','周边高校（黑大/理工/师大附中等）','周边高校（黑大/理工/师大附中等）','周边高校（黑大/理工/师大附中等）','周边高校（黑大/理工/师大附中等）','周边高校（黑大/理工/师大附中等）','周边高校（黑大/理工/师大附中等）','周边居住小区','周边居住小区','周边居住小区','周边居住小区','周边居住小区','周边居住小区','周边居住小区','周边居住小区','周边居住小区','周边居住小区','凯德广场等商业区','凯德广场等商业区','凯德广场等商业区','凯德广场等商业区','凯德广场等商业区','凯德广场等商业区','其他区域（经公交/出租等接驳到达）','其他区域（经公交/出租等接驳到达）','其他区域（经公交/出租等接驳到达）','其他区域（经公交/出租等接驳到达）'],
    walk: ['100米以内（约1分钟）','100米以内（约1分钟）','100米以内（约1分钟）','100米以内（约1分钟）','100米以内（约1分钟）','100米以内（约1分钟）','100~200米（约2~3分钟）','100~200米（约2~3分钟）','100~200米（约2~3分钟）','100~200米（约2~3分钟）','100~200米（约2~3分钟）','100~200米（约2~3分钟）','100~200米（约2~3分钟）','100~200米（约2~3分钟）','200~400米（约3~5分钟）','200~400米（约3~5分钟）','200~400米（约3~5分钟）','200~400米（约3~5分钟）','200~400米（约3~5分钟）','200~400米（约3~5分钟）','200~400米（约3~5分钟）','200~400米（约3~5分钟）','400米以上（5分钟以上）','400米以上（5分钟以上）','400米以上（5分钟以上）','400米以上（5分钟以上）','无所谓','无所谓','无所谓','无所谓'],
    bus: ['50米以内','50米以内','50米以内','50米以内','50米以内','50~100米','50~100米','50~100米','50~100米','50~100米','50~100米','50~100米','50~100米','50~100米','100~150米','100~150米','100~150米','100~150米','100~150米','100~150米','100~150米','150~200米','150~200米','150~200米','150~200米','150~200米','200米以上也可接受','200米以上也可接受','200米以上也可接受','200米以上也可接受'],
  };
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
  for (let i = 0; i < count; i++) {
    const ans = {};
    ans[1] = pick(pools.g); ans[2] = pick(pools.a); ans[3] = pick(pools.o);
    ans[4] = pick(pools.p); ans[5] = pick(pools.arr); ans[6] = pick(pools.dep);
    ans[7] = pick(pools.t); ans[8] = pick(pools.walk); ans[9] = pick(pools.bus);
    const rn = () => Math.max(1, Math.min(5, Math.round(2.5 + (Math.random()-0.5)*2.5)));
    ans[10] = rn(); ans[11] = rn(); ans[12] = rn(); ans[13] = rn();
    ans[14] = pick([['无明显问题'],['无明显问题'],['公交站距离地铁口过远'],['无明显问题'],['换乘路线缺少引导标识'],['无明显问题'],['人行道过窄影响通行'],['无明显问题'],['出租车/网约车停靠混乱'],['换乘步行距离过长']]);
    ans[15] = '';
    try {
      const r = await apiSubmit(ans);
      if (r.success) ok++;
    } catch(e) {}
  }
  closeAdmin();
  await openAdmin();
  showToast('\\u{1F3B2} 已生成 ' + ok + '/' + count + ' 份模拟数据');
}
'''

html = html[:old_mock_start] + new_mock + html[old_mock_end:]
print('8. Mock data -> server API')

# === Write output ===
with open(dst, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Done! Written to {dst}')
