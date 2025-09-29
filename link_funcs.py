from typing import List, Optional
from fastapi import APIRouter
import json
import os
from pydantic import BaseModel

api = APIRouter(prefix="/api")

class Link(BaseModel):
    id: Optional[int] = None  # Add this field
    url: str
    title: str
    description: str

def save_link(db,url,title,description):
    # print(db,url,title,description)
    if os.path.exists(db):
        with open(db, 'r') as f:
            links = json.load(f)
    else:
        links = []
    
    new_id = max([link.get("id",0) for link in links], default=0) + 1
    links_lst = list(links)
    new_link = {"id":new_id, "url": url, "title": title, "description": description}
    links_lst.append(new_link)
    
    # print(new_link)
    # print(links_lst)
    
    f = open(db, "w")
    json.dump(links_lst,f,indent=1)

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
            url=item.get("url", ""),
            title=item.get("title", ""),
            description=item.get("description", "")
        ))
    
    return links