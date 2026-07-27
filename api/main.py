from fastapi import FastAPI

app = FastAPI(title="CLI Agent Platform API")


@app.get("/health")
def health():
    return {"status": "ok"}
