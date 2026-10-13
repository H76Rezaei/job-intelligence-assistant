from fastapi import FastAPI
from app.api import jobs
from app.api import candidate_profile
from app.api import applications
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(title="AI Job Intelligence & Application Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(candidate_profile.router)
app.include_router(applications.router)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}