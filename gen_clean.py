# -*- coding: utf-8 -*-
"""Generate a clean index.html with Supabase fetch API"""

# Read the original HTML (clean version from the questionnaire system)
with open(r'C:\Users\Administrator\Desktop\课设\学府路地铁站换乘衔接调查问卷系统\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# The API code to insert right after the main <script> tag
api_code = """
// ============================================================
// Supabase API (fetch-based, no external library needed)
// ============================================================
const SB_URL = 'https://ojrickkrhflqataggcyx.supabase.co';
const SB_KEY = 'sb_publishable_XoCCIoxm84_rhXEeHFogug_5-tmS8Bk';

async function sbInsert(answers) {
  const res = await fetch(SB_URL + '/rest/v1/responses', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'apikey': SB_KEY,
      'Authorization': 'Bearer ' + SB_KEY,
      'Prefer': 'return=representation'
    },
    body: JSON.stringify([{ data: answers }])
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function sbGetAll() {
  const res = await fetch(SB_URL + '/rest/v1/responses?select=*&order=created_at.desc', {
    headers: { 'apikey': SB_KEY, 'Authorization': 'Bearer ' + SB_KEY }
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function sbClear() {
  const res = await fetch(SB_URL + '/rest/v1/responses?id=gt.0', {
    method: 'DELETE',
    headers: { 'apikey': SB_KEY, 'Authorization': 'Bearer ' + SB_KEY }
  });
}

async function sbCount() {
  const res = await fetch(SB_URL + '/rest/v1/responses?select=count', {
    headers: { 'apikey': SB_KEY, 'Authorization': 'Bearer ' + SB_KEY }
  });
  if (!res.ok) return { count: '?' };
  return { count: (await res.json())[0]?.count || 0 };
}

// ============================================================
"""

# Insert API code after the opening <script> tag
html = html.replace('<script>\n', '<script>\n' + api_code, 1)

# =============================================================
# Now replace all the old functions with Supabase versions
# =============================================================

# 1. Replace submitSurvey
old = '''function submitSurvey() {
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

new = '''async function submitSurvey() {
  showToast('📤 提交中...');
  try {
    const data = await sbInsert(appState.answers);
    appState.step = 'complete';
    appState.responseId = data?.[0]?.id || '';
    saveState(appState);
    render();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    showToast('✅ 提交成功！已同步至云端');
  } catch(e) {
    showToast('❌ 无法连接云端服务器');
    console.error('Submit error:', e);
  }
}'''

if old in html:
    html = html.replace(old, new)
    print('[OK] submitSurvey')
else:
    print('[FAIL] submitSurvey not found')

# 2. Replace openAdmin's data loading
old2 = '''function openAdmin() {
  adminOpen = true;
  responses = loadResponses();'''
new2 = '''async function openAdmin() {
  adminOpen = true;
  try {
    const data = await sbGetAll();
    responses = (data || []).map(r => ({
      id: r.id,
      timestamp: r.created_at,
      answers: r.data || {},
    }));
  } catch(e) {
    responses = [];
    showToast('⚠️ 无法连接云端');
    return;
  }'''

if old2 in html:
    html = html.replace(old2, new2)
    print('[OK] openAdmin')
else:
    print('[FAIL] openAdmin not found')

# 3. Replace clearAllData
old3 = '''function clearAllData() {
  if (confirm('确定要清空所有问卷数据吗？此操作不可恢复！')) {
    responses = [];
    saveResponses(responses);
    closeAdmin();
    showToast('所有数据已清空');
  }
}'''
new3 = '''async function clearAllData() {
  if (confirm('确定要清空所有问卷数据吗？此操作不可恢复！')) {
    try {
      await sbClear();
      responses = [];
      closeAdmin();
      showToast('🗑 所有数据已清空');
    } catch(e) { showToast('❌ 操作失败'); }
  }
}'''
if old3 in html:
    html = html.replace(old3, new3)
    print('[OK] clearAllData')
else:
    print('[FAIL] clearAllData not found')

# 4. Replace renderComplete to show cloud info
html = html.replace(
    '📊 当前已收集 <b style="color:var(--primary);">${responses.length}</b> 份问卷数据',
    '📊 数据实时同步至云端数据库'
)

# 5. Update saveResponses/loadResponses calls
html = html.replace('responses = loadResponses();', '// loaded from cloud')
html = html.replace('saveResponses(responses);', '// saved to cloud')
html = html.replace('saveResponses(responses)', '// saved to cloud')

# 6. Update mock data to use sbInsert
html = html.replace(
    '''function addMockData() {
  const genders = ['男', '女'];
  const ages = ['18~25岁', '18~25岁', '18~25岁', '26~40岁', '26~40岁', '41~60岁', '18岁以下', '60岁以上'];''',
    '''async function addMockData() {
  showToast('🎲 生成模拟数据...');
  let ok = 0;
  const g = ['男','女'];'''
)

# Remove the old mock data body and replace with simple version
import re
# Find the old mock function end
start = html.find('async function addMockData()')
end = html.find('// ============================================================', start + 100)
if end < 0:
    end = html.find('function escapeHTML', start + 100)

if start > 0 and end > start:
    new_mock = '''async function addMockData() {
  showToast('🎲 生成模拟数据...');
  let ok = 0;
  const modes = ['步行','常规公交','出租车/网约车','共享单车','不换乘（目的地即在站点周边）'];
  for (let i = 0; i < 30; i++) {
    const ans = {
      1: ['男','女'][i%2],
      2: ['18~25岁','26~40岁','41~60岁'][i%3],
      3: ['学生','上班族','自由职业'][i%3],
      4: ['通勤（上下学/上下班）','购物消费','休闲娱乐'][i%3],
      5: ['步行','常规公交','出租车/网约车','共享单车'][i%4],
      6: ['周边高校（黑大/理工/师大附中等）','周边居住小区','凯德广场等商业区'][i%3],
      7: modes[i%5],
      8: ['100米以内','100~200米','200~400米','400米以上','无所谓'][i%5],
      9: ['50米以内','50~100米','100~150米','150~200米'][i%4],
      10: Math.max(1,Math.min(5,Math.round(2.5+(Math.random()-0.5)*2.5))),
      11: Math.max(1,Math.min(5,Math.round(2.5+(Math.random()-0.5)*2.5))),
      12: Math.max(1,Math.min(5,Math.round(2.5+(Math.random()-0.5)*2.5))),
      13: Math.max(1,Math.min(5,Math.round(2.5+(Math.random()-0.5)*2.5))),
      14: [['无明显问题'],['公交站距离地铁口过远'],['换乘路线缺少引导标识'],['无明显问题'],['人行道过窄影响通行']][i%5],
      15: ''
    };
    try { await sbInsert(ans); ok++; } catch(e) {}
  }
  closeAdmin(); await openAdmin();
  showToast('🎲 已生成 ' + ok + '/30 份');
}

'''
    html = html[:start] + new_mock + html[end:]
    print('[OK] addMockData')
else:
    print('[FAIL] addMockData boundary not found')

# Final check
remaining = html.count('supabase.from')
print(f'Remaining supabase.from: {remaining}')

# Write output
out = r'C:\Users\Administrator\Desktop\课设\survey-server\index.html'
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Written to {out}')
