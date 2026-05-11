"""Coding-focused agent implementation."""

from __future__ import annotations

import asyncio
import textwrap

from agents.base_agent import AgentResult, BaseAgent


class CodingAgent(BaseAgent):
    """Generates implementation plans and code skeletons for software tasks."""

    _KEYWORDS = {
        "code",
        "implement",
        "build",
        "fix",
        "bug",
        "optimize",
        "refactor",
        "python",
        "api",
    }

    async def can_handle(self, task: str) -> bool:
        lowered = task.lower()
        return any(keyword in lowered for keyword in self._KEYWORDS)

    async def handle(self, task: str, correlation_id: str) -> AgentResult:
        await asyncio.sleep(0)
        language = self._detect_language(task)
        snippet = self._generate_snippet(task, language)
        checklist = [
            "Define acceptance criteria and edge cases.",
            "Implement modular components with tests.",
            "Run static checks and validate runtime behavior.",
        ]
        return AgentResult(
            agent=self.name,
            status="success",
            output={
                "language": language,
                "implementation_plan": checklist,
                "generated_code": snippet,
            },
            metadata={"correlation_id": correlation_id, "snippet_lines": len(snippet.splitlines())},
        )

    def _detect_language(self, task: str) -> str:
        lowered = task.lower()
        if "javascript" in lowered or "typescript" in lowered or "node" in lowered:
            return "javascript"
        if "go " in f"{lowered} " or "golang" in lowered:
            return "go"
        if "rust" in lowered:
            return "rust"
        return "python"

    def _generate_snippet(self, task: str, language: str) -> str:
        if language == "javascript":
            return textwrap.dedent(
                """\
                export async function executeTask(context) {
                  if (!context || !context.task) {
                    throw new Error("context.task is required");
                  }
                  return {
                    status: "ok",
                    task: context.task,
                    processedAt: new Date().toISOString(),
                  };
                }
                """
            ).strip()
        if language == "go":
            return textwrap.dedent(
                """\
                package taskrunner

                import "time"

                type Result struct {
                	Status      string
                	Task        string
                	ProcessedAt time.Time
                }

                func ExecuteTask(task string) Result {
                	return Result{
                		Status:      "ok",
                		Task:        task,
                		ProcessedAt: time.Now().UTC(),
                	}
                }
                """
            ).strip()
        if language == "rust":
            return textwrap.dedent(
                """\
                use chrono::{DateTime, Utc};

                pub struct ResultPayload {
                    pub status: String,
                    pub task: String,
                    pub processed_at: DateTime<Utc>,
                }

                pub fn execute_task(task: &str) -> ResultPayload {
                    ResultPayload {
                        status: "ok".to_string(),
                        task: task.to_string(),
                        processed_at: Utc::now(),
                    }
                }
                """
            ).strip()
        return textwrap.dedent(
            """\
            from __future__ import annotations

            from datetime import datetime, timezone


            async def execute_task(task: str) -> dict[str, str]:
                if not task.strip():
                    raise ValueError("task must not be empty")
                return {
                    "status": "ok",
                    "task": task,
                    "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
            """
        ).strip()

