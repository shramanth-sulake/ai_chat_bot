from fastapi import FastAPI
from app.routes.chat import router as chat_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Chat Engine - Dev")

origins = [
    "http://localhost:3000",              # dev Next.js
    "http://127.0.0.1:3000",              # sometimes used
    "https://your-vercel-app.vercel.app", # add your production domain later
    "https://your-netlify-app.netlify.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # use ["*"] for quick dev but not recommended for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

@app.get("/")
def read_root():
    return {"message": "Hello! Your AI Chat Engine backend is running 🚀"}

@app.get("/health")
def health():
    return {"status": "ok", "uptime": "local-dev"}
