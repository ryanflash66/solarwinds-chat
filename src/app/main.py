from fastapi import FastAPI
from app.api.routes import router as api_router
from app.core.config import settings

app = FastAPI(title="Solarbot API")

# include api routes
app.include_router(api_router)

# root route for health check
@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}!"}