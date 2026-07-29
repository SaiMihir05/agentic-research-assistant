from app.repositories.base import BaseRepository
from app.models.query import ResearchQuery

class QueryRepository(BaseRepository[ResearchQuery]):
    pass

query_repo = QueryRepository(ResearchQuery)
