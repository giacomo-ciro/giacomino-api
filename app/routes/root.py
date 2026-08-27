from fastapi import APIRouter

from app.schemas.root import RootResponse

router = APIRouter(tags=["General"])


@router.get("/", response_model=RootResponse)
def hello_world():
    return {"message": "Giacomo Ciro's Personal Chatbot API"}
