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

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = "playlists.json"
USERS_FILE = "users.json"

# --- НАСТРОЙКИ ДОСТУПА ---
FREE_MAX_PLAYLISTS = 999  # Пока 999 (безлимит). Потом поставим 2 или 3.
ADMIN_ID = "твой_telegram_id" # СЮДА ВПИШИ СВОЙ ID (узнать можно у бота @userinfobot)

app = FastAPI()

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
    
    # Если это локальный тест в браузере
    if not user:
        return {"id": "local_test_user", "status": "vip"}

    user_id = str(user.get("id"))
    username = user.get("username", "unknown")
    
    # Проверяем базу пользователей
    users_db = load_json(USERS_FILE)
    
    if user_id not in users_db:
        # Если пользователь зашел впервые, регистрируем его
        status = "vip" if user_id == ADMIN_ID else "free"
        users_db[user_id] = {"username": username, "status": status}
        save_json(USERS_FILE, users_db)
        
    return {"id": user_id, "status": users_db[user_id]["status"], "username": username}

class PlaylistAddRequest(BaseModel):
    url: str

class StreamRequest(BaseModel):
    url: str

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/playlists")
async def get_playlists(request: Request):
    user = get_user_info(request)
    data = load_json(DATA_FILE)
    playlists = data.get(user["id"], [])
    
    # Проверяем, не превышен ли лимит (вернем флаг на фронтенд)
    can_add = user["status"] == "vip" or len(playlists) < FREE_MAX_PLAYLISTS
    
    return {"playlists": playlists, "status": user["status"], "can_add": can_add}

@app.post("/api/playlist")
async def add_playlist(req: PlaylistAddRequest, request: Request):
    user = get_user_info(request)
    data = load_json(DATA_FILE)
    user_playlists = data.get(user["id"], [])

    # Защита на бэкенде
    if user["status"] != "vip" and len(user_playlists) >= FREE_MAX_PLAYLISTS:
        raise HTTPException(status_code=403, detail="Лимит бесплатных плейлистов исчерпан. Оформите VIP!")

    try:
        ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)

        if "entries" not in info:
            raise HTTPException(status_code=400, detail="Это не плейлист")

        tracks = []
        for i, entry in enumerate(info["entries"]):
            if not entry: continue
            track_url = entry.get("url") or entry.get("webpage_url", "")
            title = entry.get("title")
            artist = entry.get("uploader") or entry.get("artist")

            if not title or title.isdigit() or title.lower() == "unknown":
                if "soundcloud.com" in track_url:
                    parts = track_url.split('/')
                    if len(parts) >= 5 and parts[3] != "tracks":
                        artist = parts[3].replace('-', ' ').title()
                        title = parts[4].replace('-', ' ').title()
                    elif len(parts) >= 5 and parts[3] == "tracks":
                        artist = "SoundCloud"
                        title = f"Трек (ID: {parts[4]})"

            tracks.append({
                "id": i,
                "title": title or "Без названия",
                "artist": artist or "Неизвестен",
                "url": track_url,
                "thumbnail": entry.get("thumbnail", ""),
                "duration": entry.get("duration", 0),
            })

        playlist_data = {"title": info.get("title", "Плейлист"), "tracks": tracks}
        data.setdefault(user["id"], []).append(playlist_data)
        save_json(DATA_FILE, data)
        
        return {"success": True, "playlist": playlist_data}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=400, detail=f"Ошибка: {str(e)}")

@app.delete("/api/playlist/{playlist_idx}")
async def delete_playlist(playlist_idx: int, request: Request):
    user = get_user_info(request)
    data = load_json(DATA_FILE)
    if user["id"] in data and 0 <= playlist_idx < len(data[user["id"]]):
        data[user["id"]].pop(playlist_idx)
        save_json(DATA_FILE, data)
        return {"success": True}
    raise HTTPException(status_code=404, detail="Плейлист не найден")

@app.post("/api/stream")
async def get_stream(req: StreamRequest):
    try:
        ydl_opts = {"format": "bestaudio/best", "quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            stream_url = info.get("url")
            if not stream_url:
                for f in info.get("formats", []):
                    if f.get("url"): stream_url = f["url"]; break
            if not stream_url: raise HTTPException(status_code=404, detail="Не удалось найти поток")
            return {"stream_url": stream_url}
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))