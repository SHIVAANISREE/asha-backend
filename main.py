import asyncio
from fastapi import FastAPI, requests, HTTPException, status, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from passlib.context import CryptContext
from pinecone import Pinecone
from dotenv import load_dotenv
from docx import Document
import os
from typing import Optional, List
from datetime import datetime
from src.embed_text import get_embedding
from src.job_search import is_job_search_only, fetch_remote_jobs
from src.event_search import is_event_related_query, fetch_ticketmaster_events
from src.youtube_search import is_tech_roadmap_query, fetch_youtube_roadmap_videos
from src.inputRequest import ChatRequest
from src.config import PINECONE_INDEX_NAME, PINECONE_API_KEY, PINECONE_NAMESPACE, MONGODB_URI, GEMINI_CHAT_MODEL
import uuid
import google.generativeai as genai

load_dotenv()

app = FastAPI()
# Pinecone connection
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)
# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI", "MONGODB_CONNECTOR")
db_client = None

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_client = AsyncIOMotorClient(MONGODB_URI)
chat_collection = db_client.chat_details.interactions

# Connect to MongoDB
@app.on_event("startup")
async def startup_db_client():
    global db_client
    try:
        db_client = AsyncIOMotorClient(MONGODB_URI)
        # Verify connection
        await db_client.admin.command('ping')
        print("Connected to MongoDB!")
        
        # Create indexes for unique fields
        user_collection = db_client.chat_details.interactions
        
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

@app.on_event("shutdown")
async def shutdown_db_client():
    global db_client
    if db_client:
        db_client.close()
        print("MongoDB connection closed")

# Get database dependency
async def get_db():
    if db_client is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return db_client.user_db


async def generate_gemini_response(prompt: str):
    def _sync_generate():
        # Initialize the Gemini model
        generation_model = genai.GenerativeModel(GEMINI_CHAT_MODEL)
        
        # Generate response
        response = generation_model.generate_content(prompt)
        
        # Extract and return the text
        return response.text
    
    return await asyncio.to_thread(_sync_generate)

@app.post("/chat")
async def chat_with_asha(req: ChatRequest):
    query = req.message
    print("entered", query)
    message_id = req.message_id

    print("message, message_id:", query, message_id)

    # 1. If job-only, skip Gemini and return job results
    if is_job_search_only(query):
        jobs = fetch_remote_jobs(query)
        response_text = f"📌 **Job Opportunities Based on Your Query**:\n{jobs}"
        
        # Store in MongoDB
        await store_chat_message(
            message_id=message_id,
            query=query,
            response=response_text,
            tag=None
        )
        
        return {
            "response": response_text,
            "message_id": message_id
        }
    
    if query.strip().lower() in ["hi", "hello", "hey", "hii", "heyy", "hola", "yo"]:
        response_text = "👋 Hi there! How can I assist you with your career or technical goals today?"
        print("response text:", response_text)

        await store_chat_message(
        message_id=message_id,
        query=query,
        response=response_text,
        tag=None
        )

        return {
            "response": response_text,
            "message_id": message_id
        }
    
    
    # 2. Check if it's a roadmap/learning path related query
    is_roadmap_query = is_tech_roadmap_query(query)
    youtube_content = ""
    if is_roadmap_query:
        youtube_links = await fetch_youtube_roadmap_videos(query)
        if youtube_links:
            youtube_content = "\n\n🎓 **Learning Resources**:\n" + youtube_links
    
    # Check if it's an event-related query
    is_event_query = is_event_related_query(query)
    events_content = ""

    if is_event_query:
        events = fetch_ticketmaster_events(query)
        
        if events and not events.startswith("Error") and not events.startswith("API request failed"):
            events_content = "\n\n🗓️ **Upcoming Events**:\n" + events

    # 3. Embed and search Pinecone
    embedding = await get_embedding(query)
    search_result = index.query(
            vector=embedding,
            top_k=3,
            include_metadata=True,
            namespace=PINECONE_NAMESPACE
        )

    context = ""
    if search_result and search_result.matches:
        for match in search_result.matches:
            print("match score:", match.score)
            if match.score >= 0.4:
                context += match.metadata.get("text", "") + "\n"
    print("context:", context)
    # 4. Prompt construction
    if context:
        prompt = f"""
You are Asha, a supportive and knowledgeable AI assistant focused exclusively on helping women in their career journeys.With the help of the Question{query}, answer accordingly. 
You specialize in:
- Career guidance
- Job opportunities
- Technical skill development (e.g., programming, cloud, AI/ML, data science, etc.)
- Mentorship
- Career-related events

Use the provided context to deliver clear, actionable, and inspiring responses.

🚨 Important Rules:
1. If the user's message is a simple greeting (e.g., "hi", "hello", "hey"), respond with a short, friendly greeting like "Hi there! How can I assist you with your career or technical goals today?"
2. If the user's question is related to **career, jobs, technical skills, mentorship, or workplace equality**, answer it helpfully and empathetically.
3. If the user's question involves **women empowerment or gender equality in the workplace**, respond with encouragement and facts that promote confidence and fairness.
4. If the user's question is **unrelated to careers or technology** (e.g., about food, politics, movies, general lifestyle, sexual content etc.), politely inform the user that Asha only assists with professional and technical topics.

Refer {query} and {context}, and Response Accordingly.
"""
    else:
        prompt = f"""
You are Asha, a supportive and knowledgeable AI assistant focused exclusively on helping women in their career journeys.
You specialize in:
- Career guidance
- Job opportunities
- Technical skill development (e.g., programming, cloud, AI/ML, data science, etc.)
- Mentorship
- Career-related events

There is no additional context provided. Use your general knowledge to provide a helpful and relevant response.

🚨 Important Rules:
1. If the user's message is a simple greeting (e.g., "hi", "hello", "hey"), respond with a short, friendly greeting like "Hi there! How can I assist you with your career or technical goals today?"
2. If the user's question is related to **career, jobs, technical skills, mentorship, or workplace equality**, answer it helpfully and empathetically.
3. If the user's question involves **women empowerment or gender equality in the workplace**, respond with encouragement and facts that promote confidence and fairness.
4. If the user's question is **unrelated to careers or technology** (e.g., about food, politics, movies, general lifestyle, sexual content etc.), politely inform the user that Asha only assists with professional and technical topics.

Refer {query} and Response Accordingly.
"""

    # 5. Call Gemini model instead of Hugging Face
    answer = await generate_gemini_response(prompt)

    # 6. Construct final response with jobs and videos if applicable
    final_response = answer
    
    # Add YouTube content if available for roadmap queries
    if youtube_content:
        final_response += youtube_content

    if events_content:
        final_response += events_content
    
    # Only add job listings if it's career/job-related
    if not is_roadmap_query or "job" in query.lower() or "career" in query.lower():
        job_results = fetch_remote_jobs(query)
        final_response += f"\n\n📌 **Job Opportunities Based on Your Query**:\n{job_results}"
    
    await store_chat_message(
        message_id=message_id,
        query=query,
        response=final_response,
        tag=None
    )
    
    return {
        "response": final_response,
        "message_id": message_id,
    }

# function to store the messages in db
async def store_chat_message( message_id, query, response, tag=None):
    """Store both user query and AI response in MongoDB"""
    print("chat collection:", chat_collection)
    print(message_id, query, response, tag)
    # Store user message
    user_message = {
        "message_id": f"{message_id}",
        "question": query,
        "answer": response,
        "tag": tag,
        "timestamp": datetime.utcnow()
    }
    
    
    # Insert both messages
    await chat_collection.insert_one(user_message)

# adding tag to a message
@app.post("/tag-message")
async def tag_message(message_id: str, tag: str):
    result = await chat_collection.update_one(
        {"message_id": message_id},
        {"$set": {"tag": tag}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"success": True}

# removing tag of a message
@app.post("/remove-tag")
async def remove_tag(message_id: str):
    result = await chat_collection.update_one(
        {"message_id": message_id},
        {"$unset": {"tag": ""}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"success": True}

# fetching all tags
@app.get("/tags", response_model=List[str])
async def get_all_tags():
    tags_cursor = chat_collection.find(
        {"tag": {"$exists": True, "$ne": None}},
        {"_id": 0, "tag": 1}
    )
    tags = set()
    async for doc in tags_cursor:
        if "tag" in doc:
            tags.add(doc["tag"])
    return list(tags)

# fetching messages by tags
@app.get("/messages-by-tag")
async def get_messages_by_tag(tag: str = Query(...)):
    cursor = chat_collection.find({"tag": tag})
    messages = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])  
        messages.append(doc)
    return messages


# uploading the documents in pinecone
@app.post("/pinecone-upsert-doc")
async def upsert_pinecone_from_doc():
    doc = Document("src/doc/full_stack_roadmap.docx")
    print("entering")
    if doc:
        print("True")
    else:
        print("False")

    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    chunk_size = 4
    vectors = []

    for i in range(0, len(paragraphs), chunk_size):
        chunk_paragraphs = paragraphs[i:i + chunk_size]
        chunk_text = "\n".join(chunk_paragraphs)

        embedding = await get_embedding(chunk_text)
        vector_id = str(uuid.uuid4())

        vectors.append({
            "id": vector_id,
            "values": embedding,
            "metadata": {
                "text": chunk_text,
                "source": "full_stack_roadmap.docx",
                "position": i // chunk_size
            }
        })

    index.upsert(vectors=vectors, namespace="asha-ai")
    return {"status": "success", "chunks": len(vectors)}