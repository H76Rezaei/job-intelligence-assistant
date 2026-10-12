from fastapi import FastAPI
from app.api import jobs
from app.api import candidate_profile
from app.api import applications

app = FastAPI(title="AI Job Intelligence & Application Assistant")

app.include_router(jobs.router)
app.include_router(candidate_profile.router)
app.include_router(applications.router)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}