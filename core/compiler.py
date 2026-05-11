"""
JARVIS Architect Engine.

Transforms natural-language requests into concrete project structures and writes
them into a controlled workspace. It supports trading bots, Streamlit web apps,
defensive security utilities, scripts, and documentation packs.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal

from ghost_security import AuditFinding, SecurityAuditor


ProjectKind = Literal["trading_bot", "web_app", "defensive_security", "script", "documentation"]

SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]+")
TRADING_TERMS = {"trading", "trade", "bot", "scalp", "mt5", "metatrader", "smc", "forex", "crypto"}
WEB_TERMS = {"streamlit", "dashboard", "web", "app", "ui", "frontend", "website"}
SECURITY_TERMS = {"security", "audit", "scanner", "hacking", "pentest", "vulnerability", "forensic"}
DOC_TERMS = {"documentation", "readme", "manual", "docs", "guide", "strategy"}


@dataclass(frozen=True)
class FileArtifact:
    path: str
    content: str
    executable: bool = False


@dataclass(frozen=True)
class ProjectBlueprint:
    name: str
    kind: ProjectKind
    summary: str
    files: tuple[FileArtifact, ...]
    commands: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def manifest(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "summary": self.summary,
            "files": [artifact.path for artifact in self.files],
            "commands": list(self.commands),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class BuildResult:
    root: Path
    blueprint: ProjectBlueprint
    written_files: tuple[Path, ...]
    audit_findings: tuple[AuditFinding, ...]
    manifest_path: Path


class ArchitectCompiler:
    """Natural-language to filesystem project compiler."""

    def __init__(self, workspace_root: str | Path = ".", projects_dir: str = "generated_projects") -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.projects_dir = projects_dir

    def compile_request(
        self,
        prompt: str,
        source_text: str = "",
        attachments: Iterable[str | Path] = (),
        execute: bool = False,
    ) -> BuildResult:
        blueprint = self.plan(prompt=prompt, source_text=source_text, attachments=attachments)
        result = self.materialize(blueprint)
        if execute:
            self._write_execution_plan(result)
        return result

    def plan(
        self,
        prompt: str,
        source_text: str = "",
        attachments: Iterable[str | Path] = (),
    ) -> ProjectBlueprint:
        clean_prompt = " ".join(prompt.split())
        kind = self._classify(clean_prompt, source_text)
        name = self._project_name(clean_prompt, kind)
        context = self._context_block(clean_prompt, source_text, attachments)
        if kind == "trading_bot":
            files, commands = self._trading_project(name, context)
        elif kind == "web_app":
            files, commands = self._web_project(name, context)
        elif kind == "defensive_security":
            files, commands = self._security_project(name, context)
        elif kind == "documentation":
            files, commands = self._documentation_project(name, context)
        else:
            files, commands = self._script_project(name, context)
        return ProjectBlueprint(
            name=name,
            kind=kind,
            summary=f"Generated from operator request: {clean_prompt[:220]}",
            files=tuple(files),
            commands=tuple(commands),
        )

    def materialize(self, blueprint: ProjectBlueprint) -> BuildResult:
        project_root = self._safe_join(self.workspace_root, self.projects_dir, blueprint.name)
        project_root.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for artifact in blueprint.files:
            target = self._safe_join(project_root, artifact.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.suffix == ".py":
                ast.parse(artifact.content, filename=str(target))
            target.write_text(artifact.content, encoding="utf-8")
            if artifact.executable:
                target.chmod(target.stat().st_mode | 0o111)
            written.append(target)

        manifest_path = project_root / "jarvis_manifest.json"
        manifest_path.write_text(json.dumps(blueprint.manifest(), indent=2), encoding="utf-8")
        written.append(manifest_path)
        findings = tuple(SecurityAuditor([project_root]).scan())
        return BuildResult(
            root=project_root,
            blueprint=blueprint,
            written_files=tuple(written),
            audit_findings=findings,
            manifest_path=manifest_path,
        )

    def _classify(self, prompt: str, source_text: str) -> ProjectKind:
        words = set(re.findall(r"[a-zA-Z0-9_]+", f"{prompt} {source_text}".lower()))
        if words & TRADING_TERMS:
            return "trading_bot"
        if words & SECURITY_TERMS:
            return "defensive_security"
        if words & WEB_TERMS:
            return "web_app"
        if words & DOC_TERMS:
            return "documentation"
        return "script"

    def _project_name(self, prompt: str, kind: ProjectKind) -> str:
        words = re.findall(r"[a-zA-Z0-9]+", prompt.lower())
        meaningful = [word for word in words if word not in {"jarvis", "build", "make", "create", "mir", "eine", "app"}]
        base = "_".join(meaningful[:7]) or kind
        safe = SAFE_NAME.sub("_", base).strip("_")[:70] or kind
        return f"{kind}_{safe}"

    def _context_block(self, prompt: str, source_text: str, attachments: Iterable[str | Path]) -> str:
        attachment_lines = [f"- {Path(item)}" for item in attachments]
        attachment_block = "\n".join(attachment_lines) if attachment_lines else "- none"
        strategy = source_text.strip()[:4_000] if source_text else "No external source text was provided."
        return f"Operator request:\n{prompt}\n\nParsed source context:\n{strategy}\n\nAttachments:\n{attachment_block}\n"

    def _trading_project(self, name: str, context: str) -> tuple[list[FileArtifact], list[str]]:
        files = [
            FileArtifact(
                "README.md",
                f"""# {name}

Generated trading module.

## Context

```text
{context}
```

Live trading is disabled unless `JARVIS_LIVE_TRADING=1` is explicitly set.
Use a demo account first and verify broker constraints, spreads, and news risk.
""",
            ),
            FileArtifact(
                "strategy.py",
                '''from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyDecision:
    action: str
    confidence: float
    reason: str


def decide(snapshot: dict) -> StrategyDecision:
    status = snapshot.get("status", "idle")
    signal = snapshot.get("signal")
    if signal is None:
        return StrategyDecision("wait", 0.0, f"No signal: {snapshot.get('reason', status)}")
    confluence = float(getattr(signal, "confluence", 0.0))
    if confluence >= 0.90:
        return StrategyDecision(getattr(signal, "side", "wait"), confluence, "SMC confluence threshold passed")
    return StrategyDecision("wait", confluence, "Confluence below 90%")
''',
            ),
            FileArtifact(
                "run.py",
                '''from __future__ import annotations

from trader.scalper import AggressiveScalingScalper
from strategy import decide


def main() -> None:
    scalper = AggressiveScalingScalper()
    snapshot = scalper.scan_once()
    decision = decide(snapshot)
    print({"snapshot": snapshot, "decision": decision})


if __name__ == "__main__":
    main()
''',
            ),
            FileArtifact("requirements.txt", "MetaTrader5\npandas\n"),
        ]
        return files, ["python run.py"]

    def _web_project(self, name: str, context: str) -> tuple[list[FileArtifact], list[str]]:
        files = [
            FileArtifact(
                "README.md",
                f"# {name}\n\nGenerated Streamlit app.\n\n```text\n{context}\n```\n",
            ),
            FileArtifact(
                "app.py",
                f'''from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st


def main() -> None:
    st.set_page_config(page_title={name!r}, layout="wide")
    st.title({name!r})
    st.caption("Created by JARVIS Universal Creator Core")
    st.write({context[:900]!r})
    st.metric("Generated at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    st.info("Extend this module by asking: Jarvis, erweitere dich um Modul X")


if __name__ == "__main__":
    main()
''',
            ),
            FileArtifact("requirements.txt", "streamlit\n"),
        ]
        return files, ["streamlit run app.py"]

    def _security_project(self, name: str, context: str) -> tuple[list[FileArtifact], list[str]]:
        files = [
            FileArtifact(
                "README.md",
                f"""# {name}

Generated defensive security utility.

This project is limited to owned-code auditing and local defensive checks. It
does not include credential theft, persistence, exploitation, evasion, or
unauthorized access behavior.

```text
{context}
```
""",
            ),
            FileArtifact(
                "scanner.py",
                '''from __future__ import annotations

from pathlib import Path

from ghost_security import SecurityAuditor


def main() -> None:
    root = Path.cwd()
    findings = SecurityAuditor([root]).scan()
    if not findings:
        print("No findings.")
        return
    for finding in findings:
        print(f"{finding.severity.upper()} {finding.path}:{finding.line} {finding.rule} - {finding.message}")


if __name__ == "__main__":
    main()
''',
            ),
        ]
        return files, ["python scanner.py"]

    def _documentation_project(self, name: str, context: str) -> tuple[list[FileArtifact], list[str]]:
        files = [
            FileArtifact(
                "README.md",
                f"""# {name}

## Executive Summary

Generated documentation pack from operator-provided context.

## Source Context

```text
{context}
```

## Next Commands

- `Jarvis, baue mir eine App fuer diese Strategie`
- `Jarvis, erstelle Tests fuer dieses Modul`
- `Jarvis, erweitere dich um Modul X`
""",
            )
        ]
        return files, []

    def _script_project(self, name: str, context: str) -> tuple[list[FileArtifact], list[str]]:
        files = [
            FileArtifact("README.md", f"# {name}\n\nGenerated Python script.\n\n```text\n{context}\n```\n"),
            FileArtifact(
                "main.py",
                f'''from __future__ import annotations


def main() -> None:
    print("JARVIS generated script online.")
    print({context[:1_000]!r})


if __name__ == "__main__":
    main()
''',
            ),
        ]
        return files, ["python main.py"]

    def _write_execution_plan(self, result: BuildResult) -> None:
        plan = {
            "note": "Execution was requested. Commands are recorded for operator review.",
            "commands": result.blueprint.commands,
        }
        (result.root / "execution_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")

    @staticmethod
    def _safe_join(root: Path, *parts: str) -> Path:
        target = root.joinpath(*parts).resolve()
        if root not in (target, *target.parents):
            raise ValueError(f"Refusing to write outside workspace root: {target}")
        return target
