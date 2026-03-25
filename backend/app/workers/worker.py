from __future__ import annotations

# Import tasks to ensure they are registered with Huey.
from app.workers.huey_app import huey  # noqa: F401
from app.workers import tasks  # noqa: F401

