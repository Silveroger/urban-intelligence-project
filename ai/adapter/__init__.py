"""
SIH 26124 — AI Output Normalization & Backend Ingestion Adapter Layer
Conforms to docs/API_CONTRACT.md, docs/AI_CONTRACT.md, and docs/ARCHITECTURE.md.
"""

from .backend_adapter import BackendIngestAdapter

__all__ = ["BackendIngestAdapter"]
