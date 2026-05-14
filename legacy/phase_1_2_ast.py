"""
Phase 1.2: AST + Breadcrumb Core Library

提供文本結構解析和面包屑生成的核心功能，用於：
- NotebookLM 提取內容的 AST 解析
- RemNote 現有內容的階層轉換
- NLI 路由的上下文增強
"""

from typing import List, Dict, Tuple
import re


class BreadcrumbIndex:
    """
    在單次流程中追蹤 breadcrumb 路徑的記憶體索引。
    不涉及持久化或 kb_map 綁定。
    """

    def __init__(self):
        self.breadcrumb_map = {}  # content → breadcrumb_path (流程內臨時使用)
        self.hierarchy_cache = {}  # 快速查詢物件的層級路徑

    def add(self, content: str, breadcrumb_path: str):
        """在流程中記錄一個內容的 breadcrumb"""
        self.breadcrumb_map[content] = breadcrumb_path
        # 清理快取以保持同步
        self.hierarchy_cache.clear()

    def get_breadcrumb(self, content: str) -> str | None:
        """查詢內容的 breadcrumb（流程中使用）"""
        return self.breadcrumb_map.get(content)

    def get_all_breadcrumbs(self) -> dict:
        """返回所有 breadcrumb 映射（用於調試或報告）"""
        return self.breadcrumb_map.copy()

    def get_hierarchy_info(self, breadcrumb: str) -> dict:
        """解析 breadcrumb 字符串並返回層級資訊"""
        if breadcrumb in self.hierarchy_cache:
            return self.hierarchy_cache[breadcrumb]

        # 移除方括號並分割
        clean_breadcrumb = breadcrumb.strip('[]')
        parts = [p.strip() for p in clean_breadcrumb.split('>')]

        hierarchy_info = {
            "full_path": clean_breadcrumb,
            "parts": parts,
            "depth": len(parts),
            "leaf": parts[-1] if parts else None,
            "ancestors": parts[:-1] if len(parts) > 1 else []
        }

        self.hierarchy_cache[breadcrumb] = hierarchy_info
        return hierarchy_info


def detect_indent_level(line: str) -> Tuple[int, str]:
    """
    檢測行的縮排深度。

    支持多種縮排方式：
    - 2 空格
    - 4 空格
    - Tab 字符

    Args:
        line: 要檢測的行

    Returns:
        (depth, content): 深度整數和去除縮排後的內容

    Examples:
        >>> detect_indent_level("  Hello")
        (1, "Hello")
        >>> detect_indent_level("    World")
        (1, "World")  # 4 spaces = 1 level
        >>> detect_indent_level("\\t\\tTest")
        (2, "Test")
    """
    if not line.strip():
        return 0, ""

    # 計算前導空格/Tab
    match = re.match(r'^([ \t]*)', line)
    indent_str = match.group(1) if match else ""

    # 轉換為統一的深度單位
    # 策略：1 tab = 1 level, 4 spaces = 1 level, 2 spaces = 1 level
    depth = 0
    i = 0
    while i < len(indent_str):
        if indent_str[i] == '\t':
            depth += 1
            i += 1
        elif indent_str[i:i+4] == '    ':  # 4 spaces
            depth += 1
            i += 4
        elif indent_str[i:i+2] == '  ':   # 2 spaces
            depth += 1
            i += 2
        else:
            i += 1

    content = line.lstrip()
    return depth, content


def build_ast_tree(lines: List[str]) -> List[dict]:
    """
    從扁平行列表建構樹狀結構，保留每個節點的 breadcrumb。

    Args:
        lines: 帶縮排的行列表

    Returns:
        root_nodes: 樹的根節點列表，每個節點帶有 breadcrumb

    Node 結構:
        {
            "depth": 0,
            "text": "Root Item",
            "breadcrumb": "Root Item",  # 或 "[Root Item]"
            "breadcrumb_parts": ["Root Item"],
            "children": [...]
        }

    Examples:
        >>> lines = ["Root", "  Child 1", "  Child 2", "    Grandchild"]
        >>> tree = build_ast_tree(lines)
        >>> tree[0]["text"]
        "Root"
        >>> tree[0]["children"][0]["text"]
        "Child 1"
    """
    root_nodes = []
    stack = []  # (depth, node) 棧

    for line in lines:
        if not line.strip():
            continue

        depth, content = detect_indent_level(line)

        # 建立新節點
        node = {
            "depth": depth,
            "text": content,
            "breadcrumb_parts": [],
            "children": [],
            "parent": None
        }

        # 清理堆疊：移除深度 >= 目前 depth 的節點
        while stack and stack[-1][0] >= depth:
            stack.pop()

        # 計算 breadcrumb: 堆疊中所有節點 + 目前節點
        breadcrumb_parts = [n[1]["text"] for n in stack] + [content]
        node["breadcrumb_parts"] = breadcrumb_parts
        node["breadcrumb"] = " > ".join(breadcrumb_parts)
        node["breadcrumb_formatted"] = f"[{node['breadcrumb']}]"

        # 加入堆疊
        if stack:
            parent = stack[-1][1]
            node["parent"] = parent
            parent["children"].append(node)
        else:
            root_nodes.append(node)

        stack.append((depth, node))

    return root_nodes


def flatten_with_breadcrumbs(root_nodes: List[dict],
                             prefix_format: str = "plain") -> List[dict]:
    """
    遞迴展平樹，每個節點都帶有完整的 breadcrumb。

    Args:
        root_nodes: 樹的根節點列表
        prefix_format: "markdown" | "plain" | "html"

    Returns:
        扁平列表，每項包含 text 和 breadcrumb

    Examples:
        >>> items = flatten_with_breadcrumbs(tree)
        >>> items[0]
        {"text": "Root", "breadcrumb": "Root", ...}
    """
    result = []

    def traverse(node):
        # 根據格式生成內容字符串
        if prefix_format == "markdown":
            content_with_breadcrumb = f"**[{node['breadcrumb']}]** {node['text']}"
        elif prefix_format == "plain":
            content_with_breadcrumb = f"[{node['breadcrumb']}] {node['text']}"
        elif prefix_format == "html":
            content_with_breadcrumb = f"<breadcrumb>{node['breadcrumb']}</breadcrumb><content>{node['text']}</content>"
        else:
            content_with_breadcrumb = node['text']

        result.append({
            "text": node['text'],
            "breadcrumb": node['breadcrumb'],
            "breadcrumb_formatted": node['breadcrumb_formatted'],
            "breadcrumb_parts": node['breadcrumb_parts'],
            "depth": node['depth'],
            "content_with_breadcrumb": content_with_breadcrumb,
            "has_children": len(node['children']) > 0
        })

        # 遞迴遍歷子節點
        for child in node['children']:
            traverse(child)

    for root in root_nodes:
        traverse(root)

    return result


def transform_tree_with_breadcrumbs(tree: dict) -> dict:
    """
    將現有 RemNote 結構轉換為帶 breadcrumb 版本。
    用於 Step C 中轉換 context_trees。

    預期輸入 tree 結構（來自 RemNote CLI):
        {
            "id": "rem_id_123",
            "title": "Node Title",
            "content": "...",
            "children": [...]
        }

    輸出結構：
        {
            "id": "rem_id_123",
            "title": "Node Title",
            "content": "...",
            "breadcrumb": "Ancestor > Parent > Node Title",
            "breadcrumb_formatted": "[Ancestor > Parent > Node Title]",
            "breadcrumb_parts": ["Ancestor", "Parent", "Node Title"],
            "content_with_breadcrumb": "[Ancestor > Parent > Node Title] ...",
            "children": [...]  # 遞迴轉換
        }

    Args:
        tree: RemNote 結構樹

    Returns:
        transform 後的樹，帶 breadcrumb
    """
    def traverse(node, ancestor_parts=None):
        if ancestor_parts is None:
            ancestor_parts = []

        # 當前節點的 title（或 text）
        node_title = node.get("title") or node.get("text") or "Untitled"

        # 計算 breadcrumb
        breadcrumb_parts = ancestor_parts + [node_title]
        breadcrumb = " > ".join(breadcrumb_parts)
        breadcrumb_formatted = f"[{breadcrumb}]"

        # 生成帶 breadcrumb 的內容 (plain 格式)
        original_content = node.get("content", "")
        content_with_breadcrumb = f"[{breadcrumb}] {original_content}" if original_content else breadcrumb_formatted

        # 轉換節點
        transformed = {
            "id": node.get("id"),
            "title": node_title,
            "content": original_content,
            "breadcrumb": breadcrumb,
            "breadcrumb_formatted": breadcrumb_formatted,
            "breadcrumb_parts": breadcrumb_parts,
            "content_with_breadcrumb": content_with_breadcrumb,
            "depth": len(breadcrumb_parts) - 1,
            "children": []
        }

        # 複製其他屬性
        for key in node:
            if key not in ["title", "content", "children", "id"]:
                transformed[key] = node[key]

        # 遞迴轉換子節點
        if "children" in node and node["children"]:
            for child in node["children"]:
                transformed["children"].append(traverse(child, breadcrumb_parts))

        return transformed

    return traverse(tree)


def enrich_nli_input_with_breadcrumb(
    premise_node: dict,
    hypothesis_line: str,
    use_breadcrumb: bool = True
) -> Tuple[str, str]:
    """
    使用 breadcrumb 增強 NLI 輸入，提高判斷準確度。

    Args:
        premise_node: 節點物件 (含 breadcrumb 資訊)
        hypothesis_line: 假設文本
        use_breadcrumb: 是否使用 breadcrumb

    Returns:
        (enriched_premise, enriched_hypothesis): 增強後的配對

    Examples:
        >>> node = {"text": "NTG", "breadcrumb": "Glaucoma > Open-Angle"}
        >>> p, h = enrich_nli_input_with_breadcrumb(node, "NTG pressure < 3")
        >>> p
        "[Glaucoma > Open-Angle] NTG"
    """
    if use_breadcrumb:
        # 為 premise 附加 breadcrumb
        breadcrumb = premise_node.get("breadcrumb", premise_node.get("text", ""))
        premise = f"[{breadcrumb}] {premise_node.get('text', '')}"

        # 為 hypothesis 推斷相同的 breadcrumb
        hypothesis = f"[{breadcrumb}] {hypothesis_line}"
    else:
        premise = premise_node.get("text", "")
        hypothesis = hypothesis_line

    return premise, hypothesis


if __name__ == "__main__":
    # 測試範例
    test_lines = [
        "Ophtalmology",
        "  Glaucoma Types",
        "    Open-Angle",
        "      Normal Tension Glaucoma",
        "        FL Range: <3 mmHg",
        "    Closed-Angle",
        "      Acute Glaucoma"
    ]

    print("=== Phase 1.2 AST + Breadcrumb 測試 ===\n")

    # 測試 build_ast_tree
    print("1. AST 樹構建")
    tree = build_ast_tree(test_lines)
    print(f"   根節點數: {len(tree)}")
    print(f"   第一個根節點: {tree[0]['text']}")
    print(f"   第一個根節點的 breadcrumb: {tree[0]['breadcrumb']}\n")

    # 測試 flatten_with_breadcrumbs
    print("2. 展平為清單")
    items = flatten_with_breadcrumbs(tree)
    print(f"   總項目數: {len(items)}")
    for item in items[:5]:
        print(f"   - {item['content_with_breadcrumb']}")
    print()

    # 測試 BreadcrumbIndex
    print("3. Breadcrumb 索引")
    index = BreadcrumbIndex()
    for item in items:
        index.add(item['text'], item['breadcrumb'])

    retrieved = index.get_breadcrumb("Normal Tension Glaucoma")
    print(f"   查詢 'Normal Tension Glaucoma': {retrieved}\n")

    # 測試 enrich_nli_input_with_breadcrumb
    print("4. NLI 輸入增強")
    node = items[3]  # Normal Tension Glaucoma
    premise, hypothesis = enrich_nli_input_with_breadcrumb(
        node,
        "FL pressure < 3 mmHg"
    )
    print(f"   Premise: {premise}")
    print(f"   Hypothesis: {hypothesis}")
