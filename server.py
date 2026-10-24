import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, "index.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return "ФАЙЛ index.html НЕ НАЙДЕН!"
