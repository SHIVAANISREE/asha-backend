import requests
import json

# fetching jobs from public api
def fetch_remote_jobs(category="software-dev", limit=10):

    url = f"https://remotive.com/api/remote-jobs?category={category}"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            jobs_data = response.json()
            jobs = jobs_data.get("jobs", [])[:limit]
            
            if not jobs:
                return "No jobs found for this category."
                
            job_results = []
            for job in jobs:
                company = job.get("company_name", "Unknown company")
                title = job.get("title", "Untitled position")
                url = job.get("url", "#")
                
                job_results.append(f"🔹 {title} at {company}\n🔗 {url}")
            
            return "\n\n".join(job_results)
        else:
            return f"API request failed with status code: {response.status_code}"
            
    except Exception as e:
        return f"Error fetching jobs: {str(e)}"


# classification of user query
def is_job_search_only(query: str):
    job_keywords = ["job", "jobs", "openings", "roles", "vacancies", "positions", "hiring", "opportunities"]
    return any(kw in query.lower() for kw in job_keywords) and len(query.split()) <= 6