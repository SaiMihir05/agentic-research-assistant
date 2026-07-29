import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.research import (
    plan_research,
    research_subtopics,
    synthesize_report,
    review_report,
    research_graph,
    _process_research_query,
)

@pytest.mark.asyncio
@patch("app.services.research._call_gemini")
@patch("app.services.research._get_embeddings")
@patch("app.services.research.qdrant_client")
@patch("app.services.research.publish_event")
async def test_plan_research(mock_publish, mock_qdrant, mock_get_embeddings, mock_call_gemini):
    # Mock Gemini response returning a bulleted list
    mock_call_gemini.return_value = "- Subtopic A\n- Subtopic B\n- Subtopic C"
    mock_get_embeddings.return_value = [0.1] * 768
    mock_qdrant.search = AsyncMock(return_value=[])

    state = {"topic": "artificial intelligence", "plan": [], "findings": [], "draft": "", "final_report": ""}
    result = await plan_research(state)

    assert result == {"plan": ["Subtopic A", "Subtopic B", "Subtopic C"]}
    mock_call_gemini.assert_called_once()

@pytest.mark.asyncio
@patch("app.services.research._call_gemini")
@patch("app.services.research.publish_event")
async def test_research_subtopics(mock_publish, mock_call_gemini):
    mock_call_gemini.return_value = "Detailed research details"

    state = {
        "topic": "artificial intelligence",
        "plan": ["Subtopic A", "Subtopic B"],
        "findings": [],
        "draft": "",
        "final_report": ""
    }
    result = await research_subtopics(state)

    assert len(result["findings"]) == 2
    assert result["findings"][0]["subtopic"] == "Subtopic A"
    assert result["findings"][0]["content"] == "Detailed research details"
    assert mock_call_gemini.call_count == 2

@pytest.mark.asyncio
@patch("app.services.research._call_gemini")
@patch("app.services.research.publish_event")
async def test_synthesize_report(mock_publish, mock_call_gemini):
    mock_call_gemini.return_value = "Synthesized Draft Report"

    state = {
        "topic": "artificial intelligence",
        "plan": ["Subtopic A"],
        "findings": [{"subtopic": "Subtopic A", "content": "findings details"}],
        "draft": "",
        "final_report": ""
    }
    result = await synthesize_report(state)

    assert result == {"draft": "Synthesized Draft Report"}
    mock_call_gemini.assert_called_once()

@pytest.mark.asyncio
@patch("app.services.research._call_gemini")
@patch("app.services.research._get_embeddings")
@patch("app.services.research.qdrant_client")
@patch("app.services.research.publish_event")
async def test_review_report(mock_publish, mock_qdrant, mock_get_embeddings, mock_call_gemini):
    mock_call_gemini.return_value = "# Final Polished Report"
    mock_get_embeddings.return_value = [0.1] * 768
    mock_qdrant.upsert = AsyncMock()

    state = {
        "topic": "artificial intelligence",
        "plan": [],
        "findings": [],
        "draft": "Synthesized Draft Report",
        "final_report": ""
    }
    result = await review_report(state)

    assert result == {"final_report": "# Final Polished Report"}
    mock_call_gemini.assert_called_once()

@pytest.mark.asyncio
@patch("app.services.research._call_gemini")
@patch("app.services.research._get_embeddings")
@patch("app.services.research.qdrant_client")
@patch("app.services.research.publish_event")
async def test_research_graph_execution(mock_publish, mock_qdrant, mock_get_embeddings, mock_call_gemini):
    mock_get_embeddings.return_value = [0.1] * 768
    mock_qdrant.search = AsyncMock(return_value=[])
    mock_qdrant.upsert = AsyncMock()
    # Set up mock returns for each of the nodes sequentially
    mock_call_gemini.side_effect = [
        "- Topic A\n- Topic B\n- Topic C",  # plan
        "Research A",                        # research 1
        "Research B",                        # research 2
        "Research C",                        # research 3
        "Draft Report Content",              # synthesize
        "# Polished Report Content"          # review
    ]

    initial_state = {
        "topic": "quantum computing",
        "plan": [],
        "findings": [],
        "draft": "",
        "final_report": "",
    }

    final_state = await research_graph.ainvoke(initial_state)

    assert final_state["final_report"] == "# Polished Report Content"
    assert len(final_state["plan"]) == 3
    assert len(final_state["findings"]) == 3
    assert final_state["draft"] == "Draft Report Content"

@pytest.mark.asyncio
@patch("app.services.research.query_repo")
@patch("app.services.research.research_graph")
@patch("app.services.research.publish_event")
async def test_process_research_query(mock_publish, mock_graph, mock_repo):
    db_mock = AsyncMock()

    query_obj = MagicMock()
    query_obj.id = 42
    query_obj.topic = "fusion energy"
    query_obj.status = "pending"

    mock_repo.get = AsyncMock(return_value=query_obj)
    mock_repo.update = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value={
        "final_report": "# Fusion Energy Report"
    })

    await _process_research_query(query_id=42, db=db_mock)

    mock_repo.update.assert_any_call(
        db_mock,
        db_obj=query_obj,
        obj_in={"status": "processing"}
    )
    mock_repo.update.assert_any_call(
        db_mock,
        db_obj=query_obj,
        obj_in={"result": "# Fusion Energy Report", "status": "completed"}
    )
