from pydantic import BaseModel
from datetime import datetime

class PodcastToSync(BaseModel):
    id: str
    date: datetime
    download_url: str
    title: str