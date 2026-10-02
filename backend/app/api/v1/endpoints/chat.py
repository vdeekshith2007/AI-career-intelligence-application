"""
Chat endpoints for the RAG-powered career advisor.

TODO: Full RAG implementation in Phase 5.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.auth import MessageResponse
from app.api.v1.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatSessionResponse,
    CreateSessionRequest,
    SendMessageRequest,
)
from app.core.exceptions import NotFoundException
from app.core.security import get_current_user
from app.db.session import get_async_session
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.services.career_agents import execute_career_agent_graph

router = APIRouter()


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_session(
    payload: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Start a new conversation with the career advisor."""
    session = ChatSession(
        user_id=current_user.id,
        title=payload.title or "New Conversation",
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)

    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get(
    "/sessions",
    response_model=list[ChatSessionResponse],
    summary="List chat sessions",
)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get all chat sessions for the current user."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    sessions = result.scalars().all()

    response = []
    for s in sessions:
        msg_count = await db.execute(
            select(func.count()).where(ChatMessage.session_id == s.id)
        )
        response.append(
            ChatSessionResponse(
                id=s.id,
                title=s.title,
                is_active=s.is_active,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=msg_count.scalar() or 0,
            )
        )

    return response


@router.get(
    "/sessions/{session_id}",
    response_model=ChatHistoryResponse,
    summary="Get session with messages",
)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get a chat session with its full message history."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Chat Session", session_id)

    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = msg_result.scalars().all()

    return ChatHistoryResponse(
        session=ChatSessionResponse(
            id=session.id,
            title=session.title,
            is_active=session.is_active,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(messages),
        ),
        messages=[
            ChatMessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                sources=m.sources,
                token_count=m.token_count,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
)
async def send_message(
    session_id: UUID,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Send a message to the career advisor and get an AI response.

    TODO: Connect to Career Advisor Agent with RAG pipeline in Phase 5.
    """
    # Verify session ownership
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Chat Session", session_id)

    # Save user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=payload.content,
    )
    db.add(user_msg)
    await db.flush()

    # Execute LangGraph Multi-Agent System (Router -> Specialist Agent -> Tools/RAG -> Synthesizer)
    agent_result = await execute_career_agent_graph(
        db=db,
        user_id=current_user.id,
        query=payload.content,
    )

    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=agent_result["content"],
        sources=agent_result["sources"],
        token_count=agent_result["token_count"],
    )
    db.add(assistant_msg)
    await db.flush()
    await db.refresh(assistant_msg)

    return ChatMessageResponse(
        id=assistant_msg.id,
        role=assistant_msg.role,
        content=assistant_msg.content,
        sources=assistant_msg.sources,
        token_count=assistant_msg.token_count,
        created_at=assistant_msg.created_at,
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=MessageResponse,
    summary="Delete a chat session",
)
async def delete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Delete a chat session and all its messages."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundException("Chat Session", session_id)

    await db.delete(session)
    await db.flush()

    return MessageResponse(message="Chat session deleted successfully.")
