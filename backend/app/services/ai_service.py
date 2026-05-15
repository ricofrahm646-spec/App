"""
AI Service - wraps OpenAI / Anthropic APIs for trading bot generation and chat.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Optional provider imports
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    openai = None  # type: ignore
    OPENAI_AVAILABLE = False

try:
    import anthropic as anthropic_sdk
    ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic_sdk = None  # type: ignore
    ANTHROPIC_AVAILABLE = False


SYSTEM_PROMPT = """You are JARVIS, an expert AI trading assistant specializing in MetaTrader 5 (MT5),
MQL5 programming, Pine Script, algorithmic trading strategies, and quantitative finance.
You generate production-ready, well-commented code for EAs, indicators, and Python strategies.
Always prioritize risk management, clear documentation, and robustness."""


class AIService:
    """Handles all AI/LLM interactions."""

    generated_files_dir = Path(settings.GENERATED_FILES_DIR)

    @classmethod
    def _ensure_dir(cls) -> None:
        cls.generated_files_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------------- #
    # Chat                                                                    #
    # --------------------------------------------------------------------- #

    @classmethod
    async def chat_stream(
        cls,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat tokens from the configured LLM."""
        history = history or []
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in history:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": message})

        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            async for token in cls._openai_stream(messages):
                yield token
        elif ANTHROPIC_AVAILABLE and settings.ANTHROPIC_API_KEY:
            async for token in cls._anthropic_stream(messages):
                yield token
        else:
            # Fallback mock response
            mock = f"[JARVIS Mock] Received: '{message}'. Configure OPENAI_API_KEY or ANTHROPIC_API_KEY for real AI responses."
            for word in mock.split():
                yield word + " "

    @classmethod
    async def _openai_stream(cls, messages: List[Dict]) -> AsyncGenerator[str, None]:
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        async with client.chat.completions.stream(
            model=settings.DEFAULT_AI_MODEL,
            messages=messages,
            max_tokens=settings.AI_MAX_TOKENS,
            temperature=settings.AI_TEMPERATURE,
        ) as stream:
            async for event in stream:
                if event.choices and event.choices[0].delta.content:
                    yield event.choices[0].delta.content

    @classmethod
    async def _anthropic_stream(cls, messages: List[Dict]) -> AsyncGenerator[str, None]:
        client = anthropic_sdk.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        # Extract system message
        system_content = next((m["content"] for m in messages if m["role"] == "system"), SYSTEM_PROMPT)
        user_messages = [m for m in messages if m["role"] != "system"]
        async with client.messages.stream(
            model="claude-opus-4-5",
            max_tokens=settings.AI_MAX_TOKENS,
            system=system_content,
            messages=user_messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    @classmethod
    async def chat_complete(cls, message: str, history: Optional[List[Dict]] = None) -> str:
        """Non-streaming chat completion."""
        full = ""
        async for token in cls.chat_stream(message, history):
            full += token
        return full

    # --------------------------------------------------------------------- #
    # Code generation                                                          #
    # --------------------------------------------------------------------- #

    @classmethod
    async def generate_mql5_ea(
        cls,
        name: str,
        strategy_type: str,
        symbols: List[str],
        timeframes: List[str],
        description: str,
        extra_params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        prompt = cls._ea_prompt(name, strategy_type, symbols, timeframes, description, extra_params or {})
        code = await cls.chat_complete(prompt)
        filename = f"{name.replace(' ', '_')}.mq5"
        file_path = cls._save_generated_file(filename, code, "mql5/experts")
        return {
            "filename": filename,
            "path": str(file_path),
            "code": code,
            "type": "EA",
            "strategy_type": strategy_type,
            "created_at": datetime.utcnow().isoformat(),
        }

    @classmethod
    async def generate_mql5_indicator(
        cls,
        name: str,
        description: str,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        prompt = cls._indicator_prompt(name, description, symbols or [], timeframes or [])
        code = await cls.chat_complete(prompt)
        filename = f"{name.replace(' ', '_')}.mq5"
        file_path = cls._save_generated_file(filename, code, "mql5/indicators")
        return {
            "filename": filename,
            "path": str(file_path),
            "code": code,
            "type": "Indicator",
            "created_at": datetime.utcnow().isoformat(),
        }

    @classmethod
    async def generate_python_strategy(
        cls,
        name: str,
        strategy_type: str,
        description: str,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        prompt = cls._python_strategy_prompt(name, strategy_type, description, symbols or [], timeframes or [])
        code = await cls.chat_complete(prompt)
        filename = f"{name.replace(' ', '_')}.py"
        file_path = cls._save_generated_file(filename, code, "python/strategies")
        return {
            "filename": filename,
            "path": str(file_path),
            "code": code,
            "type": "Python Strategy",
            "strategy_type": strategy_type,
            "created_at": datetime.utcnow().isoformat(),
        }

    @classmethod
    async def generate_pinescript(
        cls,
        name: str,
        description: str,
        strategy_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        prompt = (
            f"Generate a complete Pine Script v5 indicator/strategy called '{name}'.\n"
            f"Description: {description}\n"
            f"Strategy type: {strategy_type or 'custom'}\n"
            "Include proper inputs, alerts, and plotting. Return only the Pine Script code."
        )
        code = await cls.chat_complete(prompt)
        filename = f"{name.replace(' ', '_')}.pine"
        file_path = cls._save_generated_file(filename, code, "pinescript")
        return {
            "filename": filename,
            "path": str(file_path),
            "code": code,
            "type": "PineScript",
            "created_at": datetime.utcnow().isoformat(),
        }

    @classmethod
    async def analyze_strategy(cls, code: str, language: str = "auto") -> Dict[str, Any]:
        prompt = (
            f"Analyze this {language} trading strategy code. "
            "Identify: 1) Logic and rules, 2) Strengths, 3) Weaknesses/risks, "
            "4) Suggested improvements, 5) Risk management assessment.\n\n"
            f"```\n{code}\n```"
        )
        analysis = await cls.chat_complete(prompt)
        return {
            "analysis": analysis,
            "language": language,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

    @classmethod
    async def optimize_strategy(cls, strategy_id: int, code: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            f"Optimize this trading strategy (ID: {strategy_id}) based on these performance metrics:\n"
            f"{json.dumps(metrics, indent=2)}\n\n"
            f"Current code:\n```\n{code}\n```\n\n"
            "Provide: 1) Optimized parameter ranges, 2) Improved logic, 3) Better risk management, "
            "4) Full optimized code."
        )
        result = await cls.chat_complete(prompt)
        return {
            "strategy_id": strategy_id,
            "optimization": result,
            "optimized_at": datetime.utcnow().isoformat(),
        }

    # --------------------------------------------------------------------- #
    # File management                                                          #
    # --------------------------------------------------------------------- #

    @classmethod
    def list_generated_files(cls) -> List[Dict[str, Any]]:
        cls._ensure_dir()
        files = []
        for f in cls.generated_files_dir.rglob("*"):
            if f.is_file():
                stat = f.stat()
                files.append({
                    "name": f.name,
                    "path": str(f.relative_to(cls.generated_files_dir)),
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": cls._detect_file_type(f),
                })
        return files

    @classmethod
    def read_generated_file(cls, relative_path: str) -> str:
        cls._ensure_dir()
        file_path = cls.generated_files_dir / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return file_path.read_text(encoding="utf-8")

    @classmethod
    def delete_generated_file(cls, relative_path: str) -> bool:
        cls._ensure_dir()
        file_path = cls.generated_files_dir / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        file_path.unlink()
        return True

    @classmethod
    def install_to_mt5(cls, relative_path: str) -> Dict[str, Any]:
        """Copy generated MQL5 file to MT5 Experts/Indicators folder."""
        cls._ensure_dir()
        file_path = cls.generated_files_dir / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")

        if relative_path.startswith("mql5/experts") or file_path.suffix == ".mq5":
            dest_dir = Path(settings.MT5_EXPERTS_PATH)
        else:
            dest_dir = Path(settings.MT5_INDICATORS_PATH)

        if not dest_dir.exists():
            return {
                "success": False,
                "message": f"MT5 path not found: {dest_dir}. Set MT5_EXPERTS_PATH/MT5_INDICATORS_PATH.",
                "source": str(file_path),
                "destination": str(dest_dir / file_path.name),
            }

        import shutil
        dest = dest_dir / file_path.name
        shutil.copy2(file_path, dest)
        return {
            "success": True,
            "message": f"Installed to {dest}",
            "source": str(file_path),
            "destination": str(dest),
        }

    # --------------------------------------------------------------------- #
    # Private helpers                                                          #
    # --------------------------------------------------------------------- #

    @classmethod
    def _save_generated_file(cls, filename: str, content: str, subdir: str = "") -> Path:
        cls._ensure_dir()
        target_dir = cls.generated_files_dir / subdir if subdir else cls.generated_files_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path

    @staticmethod
    def _detect_file_type(path: Path) -> str:
        ext = path.suffix.lower()
        mapping = {".mq5": "MQL5", ".mq4": "MQL4", ".pine": "PineScript", ".py": "Python"}
        return mapping.get(ext, "unknown")

    @staticmethod
    def _ea_prompt(
        name: str,
        strategy_type: str,
        symbols: List[str],
        timeframes: List[str],
        description: str,
        extra: Dict,
    ) -> str:
        return (
            f"Generate a complete, production-ready MQL5 Expert Advisor named '{name}'.\n"
            f"Strategy type: {strategy_type}\n"
            f"Target symbols: {', '.join(symbols)}\n"
            f"Timeframes: {', '.join(timeframes)}\n"
            f"Description: {description}\n"
            f"Extra parameters: {json.dumps(extra)}\n\n"
            "Requirements:\n"
            "- Full MQL5 code with OnInit, OnDeinit, OnTick, OnTradeTransaction\n"
            "- Configurable inputs for risk%, SL, TP, lot size\n"
            "- Built-in risk management with max daily loss and drawdown protection\n"
            "- Trailing stop functionality\n"
            "- Magic number for trade identification\n"
            "- Comprehensive comments explaining logic\n"
            "- Error handling for all MT5 API calls\n"
            "Return ONLY the MQL5 code, no markdown fences."
        )

    @staticmethod
    def _indicator_prompt(name: str, description: str, symbols: List[str], timeframes: List[str]) -> str:
        return (
            f"Generate a complete MQL5 custom indicator named '{name}'.\n"
            f"Description: {description}\n"
            f"Target symbols: {', '.join(symbols) if symbols else 'Any'}\n"
            f"Timeframes: {', '.join(timeframes) if timeframes else 'Any'}\n\n"
            "Requirements:\n"
            "- Full MQL5 indicator code with OnInit, OnCalculate\n"
            "- Configurable input parameters\n"
            "- Proper buffer declarations and plotting\n"
            "- Alert functionality\n"
            "Return ONLY the MQL5 code, no markdown fences."
        )

    @staticmethod
    def _python_strategy_prompt(
        name: str, strategy_type: str, description: str, symbols: List[str], timeframes: List[str]
    ) -> str:
        return (
            f"Generate a complete Python trading strategy class named '{name}'.\n"
            f"Strategy type: {strategy_type}\n"
            f"Description: {description}\n"
            f"Symbols: {', '.join(symbols) if symbols else 'configurable'}\n"
            f"Timeframes: {', '.join(timeframes) if timeframes else 'configurable'}\n\n"
            "Requirements:\n"
            "- Class-based with __init__, generate_signals, calculate_position_size, execute methods\n"
            "- Integration with MT5Service\n"
            "- Pandas for data manipulation, numpy for calculations\n"
            "- Risk management with configurable parameters\n"
            "- Logging throughout\n"
            "- Type hints and docstrings\n"
            "Return ONLY Python code, no markdown fences."
        )
