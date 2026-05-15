"""
AI Service for JARVIS AI Trading OS.

Handles all LLM interactions: streaming chat, MQL5/Python code generation,
strategy analysis, optimisation, indicator creation, error fixing, and
intent-based file planning.

Supports OpenAI (primary) and Anthropic (fallback).
"""
import json
import os
import re
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from loguru import logger

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

try:
    from app.core.config import settings as _app_settings
except ImportError:
    _app_settings = None  # type: ignore


def _get_setting(key: str, default: str = "") -> str:
    """Retrieve a config value from app settings or environment."""
    if _app_settings and hasattr(_app_settings, key):
        return getattr(_app_settings, key) or os.getenv(key, default)
    return os.getenv(key, default)


# ---------------------------------------------------------------------------
SYSTEM_PROMPT = textwrap.dedent(
    """\
    You are JARVIS, an elite AI trading system built to assist professional traders and
    quantitative developers. Your primary responsibilities are:

    1. BUILD complete, production-ready trading bots (MQL5 Expert Advisors, Python strategies).
    2. DESIGN robust risk management logic with strict drawdown controls.
    3. ANALYZE strategy performance and suggest data-driven optimisations.
    4. GENERATE Pine Script v5 indicators and strategies for TradingView.
    5. DEBUG and fix MQL5 / Python trading code precisely.

    Rules you must always follow:
    - All code you produce is syntactically correct and runnable as-is.
    - Include proper error handling and logging in every function.
    - Apply 2% max risk-per-trade and 20% max drawdown as defaults unless overridden.
    - Never expose API keys or credentials in generated code.
    - Think step by step before writing code. Correctness > brevity.
    """
)
# ---------------------------------------------------------------------------


class AIService:
    """
    Handles all AI / LLM interactions for JARVIS.

    Automatically selects OpenAI → Anthropic → mock fallback based on
    which credentials are configured.
    """

    def __init__(self) -> None:
        self._openai_key: str = _get_setting("OPENAI_API_KEY")
        self._anthropic_key: str = _get_setting("ANTHROPIC_API_KEY")
        self._model: str = _get_setting("DEFAULT_AI_MODEL", "gpt-4o")
        self._max_tokens: int = int(_get_setting("AI_MAX_TOKENS", "4096"))
        self._temperature: float = float(_get_setting("AI_TEMPERATURE", "0.3"))

        self._generated_dir = Path(
            _get_setting("GENERATED_FILES_DIR", "/workspace/generated")
        )
        self._generated_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal provider helpers
    # ------------------------------------------------------------------

    def _openai_client(self):
        if not OPENAI_AVAILABLE or not self._openai_key:
            return None
        return openai.AsyncOpenAI(api_key=self._openai_key)

    def _anthropic_client(self):
        if not ANTHROPIC_AVAILABLE or not self._anthropic_key:
            return None
        return anthropic_sdk.AsyncAnthropic(api_key=self._anthropic_key)

    def _build_messages(
        self, user_message: str, history: List[Dict], system: str = SYSTEM_PROMPT
    ) -> List[Dict]:
        messages = [{"role": "system", "content": system}]
        for entry in history:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})
        return messages

    async def _complete(
        self, messages: List[Dict], temperature: Optional[float] = None
    ) -> str:
        """Non-streaming completion with provider fallback."""
        temp = temperature if temperature is not None else self._temperature
        client = self._openai_client()

        if client:
            resp = await client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temp,
                max_tokens=self._max_tokens,
            )
            return resp.choices[0].message.content.strip()

        anthropic_client = self._anthropic_client()
        if anthropic_client:
            system_content = next(
                (m["content"] for m in messages if m["role"] == "system"), SYSTEM_PROMPT
            )
            user_messages = [m for m in messages if m["role"] != "system"]
            resp = await anthropic_client.messages.create(
                model="claude-opus-4-5",
                max_tokens=self._max_tokens,
                system=system_content,
                messages=user_messages,
            )
            return resp.content[0].text.strip()

        # Mock fallback
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        return (
            f"[JARVIS Mock] Received: '{last_user[:80]}...'. "
            "Configure OPENAI_API_KEY or ANTHROPIC_API_KEY for real AI responses."
        )

    @staticmethod
    def _strip_fences(code: str) -> str:
        """Remove markdown code fences from a code block."""
        code = re.sub(r"^```[\w]*\n?", "", code.strip(), flags=re.IGNORECASE)
        code = re.sub(r"\n?```$", "", code)
        return code.strip()

    @staticmethod
    def _extract_json_object(text: str) -> Optional[str]:
        m = re.search(r"\{[\s\S]+\}", text)
        return m.group() if m else None

    @staticmethod
    def _extract_json_array(text: str) -> Optional[str]:
        m = re.search(r"\[[\s\S]+\]", text)
        return m.group() if m else None

    # ------------------------------------------------------------------
    # Chat (streaming)
    # ------------------------------------------------------------------

    async def chat(
        self, message: str, history: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """
        Stream an AI response token-by-token.

        Args:
            message: The current user message.
            history: Prior conversation turns as [{role, content}] dicts.

        Yields successive string chunks as they arrive from the model.
        """
        messages = self._build_messages(message, history)
        client = self._openai_client()

        if client:
            stream = await client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
            return

        anthropic_client = self._anthropic_client()
        if anthropic_client:
            system_content = next(
                (m["content"] for m in messages if m["role"] == "system"), SYSTEM_PROMPT
            )
            user_messages = [m for m in messages if m["role"] != "system"]
            async with anthropic_client.messages.stream(
                model="claude-opus-4-5",
                max_tokens=self._max_tokens,
                system=system_content,
                messages=user_messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
            return

        # Mock streaming fallback
        mock = (
            f"[JARVIS Mock] I received your message: '{message[:60]}...'. "
            "Please configure OPENAI_API_KEY or ANTHROPIC_API_KEY."
        )
        for word in mock.split():
            yield word + " "

    # ------------------------------------------------------------------
    # MQL5 EA generation
    # ------------------------------------------------------------------

    async def generate_mql5_bot(self, params: Dict) -> str:
        """
        Generate a complete MQL5 Expert Advisor based on *params*.

        Params keys:
            name, strategy_type, symbols, timeframes, indicators,
            risk_params {risk_percent, max_sl_pips, max_tp_pips, magic_number},
            extra_instructions.

        Returns raw MQL5 source code (no markdown fences).
        """
        name          = params.get("name", "JARVISBot")
        strategy_type = params.get("strategy_type", "trend-following")
        symbols       = params.get("symbols", ["EURUSD"])
        timeframes    = params.get("timeframes", ["H1"])
        indicators    = params.get("indicators", ["EMA(20)", "EMA(50)", "RSI(14)"])
        risk          = params.get("risk_params", {})
        risk_pct      = risk.get("risk_percent", 2.0)
        max_sl        = risk.get("max_sl_pips", 50)
        max_tp        = risk.get("max_tp_pips", 100)
        magic         = risk.get("magic_number", 20240101)
        extra         = params.get("extra_instructions", "")

        prompt = textwrap.dedent(
            f"""\
            Generate a complete, production-ready MQL5 Expert Advisor (.mq5) file:

            EA Name:         {name}
            Strategy Type:   {strategy_type}
            Symbols:         {', '.join(symbols)}
            Timeframes:      {', '.join(timeframes)}
            Indicators:      {', '.join(indicators)}
            Risk Per Trade:  {risk_pct}%
            Max Stop-Loss:   {max_sl} pips
            Max Take-Profit: {max_tp} pips
            Magic Number:    {magic}
            Extra:           {extra or 'None'}

            Requirements:
            - Full #property metadata (copyright, version, description).
            - All input parameters declared as `input` variables.
            - Complete OnInit(), OnDeinit(), OnTick() handlers.
            - Proper lot-size calculation based on account balance and {risk_pct}% risk.
            - SL must never exceed {max_sl} pips.
            - Only 1 open trade at a time.
            - Close all trades when drawdown exceeds 20%.
            - Detailed inline comments explaining each logic block.
            - Output ONLY the raw .mq5 file content. No markdown fences.
            """
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]
        code = await self._complete(messages, temperature=0.2)
        code = self._strip_fences(code)
        logger.info(f"Generated MQL5 EA '{name}' ({len(code)} chars)")

        filename = f"{name.replace(' ', '_')}.mq5"
        dest = self._generated_dir / "mql5" / "experts" / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code, encoding="utf-8")
        return code

    # ------------------------------------------------------------------
    # Python strategy generation
    # ------------------------------------------------------------------

    async def generate_python_strategy(self, params: Dict) -> str:
        """
        Generate a complete Python trading strategy class.

        Params keys: name, strategy_type, symbols, timeframe, indicators,
                     risk_params, extra_instructions.

        Returns raw Python source code.
        """
        name          = params.get("name", "JARVISStrategy")
        strategy_type = params.get("strategy_type", "trend-following")
        symbols       = params.get("symbols", ["EURUSD"])
        timeframe     = params.get("timeframe", "H1")
        indicators    = params.get("indicators", ["EMA(20)", "EMA(50)"])
        risk          = params.get("risk_params", {})
        risk_pct      = risk.get("risk_percent", 2.0)
        extra         = params.get("extra_instructions", "")

        prompt = textwrap.dedent(
            f"""\
            Generate a complete Python trading strategy class:

            Class Name:    {name}
            Strategy Type: {strategy_type}
            Symbols:       {', '.join(symbols)}
            Timeframe:     {timeframe}
            Indicators:    {', '.join(indicators)}
            Risk/Trade:    {risk_pct}%
            Extra:         {extra or 'None'}

            Requirements:
            - Use pandas and numpy.
            - Methods: __init__, generate_signals(df) -> df,
              calculate_position_size(balance, risk_pct, sl_distance) -> float,
              run_backtest(data: pd.DataFrame) -> Dict.
            - generate_signals: add 'signal' (1=BUY, -1=SELL, 0=neutral), 'sl', 'tp'.
            - run_backtest: return total_return, sharpe_ratio, max_drawdown,
              win_rate, profit_factor.
            - Full docstrings and type hints.
            - Output ONLY raw Python code. No markdown fences.
            """
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]
        code = await self._complete(messages, temperature=0.2)
        code = self._strip_fences(code)
        logger.info(f"Generated Python strategy '{name}' ({len(code)} chars)")

        filename = f"{name.replace(' ', '_')}.py"
        dest = self._generated_dir / "python" / "strategies" / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code, encoding="utf-8")
        return code

    # ------------------------------------------------------------------
    # Strategy analysis
    # ------------------------------------------------------------------

    async def analyze_strategy(self, strategy_code: str) -> Dict:
        """
        Analyse a Python or MQL5 strategy and return structured feedback.

        Returns:
            {summary, strengths, weaknesses, suggestions, risk_score, complexity_score}
        """
        prompt = textwrap.dedent(
            f"""\
            Analyse the following trading strategy code and respond with JSON only.

            Schema:
            {{
                "summary": "<one-paragraph>",
                "strengths": ["..."],
                "weaknesses": ["..."],
                "suggestions": ["..."],
                "risk_score": <0-10>,
                "complexity_score": <0-10>
            }}

            Code:
            ```
            {strategy_code[:8000]}
            ```

            Output ONLY valid JSON.
            """
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]
        raw = await self._complete(messages, temperature=0.1)
        json_str = self._extract_json_object(raw)
        if not json_str:
            return {
                "summary": raw, "strengths": [], "weaknesses": [],
                "suggestions": [], "risk_score": 5, "complexity_score": 5,
            }
        return json.loads(json_str)

    # ------------------------------------------------------------------
    # Strategy optimisation
    # ------------------------------------------------------------------

    async def optimize_strategy(self, strategy_id: int, metrics: Dict) -> Dict:
        """
        Suggest optimised parameters based on recent performance metrics.

        metrics keys: win_rate, profit_factor, max_drawdown, sharpe_ratio,
                      avg_trade_duration_hours, total_trades, current_params.

        Returns {optimized_params, expected_improvements, rationale}.
        """
        prompt = textwrap.dedent(
            f"""\
            Strategy (ID: {strategy_id}) recent performance:
            {json.dumps(metrics, indent=2)}

            Suggest optimised parameters to improve Sharpe and Profit Factor
            while reducing Max Drawdown. Respond with JSON only:
            {{
                "optimized_params": {{}},
                "expected_improvements": {{
                    "sharpe_ratio": "...",
                    "profit_factor": "...",
                    "max_drawdown": "..."
                }},
                "rationale": "..."
            }}
            Output ONLY valid JSON.
            """
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]
        raw = await self._complete(messages, temperature=0.2)
        json_str = self._extract_json_object(raw)
        if not json_str:
            return {"optimized_params": {}, "expected_improvements": {}, "rationale": raw}
        return json.loads(json_str)

    # ------------------------------------------------------------------
    # Indicator generation
    # ------------------------------------------------------------------

    async def generate_indicator(self, params: Dict) -> str:
        """
        Generate a complete MQL5 custom indicator.

        Params keys: name, type, calculation, display, buffers,
                     extra_instructions.

        Returns raw MQL5 source code.
        """
        name        = params.get("name", "JARVISIndicator")
        ind_type    = params.get("type", "trend")
        calculation = params.get("calculation", "EMA of close prices")
        display     = params.get("display", "chart")
        buffers     = params.get("buffers", 2)
        extra       = params.get("extra_instructions", "")

        prompt = textwrap.dedent(
            f"""\
            Generate a complete MQL5 custom indicator (.mq5):

            Name:        {name}
            Type:        {ind_type}
            Calculation: {calculation}
            Display:     {display}
            Buffers:     {buffers}
            Extra:       {extra or 'None'}

            Requirements:
            - Full #property metadata including indicator window type.
            - All input parameters as `input` variables.
            - Complete OnInit() with SetIndexBuffer and PlotIndexSetString.
            - Complete OnCalculate() with full computation logic.
            - Error handling and input validation.
            - Output ONLY the raw .mq5 file content. No markdown fences.
            """
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]
        code = await self._complete(messages, temperature=0.2)
        code = self._strip_fences(code)
        logger.info(f"Generated MQL5 indicator '{name}' ({len(code)} chars)")

        filename = f"{name.replace(' ', '_')}.mq5"
        dest = self._generated_dir / "mql5" / "indicators" / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(code, encoding="utf-8")
        return code

    # ------------------------------------------------------------------
    # Code debugging / error fixing
    # ------------------------------------------------------------------

    async def fix_code_errors(self, code: str, error: str) -> str:
        """
        Return a corrected version of the code that resolves the reported error.

        Args:
            code:  The original (broken) source code.
            error: The compiler / runtime error message.

        Returns fixed source code as a plain string (no markdown fences).
        """
        prompt = textwrap.dedent(
            f"""\
            Fix the bug in the following code. The error is:

            ERROR:
            {error}

            CODE:
            ```
            {code[:8000]}
            ```

            Rules:
            - Fix ONLY what is necessary to resolve the error(s).
            - Do not change the logic or structure unless required.
            - Output ONLY the complete fixed code. No markdown fences. No explanation.
            """
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]
        fixed = await self._complete(messages, temperature=0.1)
        fixed = self._strip_fences(fixed)
        logger.info(f"fix_code_errors: {len(code)} → {len(fixed)} chars")
        return fixed

    # ------------------------------------------------------------------
    # Intent → file creation
    # ------------------------------------------------------------------

    async def create_files_from_intent(self, intent: str) -> List[Dict]:
        """
        Parse a natural-language intent and return a list of files to create.

        Each item: {path, content, type}
        where type ∈ {mql5_ea, mql5_indicator, python_strategy,
                      pine_script, config, other}.
        """
        # Step 1: Plan the files
        plan_prompt = textwrap.dedent(
            f"""\
            A user wants to build: "{intent}"

            List all files that need to be created. JSON array only:
            [
                {{
                    "path": "<relative path, e.g. strategies/MyEA.mq5>",
                    "type": "<mql5_ea|mql5_indicator|python_strategy|pine_script|config|other>",
                    "description": "<one line>"
                }}
            ]
            Output ONLY valid JSON.
            """
        )

        plan_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": plan_prompt},
        ]
        plan_raw = await self._complete(plan_messages, temperature=0.2)
        json_str = self._extract_json_array(plan_raw)
        if not json_str:
            logger.error("create_files_from_intent: could not parse file plan.")
            return []

        file_plan: List[Dict] = json.loads(json_str)
        results: List[Dict] = []

        for spec in file_plan:
            path        = spec.get("path", "output/file.txt")
            file_type   = spec.get("type", "other")
            description = spec.get("description", "")

            gen_prompt = textwrap.dedent(
                f"""\
                Generate the complete content for:

                Path:        {path}
                Type:        {file_type}
                Description: {description}
                System:      {intent}

                Output ONLY the raw file content. No markdown fences. No explanation.
                """
            )

            gen_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": gen_prompt},
            ]
            content = await self._complete(gen_messages, temperature=0.2)
            content = self._strip_fences(content)

            dest = self._generated_dir / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

            results.append({"path": path, "content": content, "type": file_type})
            logger.info(f"create_files_from_intent: created {path} ({file_type})")

        return results

    # ------------------------------------------------------------------
    # Legacy / compatibility helpers (used by existing API routes)
    # ------------------------------------------------------------------

    async def chat_stream(
        self, message: str, history: Optional[List[Dict]] = None
    ) -> AsyncGenerator[str, None]:
        """Alias for chat() — kept for backward compatibility."""
        async for token in self.chat(message, history or []):
            yield token

    async def chat_complete(
        self, message: str, history: Optional[List[Dict]] = None
    ) -> str:
        """Non-streaming wrapper over chat()."""
        full = ""
        async for token in self.chat(message, history or []):
            full += token
        return full

    async def generate_mql5_ea(
        self,
        name: str,
        strategy_type: str,
        symbols: List[str],
        timeframes: List[str],
        description: str,
        extra_params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Legacy positional-arg wrapper — delegates to generate_mql5_bot()."""
        params = {
            "name": name,
            "strategy_type": strategy_type,
            "symbols": symbols,
            "timeframes": timeframes,
            "extra_instructions": description,
            "risk_params": extra_params or {},
        }
        code = await self.generate_mql5_bot(params)
        filename = f"{name.replace(' ', '_')}.mq5"
        path = self._generated_dir / "mql5" / "experts" / filename
        return {
            "filename": filename,
            "path": str(path),
            "code": code,
            "type": "EA",
            "strategy_type": strategy_type,
            "created_at": datetime.utcnow().isoformat(),
        }

    def list_generated_files(self) -> List[Dict[str, Any]]:
        """Return metadata for all files under the generated directory."""
        files = []
        for f in self._generated_dir.rglob("*"):
            if f.is_file():
                stat = f.stat()
                ext = f.suffix.lower()
                type_map = {".mq5": "MQL5", ".mq4": "MQL4", ".pine": "PineScript", ".py": "Python"}
                files.append({
                    "name": f.name,
                    "path": str(f.relative_to(self._generated_dir)),
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": type_map.get(ext, "unknown"),
                })
        return files
