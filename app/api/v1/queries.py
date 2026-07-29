from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from app.db.session import get_db
from app.schemas.query import QueryCreate, QueryResponse
from app.repositories.query import query_repo
from app.repositories.user import user_repo
from app.services.research import process_research_query
from app.services.events import subscribe_events

router = APIRouter(prefix="/queries", tags=["queries"])

@router.post("/", response_model=QueryResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_query(
    query_in: QueryCreate, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    # Validate user
    user = await user_repo.get(db, id=query_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create query in db
    query_obj = await query_repo.create(db, obj_in=query_in.model_dump())

    # Dispatch background task
    background_tasks.add_task(process_research_query, query_obj.id)

    return query_obj

@router.get("/{query_id}", response_model=QueryResponse)
async def read_query(query_id: int, db: AsyncSession = Depends(get_db)):
    query_obj = await query_repo.get(db, id=query_id)
    if not query_obj:
        raise HTTPException(status_code=404, detail="Query not found")
    return query_obj

@router.get("/{query_id}/stream")
async def stream_query(query_id: int):
    """
    Stream live updates for a query via Server-Sent Events (SSE).
    """
    return EventSourceResponse(subscribe_events(query_id))
