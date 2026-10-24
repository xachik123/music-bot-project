import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Music Bot</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
    </head>
    <body style="background-color: #1a1a1a; color: white; text-align: center; padding-top: 50px; font-family: sans-serif;">
        <h1>🎉 МУЗЫКАЛЬНЫЙ ПЛЕЕР ЗАГРУЖЕН!</h1>
        <p>Сервер работает идеально.</p>
    </body>
    </html>
    """
