from fastapi import APIRouter, Depends

router = APIRouter()


def require_user():
    """Peer dependency used by mutating routes."""
    return {"id": "user"}


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/items")
def list_items():
    rows = db_all()
    return rows


@router.post("/items")
def create_item(body: dict):
    if not body.get("name"):
        return {"error": "name is required"}
    return {"ok": True}


def db_all():
    return [{"id": "1", "name": "one"}]
