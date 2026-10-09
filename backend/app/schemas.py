from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

AGE_GROUPS = ["15–17", "18–24", "25–29", "30–34"]
STATUSES = ["received", "reviewed", "reflected", "not_reflected"]


class ConsultationIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    summary: str = ""
    law_reference: str = ""
    organizer: str = ""
    closes_at: datetime | None = None


class ConsultationOut(ConsultationIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    created_at: datetime
    proposal_count: int = 0


class ProposalIn(BaseModel):
    text: str = Field(min_length=10, max_length=4000)
    age_group: str = Field(default="18–24")
    location: str = Field(default="Улаанбаатар", max_length=60)
    consultation_id: int | None = None


class ClassificationOut(BaseModel):
    category: str
    sentiment: str
    urgency: str
    confidence: float
    classifier: str


class ReceiptOut(BaseModel):
    proposal_id: int
    content_hash: str
    block_index: int
    block_hash: str
    prev_hash: str
    timestamp: str
    classification: ClassificationOut
    owner_secret: str  # shown once; lets the author erase their proposal later


class ProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    consultation_id: int | None
    text: str | None
    age_group: str
    location: str
    category: str
    sentiment: str
    urgency: str
    confidence: float
    classifier: str
    status: str
    response_note: str
    content_hash: str
    created_at: datetime
    erased: bool = False


class ReceiptStatus(BaseModel):
    proposal_id: int
    status: str
    response_note: str
    category: str
    created_at: datetime
    block_index: int
    block_hash: str
    integrity: str  # intact | modified | erased
    consultation_title: str | None = None


class AdminUpdate(BaseModel):
    status: str | None = None
    response_note: str | None = None


class EraseIn(BaseModel):
    owner_secret: str = Field(min_length=8)
