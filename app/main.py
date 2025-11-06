from fastapi import FastAPI
from app.routes.chat import router as chat_router
from fastapi.middleware.cors import CORSMiddleware
from app.utils import query_response_cache

app = FastAPI(title="AI Chat Engine - Dev")

# For development, allow all origins. Change this in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Temporarily allow all origins for testing
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose all headers for debugging
)

app.include_router(chat_router)

# Clear in-memory dev cache on startup so code changes show immediately
query_response_cache.clear()

@app.get("/")
def read_root():
    return {"message": "Hello! Your AI Chat Engine backend is running 🚀"}

@app.get("/health")
def health():
    return {"status": "ok", "uptime": "local-dev"}
