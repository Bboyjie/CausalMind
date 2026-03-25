from __future__ import annotations


def success(data=None, message: str | None = "success", code: int = 200) -> dict:
    payload: dict = {"code": code}
    if message is not None:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return payload


def error(message: str, code: int = 40000) -> dict:
    return {"code": code, "message": message}

