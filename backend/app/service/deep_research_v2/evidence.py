"""无检索事实时的写作降级规则，不阻断报告生成。"""
import re

DRAFT_NOTICE = "参考草稿：本次未获取可用于写作的检索事实，内容基于模型已有知识，未经本次联网核验。具体数据、时效性结论和来源归属需另行核实。"
DRAFT_INSTRUCTION = "\n本次没有可用检索事实。请继续提供基于已有知识的参考草稿。不要声称已检索或核实来源，不要生成引用、参考文献、网址或无依据的精确统计数字；不确定内容明确标注待核实。citations 和 references 必须为空数组。此规则优先于下文的格式要求。\n"


def lacks_evidence(state):
    return not state.get("facts")


def writing_instruction(state):
    return DRAFT_INSTRUCTION if lacks_evidence(state) else ""


def guard_draft(state, content):
    if not lacks_evidence(state):
        return content
    state["references"] = []
    state["evidence_status"] = "unverified_draft"
    # 去除模型生成的引用链接及数字引用标记，保留正文和链接的可读文本。
    content = re.sub(r"!?\[([^]\n]+)\]\([^\n]*?\)", r"\1", content)
    content = re.sub(r"(?im)^\s*\[\d+\]:.*$", "", content)
    content = re.sub(r"https?://[^\s<>）)]+", "", content)
    content = re.sub(r"\[\d+(?:[,，、 -]\d+)*\]", "", content)
    content = content.replace("> " + DRAFT_NOTICE, "").strip()
    return "> " + DRAFT_NOTICE + "\n\n" + content
