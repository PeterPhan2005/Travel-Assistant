"""Database metadata and models.

Importing this package defines mappings only. Engines and sessions belong to
later application tasks and are never created at module import time.
"""

from app.db.base import Base

__all__ = ["Base"]
