from fastapi import FastAPI, HTTPException
import os, httpx

app = FastAPI(title="POC backend")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/run")
async def run():
    return {"success": True, "details": []}

@app.post("/notify")
async def notify():
    chat_id = os.getenv("CHAT_ID")
    bot_token = os.getenv("BOT_TOKEN")
    if not chat_id or not bot_token:
        raise HTTPException(status_code=400, detail="CHAT_ID or BOT_TOKEN missing")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json={"chat_id": chat_id, "text": "Hello"})
        r.raise_for_status()
        return r.json()
