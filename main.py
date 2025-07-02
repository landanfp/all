import threading
from fastapi import FastAPI
import uvicorn

from loader import app
from plugins import start, hardsub, upload

# FastAPI app برای پاسخ دادن به Health Check
api = FastAPI()

@api.get("/")
async def root():
    return {"message": "Bot is running."}

# اجرای سرور در یک ترد جدا
def run_server():
    uvicorn.run(api, host="0.0.0.0", port=8000)

# شروع سرور
threading.Thread(target=run_server).start()

# اجرای اپلیکیشن پایروگرام 
app.run()
