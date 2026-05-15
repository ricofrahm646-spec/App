"""
JARVIS MQL5 Custom Indicator Generator.

Generates complete, syntactically correct .mq5 indicator files for various
indicator types with proper buffer setup and drawing styles.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from mql5.templates.indicator_base import (
    INDICATOR_BASE_TEMPLATE,
    INDICATOR_BOLLINGER_BANDS_LOGIC,
    INDICATOR_CUSTOM_OSCILLATOR_LOGIC,
    INDICATOR_LIQUIDITY_ZONES_LOGIC,
    INDICATOR_MOVING_AVERAGE_LOGIC,
    INDICATOR_ORDER_BLOCKS_LOGIC,
    INDICATOR_RSI_LOGIC,
)


class IndicatorType(str, Enum):
    MOVING_AVERAGE = "moving_average"
    RSI = "rsi"
    BOLLINGER_BANDS = "bollinger_bands"
    ORDER_BLOCKS = "order_blocks"
    LIQUIDITY_ZONES = "liquidity_zones"
    CUSTOM_OSCILLATOR = "custom_oscillator"


class DrawingStyle(str, Enum):
    LINE = "DRAW_LINE"
    HISTOGRAM = "DRAW_HISTOGRAM"
    ARROW = "DRAW_ARROW"
    SECTION = "DRAW_SECTION"
    NONE = "DRAW_NONE"
    COLOR_HISTOGRAM = "DRAW_COLOR_HISTOGRAM"


@dataclass
class PlotConfig:
    """Configuration for a single indicator plot."""

    label: str
    style: str = "DRAW_LINE"
    color: str = "clrDodgerBlue"
    width: int = 2
    line_style: str = "STYLE_SOLID"
    arrow_code: int = 233


@dataclass
class IndicatorParams:
    """Parameters for indicator generation."""

    chart_window: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _IndicatorSpec:
    """Internal specification for building an indicator."""

    plots: List[PlotConfig]
    buffers: List[str]
    inputs: str
    init_code: str
    globals_code: str
    logic: str
    min_bars: int
    chart_window: bool


def _build_ma_spec() -> _IndicatorSpec:
    return _IndicatorSpec(
        plots=[
            PlotConfig("MA", "DRAW_LINE", "clrDodgerBlue", 2),
            PlotConfig("Signal", "DRAW_LINE", "clrOrangeRed", 1),
        ],
        buffers=["MaBuffer", "SignalBuffer"],
        inputs="""input int    InpMAPeriod     = 14;    // MA Period
input int    InpSignalPeriod = 0;     // Signal Period (0=disabled)
input ENUM_MA_METHOD InpMAMethod = MODE_SMA; // MA Method
""",
        init_code="",
        globals_code="",
        logic=INDICATOR_MOVING_AVERAGE_LOGIC,
        min_bars=50,
        chart_window=True,
    )


def _build_rsi_spec() -> _IndicatorSpec:
    return _IndicatorSpec(
        plots=[
            PlotConfig("RSI", "DRAW_LINE", "clrDodgerBlue", 2),
            PlotConfig("Overbought", "DRAW_LINE", "clrRed", 1, "STYLE_DOT"),
            PlotConfig("Oversold", "DRAW_LINE", "clrGreen", 1, "STYLE_DOT"),
        ],
        buffers=["RsiBuffer", "OverboughtBuffer", "OversoldBuffer",
                 "AvgGainBuffer", "AvgLossBuffer"],
        inputs="""input int    InpRSIPeriod    = 14;    // RSI Period
input double InpOverbought   = 70.0;  // Overbought Level
input double InpOversold     = 30.0;  // Oversold Level
""",
        init_code="""
   IndicatorSetDouble(INDICATOR_MINIMUM, 0.0);
   IndicatorSetDouble(INDICATOR_MAXIMUM, 100.0);
   IndicatorSetInteger(INDICATOR_LEVELS, 2);
   IndicatorSetDouble(INDICATOR_LEVELVALUE, 0, InpOverbought);
   IndicatorSetDouble(INDICATOR_LEVELVALUE, 1, InpOversold);
""",
        globals_code="",
        logic=INDICATOR_RSI_LOGIC,
        min_bars=50,
        chart_window=False,
    )


def _build_bb_spec() -> _IndicatorSpec:
    return _IndicatorSpec(
        plots=[
            PlotConfig("Middle", "DRAW_LINE", "clrDodgerBlue", 2),
            PlotConfig("Upper", "DRAW_LINE", "clrRed", 1, "STYLE_DASH"),
            PlotConfig("Lower", "DRAW_LINE", "clrGreen", 1, "STYLE_DASH"),
        ],
        buffers=["MiddleBuffer", "UpperBuffer", "LowerBuffer"],
        inputs="""input int    InpBBPeriod     = 20;    // BB Period
input double InpBBDeviation  = 2.0;   // BB Deviation
""",
        init_code="",
        globals_code="",
        logic=INDICATOR_BOLLINGER_BANDS_LOGIC,
        min_bars=50,
        chart_window=True,
    )


def _build_order_blocks_spec() -> _IndicatorSpec:
    return _IndicatorSpec(
        plots=[
            PlotConfig("BullOB", "DRAW_ARROW", "clrLime", 2, arrow_code=233),
            PlotConfig("BearOB", "DRAW_ARROW", "clrRed", 2, arrow_code=234),
        ],
        buffers=["BullOBBuffer", "BearOBBuffer"],
        inputs="""input double InpOBStrength   = 1.5;   // Order Block Strength Multiplier
input int    InpLookback     = 50;    // Lookback Period
""",
        init_code="",
        globals_code="",
        logic=INDICATOR_ORDER_BLOCKS_LOGIC,
        min_bars=10,
        chart_window=True,
    )


def _build_liquidity_zones_spec() -> _IndicatorSpec:
    return _IndicatorSpec(
        plots=[
            PlotConfig("LiqHigh", "DRAW_ARROW", "clrOrange", 2, arrow_code=218),
            PlotConfig("LiqLow", "DRAW_ARROW", "clrAqua", 2, arrow_code=217),
        ],
        buffers=["LiqHighBuffer", "LiqLowBuffer"],
        inputs="""input int    InpLookback    = 50;    // Lookback Period
input double InpZoneWidth   = 100;   // Zone Width in Points
input int    InpMinTouches  = 3;     // Min Touches for Zone
""",
        init_code="",
        globals_code="",
        logic=INDICATOR_LIQUIDITY_ZONES_LOGIC,
        min_bars=60,
        chart_window=True,
    )


def _build_custom_oscillator_spec() -> _IndicatorSpec:
    return _IndicatorSpec(
        plots=[
            PlotConfig("Oscillator", "DRAW_LINE", "clrDodgerBlue", 2),
            PlotConfig("Signal", "DRAW_LINE", "clrOrangeRed", 1),
            PlotConfig("Histogram", "DRAW_HISTOGRAM", "clrGray", 2),
            PlotConfig("ZeroLine", "DRAW_LINE", "clrGray", 1, "STYLE_DOT"),
        ],
        buffers=["OscBuffer", "SignalBuffer", "HistBuffer", "ZeroBuffer"],
        inputs="""input int    InpMomentumPeriod = 14;   // Momentum Period
input int    InpSmoothPeriod   = 10;   // Smoothing Period
input int    InpSignalPeriod   = 9;    // Signal Period
""",
        init_code="""
   IndicatorSetInteger(INDICATOR_LEVELS, 1);
   IndicatorSetDouble(INDICATOR_LEVELVALUE, 0, 0.0);
""",
        globals_code="",
        logic=INDICATOR_CUSTOM_OSCILLATOR_LOGIC,
        min_bars=30,
        chart_window=False,
    )


_SPEC_BUILDERS = {
    IndicatorType.MOVING_AVERAGE: _build_ma_spec,
    IndicatorType.RSI: _build_rsi_spec,
    IndicatorType.BOLLINGER_BANDS: _build_bb_spec,
    IndicatorType.ORDER_BLOCKS: _build_order_blocks_spec,
    IndicatorType.LIQUIDITY_ZONES: _build_liquidity_zones_spec,
    IndicatorType.CUSTOM_OSCILLATOR: _build_custom_oscillator_spec,
}


class IndicatorGenerator:
    """Generates complete MQL5 custom indicator source files.

    Supports multiple indicator types including Moving Averages, RSI,
    Bollinger Bands, Order Blocks, Liquidity Zones, and custom oscillators.
    Generated indicators include proper buffer setup, drawing styles,
    and complete OnCalculate implementations.
    """

    SUPPORTED_INDICATORS = list(IndicatorType)

    def __init__(self, output_dir: str = "./output/indicators") -> None:
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_indicator(
        self,
        name: str,
        indicator_type: str | IndicatorType,
        params: Optional[Dict[str, Any] | IndicatorParams] = None,
    ) -> str:
        """Generate a complete .mq5 custom indicator file.

        Args:
            name: Indicator name (used for filename and internal identification).
            indicator_type: One of the supported indicator types.
            params: Optional parameters to override defaults.

        Returns:
            Absolute path to the generated .mq5 file.

        Raises:
            ValueError: If indicator_type is not supported.
        """
        if isinstance(indicator_type, str):
            indicator_type = IndicatorType(indicator_type.lower())

        if indicator_type not in IndicatorType:
            raise ValueError(
                f"Unsupported indicator type: {indicator_type}. "
                f"Choose from: {[i.value for i in IndicatorType]}"
            )

        spec = _SPEC_BUILDERS[indicator_type]()
        mql5_code = self._build_indicator_code(name, indicator_type, spec, params)

        file_path = os.path.join(self.output_dir, f"{name}.mq5")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(mql5_code)

        return os.path.abspath(file_path)

    def list_indicators(self) -> list[str]:
        """Return list of supported indicator type names."""
        return [i.value for i in IndicatorType]

    def _build_indicator_code(
        self,
        name: str,
        indicator_type: IndicatorType,
        spec: _IndicatorSpec,
        params: Optional[Dict[str, Any] | IndicatorParams],
    ) -> str:
        """Assemble the final MQL5 indicator source code."""
        num_plots = len(spec.plots)
        num_buffers = len(spec.buffers)

        plot_properties = self._generate_plot_properties(spec.plots)
        buffer_declarations = self._generate_buffer_declarations(spec.buffers)
        buffer_setup = self._generate_buffer_setup(spec.plots, spec.buffers)

        chart_window_str = "" if spec.chart_window else "\n#property indicator_separate_window"

        replacements = {
            "indicator_name": name,
            "indicator_type": indicator_type.value.replace("_", " ").title(),
            "chart_window": chart_window_str,
            "num_buffers": str(num_buffers),
            "num_plots": str(num_plots),
            "plot_properties": plot_properties,
            "custom_inputs": spec.inputs,
            "buffer_declarations": buffer_declarations,
            "custom_globals": spec.globals_code,
            "buffer_setup": buffer_setup,
            "custom_init": spec.init_code,
            "min_bars": str(spec.min_bars),
            "calculation_logic": spec.logic,
        }

        code = INDICATOR_BASE_TEMPLATE
        for key, value in replacements.items():
            code = code.replace("{" + key + "}", value)

        return code

    def _generate_plot_properties(self, plots: List[PlotConfig]) -> str:
        """Generate #property indicator_label/type/color/style/width lines."""
        lines: list[str] = []
        for idx, plot in enumerate(plots):
            n = idx + 1
            lines.append(f'#property indicator_label{n}  "{plot.label}"')
            lines.append(f"#property indicator_type{n}   {plot.style}")
            lines.append(f"#property indicator_color{n}  {plot.color}")
            lines.append(f"#property indicator_style{n}  {plot.line_style}")
            lines.append(f"#property indicator_width{n}  {plot.width}")
            if plot.style == "DRAW_ARROW":
                lines.append(
                    f"// Arrow code for plot {n} set in OnInit"
                )
            lines.append("")
        return "\n".join(lines)

    def _generate_buffer_declarations(self, buffers: List[str]) -> str:
        """Generate double BufferName[]; declarations."""
        return "\n".join(f"double {buf}[];" for buf in buffers)

    def _generate_buffer_setup(
        self, plots: List[PlotConfig], buffers: List[str]
    ) -> str:
        """Generate SetIndexBuffer and PlotIndexSetXxx calls."""
        lines: list[str] = []
        for idx, buf_name in enumerate(buffers):
            if idx < len(plots):
                lines.append(
                    f"   SetIndexBuffer({idx}, {buf_name}, INDICATOR_DATA);"
                )
                plot = plots[idx]
                lines.append(
                    f'   PlotIndexSetString({idx}, PLOT_LABEL, "{plot.label}");'
                )
                if plot.style == "DRAW_ARROW":
                    lines.append(
                        f"   PlotIndexSetInteger({idx}, PLOT_ARROW, {plot.arrow_code});"
                    )
                lines.append(
                    f"   PlotIndexSetDouble({idx}, PLOT_EMPTY_VALUE, EMPTY_VALUE);"
                )
            else:
                lines.append(
                    f"   SetIndexBuffer({idx}, {buf_name}, INDICATOR_CALCULATIONS);"
                )
            lines.append("")
        return "\n".join(lines)
