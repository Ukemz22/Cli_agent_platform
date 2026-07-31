from fastapi import FastAPI, Depends

from api.deps import get_current_developer
from api.routes_businesses import router as businesses_router
from api.routes_whatsapp import router as whatsapp_router
from api.routes_telegram import router as telegram_router
from api.routes_paystack import router as paystack_router
from core.models import Developer

app = FastAPI(title="CLI Agent Platform API")
app.include_router(businesses_router)
app.include_router(whatsapp_router)
app.include_router(telegram_router)
app.include_router(paystack_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/whoami")
def whoami(developer: Developer = Depends(get_current_developer)):
    return {"developer_id": str(developer.id), "status": developer.status}
