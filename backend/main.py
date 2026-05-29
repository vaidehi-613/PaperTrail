from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from backend.config import get_settings
from backend.routers.chat import router as chat_router
from backend.routers.papers import router as papers_router

settings = get_settings()

app = FastAPI(title="PaperTrail")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers_router, prefix="/papers", tags=["papers"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
