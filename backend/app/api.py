import asyncio
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .audit import AuditLog
from .config import settings
from .ingestion import ContinuousIngestor, IngestionService
from .llm import EmailLLM, LLMUnavailable
from .mailbox import JsonMailboxSource
from .models import (
    AskRequest,
    AskResponse,
    EmailType,
    PriorityUpdate,
    WorkTypeUpdate,
)
from .repository import MailboxRepository
from .services import MailboxService
from .workload import paginate_work_items


def build_service() -> tuple[MailboxService, ContinuousIngestor, EmailLLM, AuditLog]:
    """Build the application's core services and their dependencies.

    The dependency chain is deliberately assembled here so that the API
    layer does not need to know how repositories, ingestion, LLM support,
    and auditing are wired together.
    """
    llm = EmailLLM()
    repository = MailboxRepository()
    mailbox_source = JsonMailboxSource(settings.mailbox_path)
    ingestion = IngestionService(mailbox_source, llm, repository)
    audit = AuditLog()

    service = MailboxService(
        repository,
        ingestion,
        llm,
        audit,
    )
    poller = ContinuousIngestor(ingestion)

    return service, poller, llm, audit


def create_app(
    service: MailboxService | None = None,
    poller: ContinuousIngestor | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    A service can be supplied by tests or other callers that need to
    provide their own dependencies. In normal application startup,
    ``build_service`` creates the production dependencies.
    """
    if service is None:
        service, poller, llm, audit = build_service()
    else:
        # When a service is injected, reuse its dependencies so that
        # the API, poller, LLM and audit log all operate on the same state.
        poller = poller or ContinuousIngestor(service.ingestion)
        llm = service.llm
        audit = service.audit

    async def poll_mailbox() -> None:
        """Continuously check the mailbox for newly available messages.

        Polling errors are recorded in the audit log rather than stopping
        the background task. This keeps mailbox monitoring alive even when
        an individual poll fails.
        """
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
                audit.record(
                    "mailbox_poll_error",
                    model=llm.model,
                    details={"error": str(exc)},
                )

            await asyncio.sleep(settings.ingest_interval)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initialise the mailbox and start/stop background polling.

        The initial ingestion loads the current mailbox before the
        application starts accepting requests. ``prime`` then prepares
        the poller so that it can detect subsequent changes without
        reprocessing the existing mailbox unnecessarily.
        """
        service.ingest()
        poller.prime()

        polling_task = asyncio.create_task(poll_mailbox())

        try:
            yield
        finally:
            # Stop the background poller cleanly when the application
            # shuts down.
            polling_task.cancel()

            try:
                await polling_task
            except asyncio.CancelledError:
                pass

    app = FastAPI(
        title="Email Workload Assistant",
        version="1.2.0",
        lifespan=lifespan,
    )

    # Store the main application services on ``app.state`` so they are
    # available to the running application and easy to replace in tests.
    app.state.service = service
    app.state.poller = poller

    # The React development server runs on port 5173.
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
        """Return API and LLM availability information."""
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
        """Run a mailbox ingestion cycle on demand."""
        return service.ingest()

    @router.get("/work-items")
    def work_items(
        q: str = Query("", max_length=200),
        filter: str = Query(
            "action",
            pattern="^(action|in_progress|archive|done)$",
        ),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
    ):
        """Return a filtered and paginated list of workload items."""
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
        """Return a work item or raise a standard 404 response."""
        item = service.repo.get_work_item(thread_id)

        if item is None:
            raise HTTPException(404, "Work item not found.")

        return item

    @router.post("/work-items/{thread_id}/pin")
    def pin(thread_id: str):
        """Pin a work item so it remains prominent in the workload."""
        require_work_item(thread_id)

        try:
            return service.set_pinned(thread_id, True)
        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc

    @router.post("/work-items/{thread_id}/unpin")
    def unpin(thread_id: str):
        """Remove the pinned state from a work item."""
        require_work_item(thread_id)

        try:
            return service.set_pinned(thread_id, False)
        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc

    @router.post("/work-items/{thread_id}/type")
    def set_type(thread_id: str, request: WorkTypeUpdate):
        """Change the classification of a work item."""
        require_work_item(thread_id)

        try:
            return service.set_email_type(thread_id, request.email_type)
        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc

    @router.post("/work-items/{thread_id}/priority")
    def set_priority(thread_id: str, request: PriorityUpdate):
        """Set a manual priority for an actionable work item."""
        require_work_item(thread_id)

        try:
            return service.set_priority(thread_id, request.priority)
        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.post("/work-items/{thread_id}/in-progress")
    def mark_in_progress(thread_id: str):
        """Move an actionable work item into the In Progress state."""
        require_work_item(thread_id)

        try:
            return service.mark_in_progress(thread_id, True)
        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.post("/work-items/{thread_id}/done")
    def mark_done(thread_id: str):
        """Mark an actionable work item as Actioned."""
        require_work_item(thread_id)

        try:
            # Informational and irrelevant emails cannot enter the
            # Actioned state because they do not represent work items.
            if service.repo.work_items[thread_id].email_type is not EmailType.ACTION:
                raise HTTPException(
                    409,
                    "Only actionable emails can be marked actioned.",
                )

            return service.mark_done(thread_id, True)

        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.post("/work-items/{thread_id}/incomplete")
    def mark_incomplete(thread_id: str):
        """Reopen an Actioned work item and return it to In Progress."""
        require_work_item(thread_id)

        try:
            return service.mark_done(thread_id, False)
        except KeyError as exc:
            raise HTTPException(404, "Work item not found.") from exc

    @router.get("/threads/{thread_id}")
    def thread(thread_id: str):
        """Return a thread together with its decision and work item."""
        value = service.repo.get_thread(thread_id)

        if value is None:
            raise HTTPException(
                404,
                "Thread not found. Ingest the mailbox first.",
            )

        return {
            "thread": value,
            "decision": service.repo.decisions.get(thread_id),
            "work_item": service.repo.get_work_item(thread_id),
        }

    @router.post("/work-items/{thread_id}/analyze")
    def analyze(thread_id: str):
        """Run LLM analysis for an actionable thread.

        The service performs the business validation and analysis.
        API-level errors are translated into appropriate HTTP responses.
        """
        if service.repo.get_thread(thread_id) is None:
            raise HTTPException(
                404,
                "Thread not found. Ingest the mailbox first.",
            )

        try:
            decision, item = service.analyze(thread_id)
        except LLMUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

        return {
            "decision": decision,
            "work_item": item,
        }

    @router.post("/ask", response_model=AskResponse)
    def ask(request: AskRequest):
        """Answer a natural-language question about the mailbox workload."""
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
        """Return the most recent audit events."""
        return audit.recent()

    app.include_router(router)

    return app


# Application instance used by the ASGI server.
app = create_app()