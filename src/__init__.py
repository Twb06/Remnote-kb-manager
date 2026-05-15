"""
src package - NLI Pipeline v1.3 核心模組

模組結構:
- parsers: AST 解析器
- pipeline: Pipeline 核心邏輯 (Steps A-D)
- routers: NLI 路由器 (mock/真實模型)
"""

__version__ = "1.3.0"
__all__ = [
    "parsers",
    "pipeline",
    "routers"
]
