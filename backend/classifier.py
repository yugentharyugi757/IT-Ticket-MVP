from pathlib import Path
from typing import Any, cast

import chromadb
from chromadb.api.types import Metadata, PyEmbedding
from sklearn.feature_extraction.text import TfidfVectorizer


CHROMA_PATH = Path(__file__).resolve().parent.parent / "chroma_data"
COLLECTION_NAME = "ticket_priority"
COLLECTION_VERSION = "tfidf-v1"

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

reference_documents: list[str] = []
reference_metadatas: list[Metadata] = []
reference_ids: list[str] = []
for priority, tickets in REFERENCE_TICKETS.items():
    for index, ticket in enumerate(tickets):
        reference_documents.append(ticket)
        reference_metadatas.append({"priority": priority})
        reference_ids.append(f"{priority.lower()}-{index}")

vectorizer: TfidfVectorizer = TfidfVectorizer()
vectorizer_runtime = cast(Any, vectorizer)
reference_matrix = vectorizer_runtime.fit_transform(reference_documents)

CHROMA_PATH.mkdir(parents=True, exist_ok=True)
client = chromadb.PersistentClient(path=str(CHROMA_PATH))
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={
        "hnsw:space": "cosine",
        "embedding_type": COLLECTION_VERSION,
    },
)

if collection.metadata.get("embedding_type") != COLLECTION_VERSION:
    client.delete_collection(name=COLLECTION_NAME)
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine",
            "embedding_type": COLLECTION_VERSION,
        },
    )

if collection.count() == 0:
    collection.add(
        documents=reference_documents,
        embeddings=cast(
            list[PyEmbedding],
            reference_matrix.toarray().tolist(),
        ),
        metadatas=reference_metadatas,
        ids=reference_ids,
    )


def classify_ticket(ticket_text: str) -> dict[str, str | float]:
    ticket_matrix = vectorizer_runtime.transform([ticket_text])
    if ticket_matrix.nnz == 0:
        raise ValueError("Ticket text contains no terms found in reference tickets.")

    result = collection.query(
        query_embeddings=[
            cast(list[float], ticket_matrix.toarray()[0].tolist())
        ],
        n_results=1,
        include=["metadatas", "distances"],
    )

    metadatas = result["metadatas"]
    distances = result["distances"]
    if not metadatas or not metadatas[0] or not distances or not distances[0]:
        raise RuntimeError("ChromaDB returned no matching reference ticket.")

    priority = metadatas[0][0].get("priority")
    distance = distances[0][0]
    if not isinstance(priority, str):
        raise RuntimeError("ChromaDB returned an incomplete matching ticket.")

    confidence = max(0.0, min(1.0, 1.0 - float(distance)))
    return {"priority": priority, "confidence": confidence}
