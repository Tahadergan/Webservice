"""
سيرفر الإشعارات - جاهز للنشر على Render.com مجاناً

WebSocket + HTTP على نفس المنفذ
"""

import asyncio
import json
import os
from aiohttp import web

# قائمة الأجهزة المتصلة
connected_clients = set()

# ======================================
# WebSocket Handler
# ======================================
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    connected_clients.add(ws)
    print(f"✅ جهاز اتصل (المتصلون: {len(connected_clients)})")

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                print(f"📩 رسالة: {msg.data}")
            elif msg.type == web.WSMsgType.ERROR:
                print(f"❌ خطأ: {ws.exception()}")
    finally:
        connected_clients.discard(ws)
        print(f"❌ جهاز انقطع (المتصلون: {len(connected_clients)})")

    return ws

# ======================================
# HTTP: إرسال إشعار
# ======================================
async def send_notification(request):
    try:
        data = await request.json()
    except:
        return web.json_response({"success": False, "error": "Invalid JSON"}, status=400)

    if "title" not in data:
        return web.json_response({"success": False, "error": "title مطلوب"}, status=400)

    message = json.dumps({
        "title": data.get("title", "إشعار"),
        "body": data.get("body", ""),
        "action": data.get("action", "show_message"),
        "data": data.get("data", {})
    }, ensure_ascii=False)

    sent = 0
    disconnected = set()

    for client in connected_clients.copy():
        try:
            await client.send_str(message)
            sent += 1
        except:
            disconnected.add(client)

    connected_clients.difference_update(disconnected)

    print(f"📤 تم الإرسال لـ {sent} جهاز")
    return web.json_response({"success": True, "sent_to": sent})

# ======================================
# HTTP: حالة السيرفر
# ======================================
async def status(request):
    return web.json_response({
        "connected_clients": len(connected_clients),
        "status": "running"
    })

# ======================================
# HTTP: Health Check (مطلوب لـ Render)
# ======================================
async def health_check(request):
    return web.Response(text="OK")

# ======================================
# HTTP: صفحة إرسال الإشعارات
# ======================================
async def home(request):
    html = """<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>لوحة إرسال الإشعارات</title>
<style>
* { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }
body { max-width: 500px; margin: 30px auto; padding: 16px; background: #0a0f1c; color: #e2e8f0; }
h1 { font-size: 22px; margin-bottom: 8px; }
.info { background: #1e293b; padding: 12px; border-radius: 10px; margin-bottom: 16px; text-align: center; }
.info strong { color: #22d3ee; font-size: 24px; }
.card { background: #111827; padding: 20px; border-radius: 14px; border: 1px solid #1e293b; }
label { display: block; font-size: 13px; color: #94a3b8; margin-bottom: 4px; font-weight: bold; }
input, textarea, select { width: 100%; padding: 10px; margin-bottom: 14px; background: #0a0f1c; border: 1px solid #1e293b; border-radius: 8px; color: #e2e8f0; font-size: 14px; }
input:focus, textarea:focus, select:focus { outline: none; border-color: #22d3ee; }
button { width: 100%; padding: 13px; background: linear-gradient(135deg, #22d3ee, #6366f1); color: #fff; border: none; border-radius: 10px; font-size: 16px; font-weight: bold; cursor: pointer; }
button:hover { opacity: 0.9; }
.result { margin-top: 12px; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; }
.ok { background: #064e3b; color: #34d399; }
.err { background: #450a0a; color: #f87171; }
select { direction: ltr; }
</style>
</head>
<body>
<h1>📡 لوحة إرسال الإشعارات</h1>
<p style="color:#64748b; margin-bottom:16px;">أرسل إشعارات لجميع الأجهزة المتصلة</p>

<div class="info">
  الأجهزة المتصلة: <strong id="c">0</strong>
</div>

<div class="card">
  <label>العنوان</label>
  <input id="t" value="طلب جديد!" />

  <label>المحتوى</label>
  <textarea id="b" rows="2">لديك طلب جديد رقم #1234</textarea>

  <label>الأمر (action)</label>
  <select id="a">
    <option value="show_message">show_message</option>
    <option value="open_order" selected>open_order</option>
    <option value="open_url">open_url</option>
    <option value="call_phone">call_phone</option>
    <option value="share">share</option>
  </select>

  <label>بيانات إضافية (JSON)</label>
  <input id="d" value='{"order_id":"1234"}' style="direction:ltr;text-align:left;" />

  <button onclick="send()">📤 إرسال</button>
  <div id="r"></div>
</div>

<script>
async function send() {
  try {
    const res = await fetch('/send', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        title: document.getElementById('t').value,
        body: document.getElementById('b').value,
        action: document.getElementById('a').value,
        data: JSON.parse(document.getElementById('d').value || '{}')
      })
    });
    const j = await res.json();
    document.getElementById('r').innerHTML = j.success
      ? '<div class="result ok">✅ تم الإرسال لـ '+j.sent_to+' جهاز</div>'
      : '<div class="result err">❌ '+j.error+'</div>';
  } catch(e) {
    document.getElementById('r').innerHTML = '<div class="result err">❌ '+e.message+'</div>';
  }
}
setInterval(async()=>{
  try {
    const r = await fetch('/status');
    const d = await r.json();
    document.getElementById('c').textContent = d.connected_clients;
  } catch(e){}
}, 3000);
</script>
</body>
</html>"""
    return web.Response(text=html, content_type='text/html')

# ======================================
# تشغيل السيرفر
# ======================================
app = web.Application()
app.router.add_get('/', home)
app.router.add_get('/ws', websocket_handler)
app.router.add_get('/status', status)
app.router.add_get('/healthz', health_check)
app.router.add_post('/send', send_notification)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8765))
    print(f"🚀 السيرفر يعمل على المنفذ {port}")
    print(f"📖 صفحة الإرسال: http://localhost:{port}")
    print(f"🔌 WebSocket: ws://localhost:{port}/ws")
    web.run_app(app, host='0.0.0.0', port=port)
