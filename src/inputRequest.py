from typing import Optional
from pydantic import  BaseModel, EmailStr, Field

# Input from user
class ChatRequest(BaseModel):
    message: str
    message_id: str

