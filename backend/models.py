from pydantic import BaseModel, Field, field_validator


class TicketCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)

    @field_validator("name", "description")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class Ticket(BaseModel):
    id: int
    name: str
    description: str
    priority: str
    confidence: float
    status: str
    created_at: str


class TicketCreated(BaseModel):
    id: int
    priority: str
    confidence: float
    created_at: str