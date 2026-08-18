"""
Genuine RX FastAPI Application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Genuine RX API",
    description="Backend API for Genuine RX per 04_API_CONTRACT.md",
    version="1.0.0",
)

# Standard permissive CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
