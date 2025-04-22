import requests

def is_event_related_query(query: str) -> bool:
    query = query.lower()
    event_keywords = [
        "event", "conference", "workshop", "meetup", "hackathon", 
        "webinar", "seminar", "talk", "presentation", "convention",
        "summit", "symposium", "forum", "gathering", "tech event",
        "networking event", "career fair", "upcoming events"
    ]
    
    return any(keyword in query for keyword in event_keywords)


# Ticketmaster API implementation
def fetch_ticketmaster_events(query="women tech", location="", limit=5):
    # Clean and enhance the query for better event results
    search_query = query.lower()
    # Add career/tech terms if they're not already present
    if not any(term in search_query for term in ["tech", "career", "programming", "developer"]):
        search_query += " tech career"
    
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "keyword": search_query,
        "segmentName": "Conference",  # Focus on professional events
        "size": limit,
        "sort": "date,asc",
        "apikey": "J8IisplwMKADaDjRhSPiJlcRqQfSwR6d"
    }
    
    # Add location if provided
    if location:
        params["city"] = location
    
    try:
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            # Check if events exist in the response
            if "_embedded" not in data or "events" not in data.get("_embedded", {}):
                return "No events found matching your criteria."
                
            events = data["_embedded"]["events"]
            
            if not events:
                return "No events found matching your criteria."
                
            event_results = []
            for event in events:
                name = event.get("name", "Unnamed event")
                
                # Get date and format it nicely
                date_info = event.get("dates", {}).get("start", {})
                date = date_info.get("localDate", "TBA")
                time = date_info.get("localTime", "")
                formatted_date = f"{date} {time}".strip()
                
                # Get venue information
                venue_info = event.get("_embedded", {}).get("venues", [{}])[0]
                venue_name = venue_info.get("name", "Location TBA")
                
                # Get city/state if available
                city = venue_info.get("city", {}).get("name", "")
                state = venue_info.get("state", {}).get("stateCode", "")
                location = f"{city}, {state}" if city and state else city or state or ""
                
                # Get event URL
                url = event.get("url", "#")
                
                # Format the event entry
                event_entry = f"📅 **{name}**"
                if formatted_date:
                    event_entry += f"\n⏰ {formatted_date}"
                if venue_name:
                    location_str = f"{venue_name}" + (f", {location}" if location else "")
                    event_entry += f"\n📍 {location_str}"
                event_entry += f"\n🔗 [Get Tickets]({url})"
                
                event_results.append(event_entry)
            
            return "\n\n".join(event_results)
        else:
            error_info = response.text[:100] + "..." if len(response.text) > 100 else response.text
            return f"API request failed with status code: {response.status_code}. Details: {error_info}"
            
    except Exception as e:
        return f"Error fetching events: {str(e)}"
    
