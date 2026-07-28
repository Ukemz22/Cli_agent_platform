from fastapi import FastAPI

app = FastAPI(title="CLI Agent Platform API")


@app.get("/health")
def health():
    return {"status": "ok"}


from fastapi import Depends
from api.deps import get_current_developer
from core.models import Developer


@app.get("/whoami")
def whoami(developer: Developer = Depends(get_current_developer)):
    return {"developer_id": str(developer.id), "status": developer.status}
