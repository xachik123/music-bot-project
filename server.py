import os
import json
import hashlib
import hmac
from urllib.parse import parse_qsl
import yt_dlp
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://example.com")
DATA_FILE = "playlists.json"
USERS_FILE = "users.json"
FREE_MAX_PLAYLISTS = 999
ADMIN_ID = "твой_telegram_id" 

app = FastAPI()

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Музыка</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
    body { font-family: sans-serif; padding: 16px; background: var(--tg-theme-bg-color, #fff); color: var(--tg-theme-text-color, #000); margin: 0; }
    #app { max-width: 600px; margin: 0 auto; padding-bottom: 150px; }
    .screen { display: none; }
    .screen.active { display: block; }
    input { width: 100%; padding: 12px; margin-bottom: 10px; box-sizing: border-box; border-radius: 8px; border: 1px solid #ccc; }
    button { padding: 12px 16px; cursor: pointer; border-radius: 8px; border: none; background: var(--tg-theme-button-color, #2481cc); color: var(--tg-theme-button-text-color, #fff); font-size: 15px; margin: 4px 4px 4px 0; }
    button.secondary { background: #888; }
    button:disabled { background: #ccc; cursor: not-allowed; }
    .user-badge { font-size: 12px; padding: 4px 8px; border-radius: 4px; font-weight: bold; margin-bottom: 10px; display: inline-block; }
    .badge-vip { background: gold; color: #000; }
    .badge-free { background: #e0e0e0; color: #333; }
    #playlists { list-style: none; padding: 0; }
    #playlists li { display: flex; justify-content: space-between; align-items: center; padding: 14px; background: var(--tg-theme-secondary-bg-color, #f0f0f0); margin-bottom: 8px; border-radius: 8px; }
    #playlists li span { cursor: pointer; flex-grow: 1; font-weight: bold; }
    .btn-delete { background: #e74c3c; padding: 8px 12px; margin: 0; font-size: 14px; }
    #track-list { list-style: none; padding: 0; }
    #track-list li { padding: 12px; border-bottom: 1px solid #eee; cursor: pointer; display: flex; align-items: center; }
    #track-list li.playing { background: #d4edda; color: #155724; font-weight: bold; }
    .player-controls { display: flex; gap: 10px; margin-bottom: 10px; }
    .toggle-btn { background: #555; font-size: 14px; padding: 8px 12px; }
    .toggle-btn.active { background: #f39c12; }
    #player { position: fixed; bottom: 0; left: 0; right: 0; background: var(--tg-theme-secondary-bg-color, #f0f0f0); padding: 10px; box-sizing: border-box; border-top: 1px solid #ddd; }
    #loading { text-align: center; padding: 20px; color: #888; }
    .control-btns { display: flex; justify-content: center; gap: 15px; margin-top: 10px; }
    .control-btns button { padding: 10px 20px; font-size: 18px; background: #333; }
</style>
</head>
<body>
<div id="app">
    <div id="profile-screen" class="screen active">
        <div id="user-status-badge" class="user-badge">Загрузка...</div>
        <h2>Мои плейлисты</h2>
        <button id="add-btn" onclick="showAddScreen()">➕ Добавить плейлист</button>
        <div id="loading" style="display:none">Загрузка...</div>
        <ul id="playlists"></ul>
    </div>
    <div id="add-screen" class="screen">
        <h2>Добавить плейлист</h2>
        <input type="text" id="playlist-url" placeholder="Вставь ссылку на плейлист SoundCloud">
        <button onclick="addPlaylist()">Добавить</button>
        <button class="secondary" onclick="showProfileScreen()">Назад</button>
    </div>
    <div id="player-screen" class="screen">
        <h2 id="playlist-title"></h2>
        <div class="player-controls">
            <button id="shuffle-btn" class="toggle-btn" onclick="toggleShuffle()">➡️ По порядку</button>
            <button class="secondary" onclick="showProfileScreen()">← Назад</button>
        </div>
        <ul id="track-list"></ul>
    </div>
</div>
<div id="player" style="display: none;">
    <audio id="audio-player" controls style="width: 100%;" onended="playNextTrack()"></audio>
    <div class="control-btns">
        <button onclick="playPrevTrack()">⏮ Назад</button>
        <button onclick="playNextTrack()">⏭ Вперёд</button>
    </div>
</div>
<script>
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
let currentPlaylist = null;
let currentTrackIndex = -1;
let isShuffle = false;
function showScreen(id) { document.querySelectorAll('.screen').forEach(s => s.classList.remove('active')); document.getElementById(id).classList.add('active'); }
function showProfileScreen() { showScreen('profile-screen'); loadPlaylists(); const audio = document.getElementById('audio-player'); if(!audio.paused) audio.pause(); }
function showAddScreen() { showScreen('add-screen'); }
async function apiRequest(path, method = 'GET', body = null) {
    const headers = { 'X-Telegram-Init-Data': tg.initData || '' };
    if (body) headers['Content-Type'] = 'application/json';
    const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : null });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}
async function loadPlaylists() {
    document.getElementById('loading').style.display = 'block';
    try {
        const data = await apiRequest('/api/playlists');
        const badge = document.getElementById('user-status-badge');
        if (data.status === 'vip') { badge.textContent = '👑 VIP Аккаунт'; badge.className = 'user-badge badge-vip'; } 
        else { badge.textContent = 'Бесплатный аккаунт'; badge.className = 'user-badge badge-free'; }
        const addBtn = document.getElementById('add-btn');
        if (!data.can_add) { addBtn.disabled = true; addBtn.textContent = 'Лимит плейлистов'; } 
        else { addBtn.disabled = false; addBtn.textContent = '➕ Добавить плейлист'; }
        const list = document.getElementById('playlists');
        list.innerHTML = '';
        if (!data.playlists.length) list.innerHTML = '<li style="cursor:default;color:#888;background:none;padding:0;">Пока пусто. Добавь первый плейлист!</li>';
        data.playlists.forEach((pl, idx) => {
            const li = document.createElement('li');
            const span = document.createElement('span');
            span.textContent = pl.title + ' (' + pl.tracks.length + ' треков)';
            span.onclick = () => openPlaylist(pl);
            const btn = document.createElement('button');
            btn.className = 'btn-delete';
            btn.textContent = '🗑';
            btn.onclick = (e) => { e.stopPropagation(); deletePlaylist(idx); };
            li.appendChild(span); li.appendChild(btn); list.appendChild(li);
        });
    } catch (e) { alert('Ошибка: ' + e.message); } 
    finally { document.getElementById('loading').style.display = 'none'; }
}
async function deletePlaylist(idx) { if (!confirm('Удалить этот плейлист?')) return; try { await apiRequest('/api/playlist/' + idx, 'DELETE'); loadPlaylists(); } catch (e) { alert('Ошибка: ' + e.message); } }
async function addPlaylist() { const url = document.getElementById('playlist-url').value.trim(); if (!url) return; document.getElementById('loading').style.display = 'block'; try { await apiRequest('/api/playlist', 'POST', { url }); document.getElementById('playlist-url').value = ''; showProfileScreen(); } catch (e) { alert('Ошибка: ' + e.message); } finally { document.getElementById('loading').style.display = 'none'; } }
function openPlaylist(pl) { currentPlaylist = pl; currentTrackIndex = -1; document.getElementById('playlist-title').textContent = pl.title; renderTrackList(); showScreen('player-screen'); }
function renderTrackList() { const list = document.getElementById('track-list'); list.innerHTML = ''; currentPlaylist.tracks.forEach((t, index) => { const li = document.createElement('li'); li.id = 'track-item-' + index; li.textContent = t.artist + ' — ' + t.title; if (index === currentTrackIndex) { li.classList.add('playing'); li.textContent = '▶ ' + li.textContent; } li.onclick = () => playTrack(index); list.appendChild(li); }); }
async function playTrack(index) { if (index < 0 || index >= currentPlaylist.tracks.length) return; const track = currentPlaylist.tracks[index]; const audio = document.getElementById('audio-player'); const playerDiv = document.getElementById('player'); if (currentTrackIndex !== -1) { const oldLi = document.getElementById('track-item-' + currentTrackIndex); if (oldLi) { oldLi.classList.remove('playing'); oldLi.textContent = oldLi.textContent.replace('▶ ', '').replace('⏳ ', ''); } } currentTrackIndex = index; const newLi = document.getElementById('track-item-' + index); if (newLi) { newLi.classList.add('playing'); newLi.textContent = '⏳ ' + track.artist + ' — ' + track.title; } try { const data = await apiRequest('/api/stream', 'POST', { url: track.url }); playerDiv.style.display = 'block'; audio.src = data.stream_url; await audio.play(); if (newLi) newLi.textContent = '▶ ' + track.artist + ' — ' + track.title; } catch (e) { alert('Ошибка: ' + e.message); if (newLi) { newLi.textContent = track.artist + ' — ' + track.title; newLi.classList.remove('playing'); } } }
function playNextTrack() { if (!currentPlaylist) return; let nextIndex = isShuffle ? Math.floor(Math.random() * currentPlaylist.tracks.length) : (currentTrackIndex + 1) % currentPlaylist.tracks.length; playTrack(nextIndex); }
function playPrevTrack() { if (!currentPlaylist) return; let prevIndex = currentTrackIndex - 1; if (prevIndex < 0) prevIndex = currentPlaylist.tracks.length - 1; playTrack(prevIndex); }
function toggleShuffle() { isShuffle = !isShuffle; const btn = document.getElementById('shuffle-btn'); if (isShuffle) { btn.textContent = '🔀 Вразброс'; btn.classList.add('active'); } else { btn.textContent = '➡️ По порядку'; btn.classList.remove('active'); } }
loadPlaylists();
</script>
</body>
</html>
"""

# --- БОТ ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    button = KeyboardButton(text="🎵 Открыть плеер", web_app=WebAppInfo(url=WEB_APP_URL))
    keyboard = ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True)
    await message.answer("Привет! Нажми на кнопку ниже:", reply_markup=keyboard)

async def start_bot():
    print("Бот запущен...")
    await dp.start_polling(bot)

# --- API ---
def load_json(file):
    if not os.path.exists(file): return {}
    with open(file, "r", encoding="utf-8") as f: return json.load(f)
def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
def validate_init_data(init_data: str):
    if not init_data or not BOT_TOKEN: return None
    try:
        parsed = dict(parse_qsl(init_data))
        hash_str = parsed.pop("hash", "")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if computed != hash_str: return None
        return json.loads(parsed.get("user", "{}"))
    except Exception: return None
def get_user_info(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    user = validate_init_data(init_data)
    if not user: return {"id": "local_test_user", "status": "vip"}
    user_id = str(user.get("id"))
    users_db = load_json(USERS_FILE)
    if user_id not in users_db:
        users_db[user_id] = {"username": user.get("username", "unknown"), "status": "vip" if user_id == ADMIN_ID else "free"}
        save_json(USERS_FILE, users_db)
    return {"id": user_id, "status": users_db[user_id]["status"], "username": users_db[user_id]["username"]}

class PlaylistAddRequest(BaseModel): url: str
class StreamRequest(BaseModel): url: str

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_bot())

@app.get("/", response_class=HTMLResponse)
async def serve_index(): return HTML_CONTENT

@app.get("/api/playlists")
async def get_playlists(request: Request):
    user = get_user_info(request)
    data = load_json(DATA_FILE)
    playlists = data.get(user["id"], [])
    return {"playlists": playlists, "status": user["status"], "can_add": user["status"] == "vip" or len(playlists) < FREE_MAX_PLAYLISTS}

@app.post("/api/playlist")
async def add_playlist(req: PlaylistAddRequest, request: Request):
    user = get_user_info(request)
    data = load_json(DATA_FILE)
    if user["status"] != "vip" and len(data.get(user["id"], [])) >= FREE_MAX_PLAYLISTS: raise HTTPException(status_code=403, detail="Лимит исчерпан.")
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl: info = ydl.extract_info(req.url, download=False)
        tracks = []
        for i, entry in enumerate(info.get("entries", [])):
            if not entry: continue
            url = entry.get("url") or entry.get("webpage_url", "")
            t = entry.get("title") or (url.split('/')[-1].replace('-', ' ').title() if "soundcloud" in url else "Трек")
            a = entry.get("uploader") or (url.split('/')[3].title() if "soundcloud" in url else "Неизвестен")
            tracks.append({"id": i, "title": t, "artist": a, "url": url, "thumbnail": entry.get("thumbnail", ""), "duration": entry.get("duration", 0)})
        playlist = {"title": info.get("title", "Плейлист"), "tracks": tracks}
        data.setdefault(user["id"], []).append(playlist)
        save_json(DATA_FILE, data)
        return {"success": True, "playlist": playlist}
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/playlist/{idx}")
async def delete_playlist(idx: int, request: Request):
    user = get_user_info(request); data = load_json(DATA_FILE)
    if user["id"] in data and 0 <= idx < len(data[user["id"]]):
        data[user["id"]].pop(idx); save_json(DATA_FILE, data); return {"success": True}
    raise HTTPException(status_code=404)

@app.post("/api/stream")
async def get_stream(req: StreamRequest):
    try:
        with yt_dlp.YoutubeDL({"format": "bestaudio/best", "quiet": True}) as ydl: info = ydl.extract_info(req.url, download=False)
        url = info.get("url") or next((f["url"] for f in info.get("formats", []) if f.get("url")), None)
        if not url: raise HTTPException(status_code=404)
        return {"stream_url": url}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
