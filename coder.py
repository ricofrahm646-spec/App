"""JARVIS coding core for safe Python app generation."""

from __future__ import annotations

import argparse
import json
import re
import textwrap
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from ghost_security import AuditFinding, CodeAuditScanner


AppKind = Literal["cli", "streamlit", "service"]


@dataclass(frozen=True)
class AppSpec:
    name: str
    description: str
    kind: AppKind = "cli"
    owner: str = "Sir"
    features: tuple[str, ...] = ()


@dataclass(frozen=True)
class GeneratedApp:
    path: str
    files: tuple[str, ...]
    audit_findings: tuple[AuditFinding, ...]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class JarvisCoder:
    """Generates small, reviewable Python apps under apps/.

    The generator uses deterministic templates and immediately runs a static
    security audit. It will not create code that requests credential theft,
    malware behavior, stealth bypassing, or game automation.
    """

    BLOCKED_TERMS = {
        "malware",
        "ransomware",
        "credential theft",
        "token stealer",
        "bypass anticheat",
        "undetected cheat",
        "keylogger",
        "phishing",
        "botnet",
    }

    def __init__(self, apps_dir: Path = Path("apps")) -> None:
        self.apps_dir = apps_dir
        self.apps_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, spec: AppSpec) -> GeneratedApp:
        self._validate_spec(spec)
        app_dir = self.apps_dir / self._slug(spec.name)
        app_dir.mkdir(parents=True, exist_ok=True)
        files = {
            "README.md": self._readme(spec),
            "app.py": self._app_code(spec),
            "config.json": json.dumps({"name": spec.name, "kind": spec.kind, "features": spec.features}, indent=2),
        }
        written: list[str] = []
        for relative, content in files.items():
            path = app_dir / relative
            path.write_text(content, encoding="utf-8")
            written.append(str(path))
        findings = tuple(CodeAuditScanner(app_dir).scan())
        manifest = GeneratedApp(str(app_dir), tuple(written), findings)
        (app_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "path": manifest.path,
                    "files": manifest.files,
                    "audit_findings": [asdict(item) for item in manifest.audit_findings],
                    "created_at": manifest.created_at,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return manifest

    def _validate_spec(self, spec: AppSpec) -> None:
        combined = " ".join([spec.name, spec.description, *spec.features]).lower()
        if any(term in combined for term in self.BLOCKED_TERMS):
            raise ValueError("Requested app behavior violates the JARVIS safety contract.")
        if spec.kind not in {"cli", "streamlit", "service"}:
            raise ValueError(f"Unsupported app kind: {spec.kind}")
        if not spec.name.strip():
            raise ValueError("App name is required.")

    def _readme(self, spec: AppSpec) -> str:
        features = "\n".join(f"- {feature}" for feature in spec.features) or "- Generated baseline workflow"
        return textwrap.dedent(
            f"""\
            # {spec.name}

            {spec.description}

            ## Features
            {features}

            ## Run

            ```bash
            python app.py
            ```
            """
        )

    def _app_code(self, spec: AppSpec) -> str:
        safe_name = self._identifier(spec.name)
        if spec.kind == "streamlit":
            return self._streamlit_template(spec, safe_name)
        if spec.kind == "service":
            return self._service_template(spec, safe_name)
        return self._cli_template(spec, safe_name)

    def _cli_template(self, spec: AppSpec, safe_name: str) -> str:
        return textwrap.dedent(
            f'''\
            """Generated JARVIS CLI app: {spec.name}."""

            from __future__ import annotations

            import argparse
            import json
            from datetime import datetime, timezone


            def run(message: str) -> dict[str, str]:
                return {{
                    "app": "{spec.name}",
                    "owner": "{spec.owner}",
                    "message": message,
                    "status": "operational",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }}


            def main() -> int:
                parser = argparse.ArgumentParser(description="{spec.description}")
                parser.add_argument("--message", default="Systems nominal, Sir.")
                args = parser.parse_args()
                print(json.dumps(run(args.message), indent=2))
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
            '''
        )

    def _streamlit_template(self, spec: AppSpec, safe_name: str) -> str:
        return textwrap.dedent(
            f'''\
            """Generated JARVIS Streamlit app: {spec.name}."""

            from __future__ import annotations

            from datetime import datetime, timezone

            import streamlit as st


            def main() -> None:
                st.set_page_config(page_title="{spec.name}", page_icon="J", layout="wide")
                st.title("{spec.name}")
                st.caption("{spec.description}")
                st.success("Operational, Sir.")
                st.json({{"app": "{safe_name}", "timestamp": datetime.now(timezone.utc).isoformat()}})


            if __name__ == "__main__":
                main()
            '''
        )

    def _service_template(self, spec: AppSpec, safe_name: str) -> str:
        return textwrap.dedent(
            f'''\
            """Generated JARVIS FastAPI service: {spec.name}."""

            from __future__ import annotations

            from datetime import datetime, timezone

            from fastapi import FastAPI

            app = FastAPI(title="{spec.name}", description="{spec.description}")


            @app.get("/health")
            def health() -> dict[str, str]:
                return {{"app": "{safe_name}", "status": "operational", "sir": "online"}}


            @app.get("/status")
            def status() -> dict[str, str]:
                return {{"timestamp": datetime.now(timezone.utc).isoformat(), "message": "Ready, Sir."}}
            '''
        )

    @staticmethod
    def _slug(name: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip().lower()).strip("-")
        return slug or "jarvis-app"

    @staticmethod
    def _identifier(name: str) -> str:
        ident = re.sub(r"\W+", "_", name.strip().lower()).strip("_")
        if not ident or ident[0].isdigit():
            ident = f"app_{ident}"
        return ident


def parse_spec(path: Path | None, args: argparse.Namespace) -> AppSpec:
    if path:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return AppSpec(
            name=str(payload["name"]),
            description=str(payload.get("description", "")),
            kind=payload.get("kind", "cli"),
            features=tuple(str(item) for item in payload.get("features", [])),
        )
    return AppSpec(args.name, args.description, args.kind, features=tuple(args.feature or ()))


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS deterministic Python app generator")
    parser.add_argument("--spec", type=Path, help="JSON spec file")
    parser.add_argument("--name", default="Jarvis Generated App")
    parser.add_argument("--description", default="A generated Python application.")
    parser.add_argument("--kind", choices=["cli", "streamlit", "service"], default="cli")
    parser.add_argument("--feature", action="append")
    args = parser.parse_args()

    manifest = JarvisCoder().generate(parse_spec(args.spec, args))
    print(json.dumps({"path": manifest.path, "files": manifest.files, "findings": len(manifest.audit_findings)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
