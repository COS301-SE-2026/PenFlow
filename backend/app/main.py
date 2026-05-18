from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health, scans
from app.realtime import stream

app = FastAPI(
    title="PenFlow API",
    description="Core backend API for the PenFlow platform.",
    version="1.0.0"
              
)

app.include_router(health.router)
app.include_router(scans.router, prefix="/api/v1")
app.include_router(stream.router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
