from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

if __package__:
    from . import classifier, database
    from .models import Ticket, TicketCreate, TicketCreated
else:
    import classifier
    import database
    from models import Ticket, TicketCreate, TicketCreated


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    database.initialize_database()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/api/tickets", response_model=TicketCreated, status_code=201)
def create_ticket(ticket: TicketCreate) -> TicketCreated:
    name = ticket.name.strip()
    description = ticket.description.strip()
    if not name or not description:
        raise HTTPException(
            status_code=422,
            detail="Name and description must not be blank.",
        )

    classification = classifier.classify_ticket(description)
    ticket_id = database.create_ticket(
        name,
        description,
        str(classification["priority"]),
        float(classification["confidence"]),
    )
    saved_ticket = database.get_ticket_by_id(ticket_id)
    if saved_ticket is None:
        raise RuntimeError(f"Created ticket {ticket_id} could not be retrieved.")

    return TicketCreated(
        id=ticket_id,
        priority=saved_ticket["priority"],
        confidence=saved_ticket["confidence"],
        created_at=saved_ticket["created_at"],
    )


@app.get("/api/tickets", response_model=list[Ticket])
def get_tickets() -> list[Ticket]:
    return [Ticket(**ticket) for ticket in database.get_open_tickets()]


@app.delete("/api/tickets/{ticket_id}", status_code=204)
def clear_ticket(ticket_id: int) -> Response:
    if not database.clear_ticket(ticket_id):
        raise HTTPException(status_code=404, detail="Ticket not found.")
    return Response(status_code=204)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def serve_user_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "user.html")


@app.get("/admin", include_in_schema=False)
def serve_admin_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "admin.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")