from fastapi import FastAPI
from app.api import companies

app = FastAPI(title="AI Job Intelligence & Application Assistant")


app.include_router(companies.router)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}