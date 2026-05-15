"""
JARVIS MQL5 Generator Package.

Provides tools for generating, compiling, and deploying MQL5 Expert Advisors
and custom indicators for MetaTrader 5.
"""


def __getattr__(name: str):
    if name == "EAGenerator":
        from mql5.generators.ea_generator import EAGenerator
        return EAGenerator
    if name == "IndicatorGenerator":
        from mql5.generators.indicator_generator import IndicatorGenerator
        return IndicatorGenerator
    if name == "MQL5Compiler":
        from mql5.compiler.compiler import MQL5Compiler
        return MQL5Compiler
    raise AttributeError(f"module 'mql5' has no attribute {name!r}")


__all__ = ["EAGenerator", "IndicatorGenerator", "MQL5Compiler"]
__version__ = "1.0.0"
