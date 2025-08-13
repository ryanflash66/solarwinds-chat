from fastapi import APIRouter
from app.core.config import settings
from app.models.base import ChatResponse, ChatRequest

router = APIRouter(prefix="/api")

@router.get("/hello")
def say_hello():
    return {"message": "Hello from SolarBot!"}


@router.get("/status")
def get_status():
    return {
        "app_name": settings.APP_NAME,
        "debug": settings.DEBUG
    }

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    user_query = payload.query

    # for now just echo back
    dummy_answer = f"You said: '{user_query}'. A real answer will go here soon."

    return ChatResponse(answer=dummy_answer)

@router.post("/echo", response_model=ChatResponse)
def echo_endpoint(payload: ChatRequest):
    user_query = payload.query
    user_name = payload.name
    echo_answer = f"Hey {user_name}, you said: '{user_query}'"

    return ChatResponse(answer=echo_answer)