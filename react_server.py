import os
import webbrowser
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import app as engine

web = FastAPI(title="ALPHA IDX • React + FastAPI")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@web.get("/", response_class=HTMLResponse)
def home():
    with open(os.path.join(BASE_DIR, "react_ui.html"), "r", encoding="utf-8") as f:
        return f.read()


@web.get("/api/scan")
def scan(force: int = 0):
    try:
        return engine.get_market_data(force=(force == 1))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@web.get("/api/issi")
def get_issi():
    return {"tickers": sorted(engine.load_issi_set())}


@web.post("/api/issi")
async def save_issi(request: Request):
    body = await request.json()
    raw_text = body.get("text", "")
    tokens = [t.strip().upper().replace("IDX:", "") for t in raw_text.replace(",", "\n").splitlines()]
    valid = sorted({t for t in tokens if 3 <= len(t) <= 5 and t.isalpha()})
    if not valid:
        return JSONResponse({"error": "Tidak ada kode saham valid."}, status_code=400)
    with open(engine.ISSI_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(valid))
    engine._cache["data"] = None
    return {"saved": len(valid)}


if __name__ == "__main__":
    webbrowser.open("http://localhost:8000")
    uvicorn.run(web, host="0.0.0.0", port=8000)