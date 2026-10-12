from fastapi import FastAPI
from app.api import jobs

app = FastAPI(title="AI Job Intelligence & Application Assistant")

app.include_router(jobs.router)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}