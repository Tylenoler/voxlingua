# API: Chat endpoint

from fastapi import APIRouter, HTTPException

from models.schemas import ChatRequest
from core.session_manager import session_manager
from llm.cloud import get_llm_client

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def chat(req: ChatRequest):
    """Send a text message and get AI reply."""
    try:
        session = session_manager.get_session(req.session_id)
        if not session:
            session = session_manager.create_session(
                language=req.language,
                scene=req.scene,
            )

        session.add_message("user", req.message)
        history = session.get_history()
        reply = get_llm_client().chat(history, scene=session.scene)
        session.add_message("assistant", reply)

        return {
            "session_id": session.session_id,
            "reply": reply,
            "language": session.language,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
