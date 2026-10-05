import json
import os
import urllib.error
import urllib.request

from .models import LLMDecision


OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434",
)
DEFAULT_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:3b",
)


SYSTEM_PROMPT = """You are decision support for an insurance claims handler.

The application has ALREADY determined the mailbox workflow type using deterministic
business rules: action, informational, or irrelevant. Do not change that classification.

Your job is to help the handler understand the email and make a decision about the work.
Return ONLY valid JSON matching this schema:
{
  "topic": "short topic",
  "actions": ["specific action the handler appears to need to take"],
  "urgency_signals": ["explicit evidence of urgency from the email"],
  "importance_signals": ["explicit evidence of importance or impact from the email"],
  "summary": "one or two sentence factual summary",
  "confidence": 0.0,
  "rationale": "brief evidence-based rationale"
}

Rules:
- Use only evidence in the supplied thread.
- Only categorize into action, informational, or irrelevant.
- Do not invent deadlines, policy decisions, facts, people, payments, actions, or commitments.
- Only list an action when the email explicitly requests it or the next action is clearly required by the thread.
- Urgency and importance signals must be grounded in explicit evidence. Empty arrays are valid.
- Prefer the latest state of the thread while considering earlier messages.
- Confidence must be between 0 and 1.
"""


class LLMUnavailable(RuntimeError):
    """Raised when Ollama cannot provide a usable response."""


class EmailLLM:
    """Ollama adapter for AI decision support and natural-language Q&A."""

    def __init__(self) -> None:
        """Load Ollama connection settings from the environment."""
        self.base_url = os.getenv(
            "OLLAMA_URL",
            OLLAMA_URL,
        ).rstrip("/")
        self.model = os.getenv(
            "OLLAMA_MODEL",
            DEFAULT_MODEL,
        )
        self.timeout = int(
            os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"),
        )

    def _chat(
        self,
        system: str,
        user: str,
        json_mode: bool = False,
    ) -> str:
        """Send a chat request to Ollama and return the model response."""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": user,
                },
            ],
            "stream": False,
            "options": {
                "temperature": 0,
            },
        }

        if json_mode:
            payload["format"] = "json"

        data = self._request(
            "/api/chat",
            payload,
        )

        content = data.get("message", {}).get("content")

        if not content:
            raise LLMUnavailable(
                "Ollama returned no model response.",
            )

        return content

    def _request(
        self,
        path: str,
        payload: dict,
    ) -> dict:
        """Send a JSON POST request to Ollama."""
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                return json.loads(
                    response.read().decode("utf-8"),
                )

        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(
                "utf-8",
                errors="replace",
            ).strip()

            if exc.code == 404 and self.model:
                message = (
                    f"Ollama is running at {self.base_url}, "
                    f"but model '{self.model}' was not found. "
                    f"Run: ollama pull {self.model}"
                )
            else:
                message = (
                    f"Ollama returned HTTP {exc.code} "
                    f"at {self.base_url}."
                )

            if detail:
                message += f" Details: {detail[:300]}"

            raise LLMUnavailable(message) from exc

        except (urllib.error.URLError, TimeoutError) as exc:
            reason = getattr(exc, "reason", None)
            suffix = f" ({reason})" if reason else ""

            raise LLMUnavailable(
                f"Cannot connect to Ollama at {self.base_url}{suffix}. "
                f"Start Ollama and ensure {self.model} is installed."
            ) from exc

        except json.JSONDecodeError as exc:
            raise LLMUnavailable(
                "Ollama returned an invalid response.",
            ) from exc

    def status(self) -> dict:
        """Return Ollama connectivity and model diagnostics."""
        try:
            request = urllib.request.Request(
                f"{self.base_url}/api/tags",
                method="GET",
            )

            with urllib.request.urlopen(
                request,
                timeout=3,
            ) as response:
                data = json.loads(
                    response.read().decode("utf-8"),
                )

            models = [
                str(item.get("name", ""))
                for item in data.get("models", [])
                if isinstance(item, dict)
            ]

            installed = any(
                name == self.model
                or name.startswith(f"{self.model}:")
                for name in models
            )

            message = (
                "Ollama is ready."
                if installed
                else (
                    f"Ollama is running, but '{self.model}' "
                    f"is not installed. Run: ollama pull {self.model}"
                )
            )

            return {
                "available": True,
                "model_installed": installed,
                "url": self.base_url,
                "model": self.model,
                "models": models,
                "message": message,
            }

        except urllib.error.HTTPError as exc:
            return self._unavailable_status(
                f"Ollama returned HTTP {exc.code} at {self.base_url}.",
            )

        except (urllib.error.URLError, TimeoutError) as exc:
            reason = getattr(exc, "reason", None)
            suffix = f" ({reason})" if reason else ""

            return self._unavailable_status(
                f"Cannot connect to Ollama at {self.base_url}{suffix}. "
                "Start Ollama first.",
            )

        except (json.JSONDecodeError, ValueError) as exc:
            return self._unavailable_status(
                f"Ollama returned an invalid /api/tags response: {exc}",
            )

    def _unavailable_status(self, message: str) -> dict:
        """Build a consistent unavailable-status response."""
        return {
            "available": False,
            "model_installed": False,
            "url": self.base_url,
            "model": self.model,
            "models": [],
            "message": message,
        }

    def is_available(self) -> bool:
        """Return whether Ollama and the configured model are available."""
        status = self.status()
        return bool(
            status["available"]
            and status["model_installed"]
        )

    def classify(self, thread_text: str) -> LLMDecision:
        """Generate structured AI decision support for a thread."""
        try:
            response = self._chat(
                SYSTEM_PROMPT,
                thread_text,
                json_mode=True,
            )
            data = json.loads(response)

            return LLMDecision.model_validate(data)

        except json.JSONDecodeError as exc:
            raise LLMUnavailable(
                "Ollama returned non-JSON decision-support output.",
            ) from exc

    def answer(
        self,
        question: str,
        evidence: str,
        mode: str = "thread_search",
        history: list[dict[str, str]] | None = None,
    ) -> dict:
        """Answer a mailbox question using only the supplied evidence."""
        system = self._question_system_prompt(mode)
        messages = self._build_history(
            question,
            evidence,
            history,
        )

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system,
                },
                *messages,
            ],
            "stream": False,
            "options": {
                "temperature": 0,
            },
            "format": "json",
        }

        data = self._request(
            "/api/chat",
            payload,
        )

        content = data.get("message", {}).get("content")

        if not content:
            raise LLMUnavailable(
                "Ollama returned no model response.",
            )

        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMUnavailable(
                "Ollama returned non-JSON Q&A output.",
            ) from exc

        return self._parse_answer(result)

    @staticmethod
    def _question_system_prompt(mode: str) -> str:
        """Return the system prompt for the requested Q&A mode."""
        if mode == "workload":
            system = """You support an insurance claims handler deciding what deserves attention.
The evidence has already been classified by deterministic business rules as action,
informational, or irrelevant. Do not invent a priority score or priority category.
Use the evidence and any available urgency/importance signals to help the handler decide
what to focus on. If an item has not been analysed by AI, say so rather than pretending
that urgency or importance has been assessed. Cite thread IDs in square brackets.
Never invent actions, deadlines, policy decisions, payments, people, or facts."""
        else:
            system = """You are a mailbox assistant for an insurance claims handler.
Use ONLY the supplied mailbox evidence and the conversation context. Answer naturally,
like a helpful chat assistant, while staying concise and factual. If the question is
related to the supplied evidence but the evidence is insufficient, say so. Never invent
facts, actions, deadlines, policy decisions, payments, people, or commitments. Cite
thread IDs when useful. The application, not you, determines whether a thread is
actionable, informational, or irrelevant."""

        return system + """

Return ONLY valid JSON matching this schema:
{
  "answer": "concise answer to the user's question",
  "suggested_questions": ["one useful follow-up question", "another useful follow-up question"]
}
Provide 2-3 genuinely useful follow-up questions grounded in the supplied evidence. Do not
repeat the user's question. If there is no sensible follow-up, return an empty array."""

    @staticmethod
    def _build_history(
        question: str,
        evidence: str,
        history: list[dict[str, str]] | None,
    ) -> list[dict[str, str]]:
        """Keep valid conversation history and append the current question."""
        messages = [
            message
            for message in history or []
            if message.get("role") in {"user", "assistant"}
            and message.get("content")
        ]

        messages.append(
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Mailbox evidence:\n{evidence}"
                ),
            },
        )

        return messages

    @staticmethod
    def _parse_answer(result: dict) -> dict:
        """Validate and normalise the model's Q&A response."""
        answer = result.get("answer")
        suggestions = result.get(
            "suggested_questions",
            [],
        )

        if not isinstance(answer, str) or not answer.strip():
            raise LLMUnavailable(
                "Ollama returned no answer.",
            )

        if not isinstance(suggestions, list):
            suggestions = []

        return {
            "answer": answer.strip(),
            "suggested_questions": [
                str(item).strip()
                for item in suggestions
                if str(item).strip()
            ][:4],
        }