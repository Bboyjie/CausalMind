from __future__ import annotations

from huey import SqliteHuey

from app.core.config import HUEY_DB_PATH

huey = SqliteHuey("wolong", filename=HUEY_DB_PATH)

