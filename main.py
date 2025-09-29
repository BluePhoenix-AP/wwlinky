from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import uvicorn
import json
import os
from datetime import datetime

from api.link_funcs import save_link

links_db = "V1/db/links.json"
votes_db = "V1/db/votes.json"
app = FastAPI(title="World Wide Linky's API")

# Configure CORS to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Link(BaseModel):
    id: Optional[int] = None
    url: str
    title: str
    description: str
    likes: int = 0
    dislikes: int = 0

class LinkData(BaseModel):
    url: str
    title: Optional[str] = None
    description: Optional[str] = None

class Vote(BaseModel):
    link_id: int
    vote_type: str  # "like" or "dislike"

def read_links(db_path: str) -> List[Link]:
    """Read links from the JSON file."""
    if not os.path.exists(db_path):
        return []
    
    with open(db_path, 'r') as f:
        links_data = json.load(f)
    
    # Convert the data to Link objects
    links = []
    for item in links_data:
        links.append(Link(
            id=item.get("id"),
            url=item.get("url", ""),
            title=item.get("title", ""),
            description=item.get("description", ""),
            likes=item.get("likes", 0),
            dislikes=item.get("dislikes", 0)
        ))
    
    return links

def write_links(db_path: str, links: List[Link]):
    """Write links to the JSON file."""
    links_data = []
    for link in links:
        links_data.append({
            "id": link.id,
            "url": link.url,
            "title": link.title,
            "description": link.description,
            "likes": link.likes,
            "dislikes": link.dislikes
        })
    
    with open(db_path, 'w') as f:
        json.dump(links_data, f, indent=2)

def read_votes(db_path: str) -> List[Dict]:
    """Read votes from the JSON file."""
    if not os.path.exists(db_path):
        return []
    
    with open(db_path, 'r') as f:
        return json.load(f)

def write_votes(db_path: str, votes: List[Dict]):
    """Write votes to the JSON file."""
    with open(db_path, 'w') as f:
        json.dump(votes, f, indent=2)

def get_next_link_id(links: List[Link]) -> int:
    """Get the next available ID for a new link."""
    if not links:
        return 1
    return max(link.id for link in links) + 1

@app.get("/api/links", response_model=List[Link])
async def get_links():
    """
    Retrieve all saved links from the database, sorted by likes - dislikes.
    """
    try:
        links = read_links(links_db)
        # Sort links by score (likes - dislikes) in descending order
        sorted_links = sorted(links, key=lambda x: (x.likes - x.dislikes), reverse=True)
        return sorted_links
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve links: {str(e)}")

@app.post("/api/process-link")
async def process_link(data: LinkData):
    """
    Process a link with title and description.
    Returns the processed data with additional information.
    """
    try:
        # Here you would add your processing logic
        # For this example, we'll just return the data with some additional fields
        
        result = {
            "original_url": data.url,
            "title": data.title if data.title else "Not Provided",
            "description": data.description if data.description else "Not Provided",
            "status": "processed",
            "message": "Link processed successfully"
        }
        
        url = data.url
        title = data.title if data.title else "No Title Provided"
        description = data.description if data.description else "No Description Provided"
        
        save_link(links_db, url, title, description)
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/api/vote")
async def add_vote(vote: Vote):
    """
    Add a like or dislike vote to a link.
    """
    try:
        # Read current links and votes
        links = read_links(links_db)
        votes = read_votes(votes_db)
        
        # Find the link by ID
        link = next((l for l in links if l.id == vote.link_id), None)
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        
        # Update vote counts
        if vote.vote_type == "like":
            link.likes += 1
        elif vote.vote_type == "dislike":
            link.dislikes += 1
        else:
            raise HTTPException(status_code=400, detail="Invalid vote type")
        
        # Save the updated link
        write_links(links_db, links)
        
        # Record the vote
        new_vote = {
            "link_id": vote.link_id,
            "vote_type": vote.vote_type,
            "timestamp": datetime.now().isoformat()
        }
        votes.append(new_vote)
        write_votes(votes_db, votes)
        
        return {"status": "success", "message": f"Vote {vote.vote_type}d successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add vote: {str(e)}")

@app.delete("/api/vote/{link_id}")
async def remove_vote(link_id: int):
    """
    Remove a vote from a link.
    """
    try:
        # Read current links and votes
        links = read_links(links_db)
        votes = read_votes(votes_db)
        
        # Find the link by ID
        link = next((l for l in links if l.id == link_id), None)
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        
        # Find the most recent vote for this link
        # In a real app, you would track votes per user
        # For simplicity, we'll just remove the most recent vote
        link_votes = [v for v in votes if v["link_id"] == link_id]
        if not link_votes:
            raise HTTPException(status_code=404, detail="No votes found for this link")
        
        # Sort by timestamp to get the most recent
        link_votes.sort(key=lambda x: x["timestamp"], reverse=True)
        recent_vote = link_votes[0]
        
        # Update vote counts
        if recent_vote["vote_type"] == "like":
            link.likes = max(0, link.likes - 1)
        elif recent_vote["vote_type"] == "dislike":
            link.dislikes = max(0, link.dislikes - 1)
        
        # Save the updated link
        write_links(links_db, links)
        
        # Remove the vote record
        votes = [v for v in votes if not (v["link_id"] == link_id and v["timestamp"] == recent_vote["timestamp"])]
        write_votes(votes_db, votes)
        
        return {"status": "success", "message": "Vote removed successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove vote: {str(e)}")

if __name__ == "__main__":
    # Ensure the db directory exists
    os.makedirs(os.path.dirname(links_db), exist_ok=True)
    
    # Initialize votes file if it doesn't exist
    if not os.path.exists(votes_db):
        with open(votes_db, 'w') as f:
            json.dump([], f)
    
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True
    )