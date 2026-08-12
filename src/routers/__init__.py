"""
routers package - NLI 路由器模組

Heavy ML dependencies (nli_bart) are NOT auto-imported here to avoid loading
the transformers library on every package import.  Import them explicitly:

    from src.routers.nli_bart import RealNLIRouter
"""

from .nli_types import NLIResult, FinalAction, LLMInterventionCase

__all__ = [
    # 資料結構
    "NLIResult",
    "FinalAction",
    "LLMInterventionCase",
]
