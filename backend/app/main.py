from fastapi import FastAPI

app = FastAPI(title="AI Job Intelligence & Application Assistant")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}