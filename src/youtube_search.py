import httpx
import re
from src.config import UTUBE_API



# Helper function to detect if query is asking for a technology roadmap
def is_tech_roadmap_query(query: str) -> bool:
    query = query.lower()
    roadmap_keywords = [
        "roadmap", "learning path", "how to learn", "how to become", 
        "path to become", "guide to", "tutorial", "course", "learn", 
        "master", "study plan", "curriculum", "skills needed", "start learning"
    ]
    
    tech_keywords = [
        "developer", "engineer", "programming", "coding", "software", 
        "web", "mobile", "frontend", "backend", "fullstack", "data science",
        "machine learning", "ai", "devops", "cloud", "cybersecurity",
        "python", "javascript", "java", "react", "node", "angular",
        "vue", "django", "flask", "spring", "kubernetes", "docker",
        "aws", "azure", "gcp", "database", "sql", "nosql", "blockchain",
        "iot", "artificial intelligence", "deep learning"
    ]
    
    has_roadmap_keyword = any(keyword in query for keyword in roadmap_keywords)
    has_tech_keyword = any(keyword in query for keyword in tech_keywords)
    
    return has_roadmap_keyword and has_tech_keyword


# Function to fetch YouTube videos for tech roadmaps
async def fetch_youtube_roadmap_videos(query: str) -> str:
    # Clean and enhance the query for better YouTube results
    search_query = query.lower()
    # Remove question words and make more specific for roadmap videos
    search_query = re.sub(r'^(how|what|where|when|why|who|can you)\s+', '', search_query)
    search_query = search_query + " roadmap tutorial"
    
    try:
        async with httpx.AsyncClient() as client:
            # Using YouTube Data API v3
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "maxResults": 3,
                    "q": search_query,
                    "type": "video",
                    "key": UTUBE_API,
                    "relevanceLanguage": "en",
                    "videoEmbeddable": "true"
                }
            )
            
            data = response.json()
            
            if "items" not in data or not data["items"]:
                return ""
            
            result = ""
            for item in data["items"]:
                video_id = item["id"]["videoId"]
                title = item["snippet"]["title"]
                channel = item["snippet"]["channelTitle"]
                result += f"• [{title}](https://www.youtube.com/watch?v={video_id}) by {channel}\n"
            
            return result
    except Exception as e:
        print(f"YouTube API error: {e}")
        return ""

