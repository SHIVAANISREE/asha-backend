from dotenv import load_dotenv
import os
import asyncio
import google.generativeai as genai
from .config import GEMINI_EMBEDDING_MODEL, GEMINI_API_KEY

load_dotenv()  



# Configure the Gemini API key
genai.configure(api_key=GEMINI_API_KEY)

# Model name for embeddings
MODEL_NAME = GEMINI_EMBEDDING_MODEL

async def get_embedding(text: str):
    def _sync_embed():
        embedding_result = genai.embed_content(
            model=MODEL_NAME,
            content=text,
            task_type="retrieval_document"  
        )
        
        # Get the embedding values from the result
        embeddings = embedding_result["embedding"]
        
        truncated_embedding = embeddings[:384]
        return truncated_embedding
    
    return await asyncio.to_thread(_sync_embed)

