import asyncio
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .audit import AuditLog
from .config import settings
from .ingestion import ContinuousIngestor, IngestionService
from .llm import EmailLLM, LLMUnavailable
from .mailbox import JsonMailboxSource
from .models import AskRequest, AskResponse, EmailType, PriorityUpdate, WorkTypeUpdate
from .repository import MailboxRepository
from .services import MailboxService
from .workload import paginate_work_items


def build_service() -> tuple[MailboxService, ContinuousIngestor, EmailLLM, AuditLog]:
    llm = EmailLLM()
    repo = MailboxRepository()
    source = JsonMailboxSource(settings.mailbox_path)
    ingestion = IngestionService(source, llm, repo)
    audit = AuditLog()
    service = MailboxService(repo, ingestion, llm, audit)
    return service, ContinuousIngestor(ingestion), llm, audit


def create_app(service: MailboxService | None = None, poller: ContinuousIngestor | None = None) -> FastAPI:
    if service is None:
        service, poller, llm, audit = build_service()
    else:
        poller = poller or ContinuousIngestor(service.ingestion)
        llm = service.llm
        audit = service.audit

    async def poll_mailbox() -> None:
        while True:
            try:
                result = poller.poll()
                if result["threads_processed"]:
                    audit.record(
                        "mailbox_poll",
                        model=llm.model,
                        details=result,
                    )
            except Exception as exc:
                audit.record("mailbox_poll_error", model=llm.model, details={"error": str(exc)})
            await asyncio.sleep(settings.ingest_interval)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        service.ingest()
        poller.prime()
        task = asyncio.create_task(poll_mailbox())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = FastAPI(title="Email Workload Assistant", version="1.2.0", lifespan=lifespan)
    app.state.service = service
    app.state.poller = poller
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    router = APIRouter(prefix="/api")

    @router.get("/health")
    def health():
        status = llm.status()
        return {
            "ok": True,
            "llm_configured": status["available"] and status["model_installed"],
            "llm_provider": "ollama",
            "llm_model": llm.model,
            "llm": status,
        }

    @router.post("/ingest")
    def ingest():
        return service.ingest()

    @router.get("/work-items")
    def work_items(
        q: str = Query("", max_length=200),
        filter: str = Query("action", pattern="^(action|in_progress|archive|done)$"),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
    ):
        try:
            result = paginate_work_items(
                list(service.repo.work_items.values()),
                page=page,
                page_size=page_size,
                query=q,
                filter_name=filter,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return result.as_dict()

    def require_work_item(thread_id: str):
        item = service.repo.get_work_item(thread_id)
        if item is None:
            raise HTTPException(404, "Work item not found.")
        return item

    @router.post("/work-items/{thread_id}/pin")
    def pin(thread_id: str):
        require_work_item(thread_id)
        try:
            return service.set_pinned(thread_id, True)
        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc

    @router.post("/work-items/{thread_id}/unpin")
    def unpin(thread_id: str):
        require_work_item(thread_id)
        try:
            return service.set_pinned(thread_id, False)
        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc

    @router.post("/work-items/{thread_id}/type")
    def set_type(thread_id: str, request: WorkTypeUpdate):
        require_work_item(thread_id)
        try:
            return service.set_email_type(thread_id, request.email_type)
        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc

    @router.post("/work-items/{thread_id}/priority")
    def set_priority(thread_id: str, request: PriorityUpdate):
        require_work_item(thread_id)
        try:
            return service.set_priority(thread_id, request.priority)
        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.post("/work-items/{thread_id}/in-progress")
    def mark_in_progress(thread_id: str):
        require_work_item(thread_id)
        try:
            return service.mark_in_progress(thread_id, True)
        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.post("/work-items/{thread_id}/done")
    def mark_done(thread_id: str):
        require_work_item(thread_id)
        try:
            if service.repo.work_items[thread_id].email_type is not EmailType.ACTION:
                raise HTTPException(409, "Only actionable emails can be marked actioned.")
            return service.mark_done(thread_id, True)
        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.post("/work-items/{thread_id}/incomplete")
    def mark_incomplete(thread_id: str):
        require_work_item(thread_id)
        try:
            return service.mark_done(thread_id, False)
        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc

    @router.get("/threads/{thread_id}")
    def thread(thread_id: str):
        value = service.repo.get_thread(thread_id)
        if value is None:
            raise HTTPException(404, "Thread not found. Ingest the mailbox first.")
        return {
            "thread": value,
            "decision": service.repo.decisions.get(thread_id),
            "work_item": service.repo.get_work_item(thread_id),
        }

    @router.post("/work-items/{thread_id}/analyze")
    def analyze(thread_id: str):
        if service.repo.get_thread(thread_id) is None:
            raise HTTPException(404, "Thread not found. Ingest the mailbox first.")
        try:
            decision, item = service.analyze(thread_id)
        except LLMUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"decision": decision, "work_item": item}

    @router.post("/ask", response_model=AskResponse)
    def ask(request: AskRequest):
        try:
            return service.ask(request)
        except LLMUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(404, "Thread not found.") from exc

    @router.get("/audit")
    def get_audit():
        return audit.recent()

    app.include_router(router)
    return app


app = create_app()
