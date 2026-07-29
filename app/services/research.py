import asyncio
import logging
from typing import TypedDict, List, Dict, Any
from google import genai
from google.genai.errors import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import uuid
from langgraph.graph import StateGraph, START, END
from app.config import settings
from app.db.session import AsyncSessionLocal
from app.repositories.query import query_repo
from app.db.qdrant import qdrant_client, COLLECTION_NAME
from qdrant_client.http import models
from app.ai.llm import generate_embeddings
from app.services.events import publish_event

logger = logging.getLogger(__name__)

# State definition for the research graph
class ResearchState(TypedDict):
    query_id: int
    topic: str
    plan: List[str]
    findings: List[Dict[str, str]]
    draft: str
    final_report: str

# Helper to configure and call Gemini API with retry/backoff on rate limits
@retry(
    retry=retry_if_exception_type(ClientError),
    wait=wait_exponential(multiplier=1, min=5, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _call_gemini_sync(prompt: str) -> str:
    """Synchronous Gemini call wrapped with tenacity retry on 429s."""
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text

async def _call_gemini(prompt: str) -> str:
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
    # Run the retrying sync call in a thread pool so the event loop stays free
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call_gemini_sync, prompt)

async def _get_embeddings(text: str) -> list[float]:
    """Async wrapper for generate_embeddings."""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not set.")
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, generate_embeddings, text)

# Node 1: Research Planner
async def plan_research(state: ResearchState) -> Dict[str, Any]:
    query_id = state.get("query_id")
    topic = state["topic"]
    logger.info(f"Generating research plan for topic: {topic}")
    if query_id:
        await publish_event(query_id, "processing", "Planning research layout...")

    # Retrieve past context from Qdrant
    context_str = ""
    try:
        topic_vector = await _get_embeddings(topic)
        search_result = await qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=topic_vector,
            limit=2,
            score_threshold=0.8
        )
        if search_result:
            context_str = "Past research context you can build upon (avoid duplicate work):\n"
            for hit in search_result:
                context_str += f"- Topic: {hit.payload.get('topic')}\n{hit.payload.get('report')[:500]}...\n\n"
    except Exception as e:
        logger.warning(f"Failed to fetch past context from Qdrant: {e}")

    prompt = (
        "You are an expert research planner. "
        "Break down the following research topic into exactly 3 key sub-topics or research questions. "
        "Provide only the sub-topics as a bulleted list (using standard hyphens or asterisks, e.g., - Subtopic).\n\n"
        f"{context_str}"
        f"Topic: {topic}"
    )
    response = await _call_gemini(prompt)

    # Parse lines to extract bullet points
    lines = [line.strip().lstrip("-* ").strip() for line in response.split("\n") if line.strip()]
    subtopics = [line for line in lines if line][:3]

    # Fallback to general topics if parsing didn't find clear lines
    if len(subtopics) < 3:
        subtopics = [
            f"Overview and foundations of {topic}",
            f"Key applications and current state of {topic}",
            f"Future trends and challenges of {topic}"
        ]

    logger.info(f"Planned subtopics: {subtopics}")
    return {"plan": subtopics}

# Node 2: Sub-topic Researcher (Parallel Execution)
async def research_subtopics(state: ResearchState) -> Dict[str, Any]:
    query_id = state.get("query_id")
    topic = state["topic"]
    plan = state["plan"]
    logger.info(f"Researching planned subtopics in parallel...")
    if query_id:
        await publish_event(query_id, "processing", "Investigating subtopics in parallel...")

    async def research_one(subtopic: str) -> Dict[str, str]:
        prompt = (
            f"You are a research analyst investigating a subtopic of the overall topic: {topic}.\n"
            f"Provide a detailed, objective analysis of the subtopic: {subtopic}\n"
            "Keep the analysis comprehensive, factual, and clear."
        )
        logger.info(f"Starting research on: {subtopic}")
        response = await _call_gemini(prompt)
        logger.info(f"Completed research on: {subtopic}")
        return {"subtopic": subtopic, "content": response}

    tasks = [research_one(subtopic) for subtopic in plan]
    findings = await asyncio.gather(*tasks)
    return {"findings": findings}

# Node 3: Synthesis Node
async def synthesize_report(state: ResearchState) -> Dict[str, Any]:
    query_id = state.get("query_id")
    topic = state["topic"]
    findings = state["findings"]
    logger.info(f"Synthesizing sections into a cohesive report for topic: {topic}")
    if query_id:
        await publish_event(query_id, "processing", "Synthesizing research into a draft...")

    findings_str = ""
    for idx, finding in enumerate(findings):
        findings_str += f"### Section {idx+1}: {finding['subtopic']}\n\n{finding['content']}\n\n"

    prompt = (
        "You are a senior editor. Synthesize the following research sections into a cohesive, "
        f"comprehensive, and well-structured markdown report on the topic: {topic}.\n\n"
        "Instructions:\n"
        "1. Write an engaging Introduction explaining the topic's context and relevance.\n"
        "2. Present the detailed findings logically, utilizing the provided research content.\n"
        "3. Conclude with a Summary/Conclusion highlighting the main takeaways and future implications.\n"
        "4. Use clear headings, bullet points, and clean markdown formatting.\n\n"
        f"Research Sections:\n{findings_str}"
    )
    draft = await _call_gemini(prompt)
    return {"draft": draft}

# Node 4: Review and Polish Node
async def review_report(state: ResearchState) -> Dict[str, Any]:
    query_id = state.get("query_id")
    topic = state["topic"]
    draft = state["draft"]
    logger.info(f"Reviewing and polishing final report for topic: {topic}")
    if query_id:
        await publish_event(query_id, "processing", "Reviewing and formatting final report...")

    prompt = (
        "You are a quality assurance reviewer. Review the following draft research report. "
        "Improve the formatting, ensure smooth transitions between sections, fix any typographical errors, "
        "and return a perfectly polished, production-ready markdown report. "
        "Do not include any preambles like 'Here is the polished report:' or comments, just output the final markdown report directly.\n\n"
        f"Draft Report:\n{draft}"
    )
    final_report = await _call_gemini(prompt)

    # Store memory in Qdrant
    try:
        report_vector = await _get_embeddings(topic)
        point_id = str(uuid.uuid4())
        await qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=report_vector,
                    payload={
                        "topic": topic,
                        "report": final_report
                    }
                )
            ]
        )
        logger.info(f"Stored research memory in Qdrant for topic: {topic}")
    except Exception as e:
        logger.warning(f"Failed to store memory in Qdrant: {e}")

    return {"final_report": final_report}

# Build the LangGraph State Machine
workflow = StateGraph(ResearchState)
workflow.add_node("plan", plan_research)
workflow.add_node("research", research_subtopics)
workflow.add_node("synthesize", synthesize_report)
workflow.add_node("review", review_report)

workflow.add_edge(START, "plan")
workflow.add_edge("plan", "research")
workflow.add_edge("research", "synthesize")
workflow.add_edge("synthesize", "review")
workflow.add_edge("review", END)

research_graph = workflow.compile()

# Public Service Interface
async def process_research_query(query_id: int):
    async with AsyncSessionLocal() as db:
        await _process_research_query(query_id, db)

async def _process_research_query(query_id: int, db):
    query_obj = await query_repo.get(db, id=query_id)
    if not query_obj:
        logger.error(f"Query {query_id} not found.")
        return

    try:
        # Update status to processing
        await query_repo.update(db, db_obj=query_obj, obj_in={"status": "processing"})

        initial_state = {
            "query_id": query_id,
            "topic": query_obj.topic,
            "plan": [],
            "findings": [],
            "draft": "",
            "final_report": "",
        }

        logger.info(f"Starting LangGraph workflow for query {query_id}: '{query_obj.topic}'")
        final_state = await research_graph.ainvoke(initial_state)
        result_text = final_state["final_report"]

        # Save the result
        await query_repo.update(
            db,
            db_obj=query_obj,
            obj_in={"result": result_text, "status": "completed"}
        )
        await publish_event(query_id, "completed", "Research finished successfully.", {"result": result_text})
        logger.info(f"Successfully processed query {query_id}")

    except Exception as e:
        logger.exception(f"Failed to process query {query_id}")
        await query_repo.update(
            db,
            db_obj=query_obj,
            obj_in={"status": "failed", "result": f"Error: {str(e)}"}
        )
        await publish_event(query_id, "failed", f"Failed: {str(e)}")
