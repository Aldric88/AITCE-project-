from pydantic import BaseModel, Field
from typing import Optional, List, Literal

NoteStatus = Literal["pending", "approved", "rejected"]
NoteType = Literal["pdf", "doc", "ppt", "image", "link", "text"]


class NoteCreate(BaseModel):
    title: str = Field(min_length=3)
    description: Optional[str] = None

    dept: str
    semester: int
    subject: str
    unit: Optional[str] = None

    tags: List[str] = []
    note_type: NoteType

    # file_url for uploaded files (later from S3/local)
    file_url: Optional[str] = None

    # for link notes
    external_link: Optional[str] = None

    # paid notes
    is_paid: bool = False
    price: int = 0


class NoteResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    dept: str
    semester: int
    subject: str
    unit: Optional[str]
    tags: List[str]
    note_type: NoteType

    file_url: Optional[str]
    external_link: Optional[str]

    status: NoteStatus
    uploader_id: str


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3)
    description: Optional[str] = None

    dept: Optional[str] = None
    semester: Optional[int] = None
    subject: Optional[str] = None
    unit: Optional[str] = None

    tags: Optional[List[str]] = None

    # allow updating link only for link notes
    external_link: Optional[str] = None


class ModerationActionRequest(BaseModel):
    status: Literal["approved", "rejected"]
    reason: Optional[str] = None
