from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


MODEL_NAME = "all-MiniLM-L6-v2"
CHROMA_PATH = Path(__file__).resolve().parent.parent / "chroma_data"
COLLECTION_NAME = "ticket_priority"

REFERENCE_TICKETS = {
    "HIGH": [
        "Production server is completely down",
        "Company network is unavailable",
        "Critical application is inaccessible",
        "Security breach detected",
        "Database server has crashed",
        "Entire office internet is down",
    ],
    "MEDIUM": [
        "Corporate VPN is not connecting",
        "Outlook is not synchronizing emails",
        "Software application is malfunctioning",
        "Network connection is unstable",
        "Internal application cannot be accessed",
        "Laptop has connectivity problems",
    ],
    "LOW": [
        "Software installation is required",
        "Install Google Chrome",
        "Password reset request",
        "Printer configuration request",
        "Desktop configuration request",
        "Install a development tool",
    ],
}


def _seed_collection(
    collection: chromadb.Collection,
    model: SentenceTransformer,
) -> None:
    if collection.count() != 0:
        return

    documents: list[str] = []
    metadatas: list[dict[str, str]] = []
    ids: list[str] = []
    for priority, tickets in REFERENCE_TICKETS.items():
        for index, ticket in enumerate(tickets):
            documents.append(ticket)
            metadatas.append({"priority": priority})
            ids.append(f"{priority.lower()}-{index}")

    embeddings = model.encode(documents).tolist()
    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )


CHROMA_PATH.mkdir(parents=True, exist_ok=True)
model = SentenceTransformer(MODEL_NAME)
client = chromadb.PersistentClient(path=str(CHROMA_PATH))
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)
_seed_collection(collection, model)


def classify_ticket(ticket_text: str) -> dict[str, str | float]:
    embedding = model.encode(ticket_text).tolist()
    result = collection.query(
        query_embeddings=[embedding],
        n_results=1,
        include=["metadatas", "distances"],
    )

    metadatas = result["metadatas"]
    distances = result["distances"]
    if not metadatas or not metadatas[0] or not distances or not distances[0]:
        raise RuntimeError("ChromaDB returned no matching reference ticket.")

    priority = metadatas[0][0].get("priority")
    distance = distances[0][0]
    if priority is None or distance is None:
        raise RuntimeError("ChromaDB returned an incomplete matching ticket.")

    confidence = max(0.0, min(1.0, 1.0 - float(distance)))
    return {"priority": priority, "confidence": confidence}