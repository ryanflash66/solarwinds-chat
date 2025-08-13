from pydantic import BaseModel


class HelloResponse(BaseModel):
    message: str

class ChatRequest(BaseModel):
    name: str
    query: str

class ChatResponse(BaseModel):
    answer: str