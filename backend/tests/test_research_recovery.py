import asyncio
import json
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from service.checkpoint_service import CheckpointService
from service.deep_research_v2.state import create_initial_state
from service.deep_research_v2.agents.writer import LeadWriter
from service.deep_research_v2.agents.critic import CriticMaster
from service.deep_research_v2.agents.base import IncompleteLLMResponseError
from service.deep_research_v2.graph import DeepResearchGraph
from service.deep_research_v2.evidence import DRAFT_NOTICE, guard_draft


class CheckpointTests(unittest.TestCase):
    def test_runtime_queue_removed_without_mutating_state(self):
        queue = asyncio.Queue()
        state = {"_message_queue": queue, "facts": [{"content": "事实"}],
                 "nested": {"_message_queue": queue, "created": datetime(2026, 1, 1)},
                 "id": uuid4()}
        clean = CheckpointService()._clean_state_for_storage(state)
        self.assertNotIn("_message_queue", clean)
        self.assertNotIn("_message_queue", clean["nested"])
        self.assertEqual(clean["facts"], state["facts"])
        self.assertIs(state["_message_queue"], queue)
        self.assertEqual(json.loads(json.dumps(clean)), clean)

    def test_unknown_objects_are_not_silently_corrupted(self):
        with self.assertRaises(TypeError):
            CheckpointService()._clean_state_for_storage({"facts": [object()]})


class ReviewTests(unittest.TestCase):
    def test_empty_review_cannot_pass(self):
        with self.assertRaises(ValueError):
            CriticMaster._validate_review_result({})
        with self.assertRaises(ValueError):
            CriticMaster._validate_review_result({"overall_assessment": {
                "quality_score": 0, "verdict": "pass"}, "issues": []})
        CriticMaster._validate_review_result({"overall_assessment": {
            "quality_score": 8, "verdict": "pass"}, "issues": []})


class ReviewCallTests(unittest.IsolatedAsyncioTestCase):
    async def test_structured_review_keeps_thinking_with_output_budget(self):
        critic = CriticMaster("test-only", "https://example.invalid/v1",
                              model="deepseek-v4-pro-0813")
        critic.call_llm = AsyncMock(return_value=json.dumps({
            "overall_assessment": {"quality_score": 8, "verdict": "pass"},
            "issues": [],
        }))
        state = create_initial_state("测试问题", "test-review")
        state["final_report"] = "待审核报告"
        result = await critic._review_content(state)
        critic._validate_review_result(result)
        self.assertIs(critic.call_llm.call_args.kwargs["enable_thinking"], True)
        self.assertEqual(critic.call_llm.call_args.kwargs["max_tokens"], 32768)

    async def test_truncated_review_retries_with_larger_budget(self):
        critic = CriticMaster("test-only", "https://example.invalid/v1",
                              model="deepseek-v4-pro-0813")
        critic.call_llm = AsyncMock(side_effect=[
            IncompleteLLMResponseError("truncated"),
            json.dumps({"overall_assessment": {"quality_score": 8,
                                              "verdict": "pass"}, "issues": []}),
        ])
        state = create_initial_state("测试问题", "test-review-retry")
        state["final_report"] = "待审核报告"
        result = await critic._review_content(state)
        self.assertEqual(result["overall_assessment"]["verdict"], "pass")
        self.assertEqual([call.kwargs["max_tokens"] for call in critic.call_llm.call_args_list],
                         [32768, 65536])
        self.assertTrue(all(call.kwargs["enable_thinking"]
                            for call in critic.call_llm.call_args_list))


class ResumeTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_stages_are_not_repeated(self):
        class Agent:
            def __init__(self, name, update=None):
                self.name, self.calls, self.update = name, 0, update

            async def process(self, state):
                self.calls += 1
                if self.update:
                    state.update(self.update)

        class Checkpoints:
            def __init__(self):
                self.saved, self.status = [], "running"

            def load_full_checkpoint(self, session_id):
                return {"ui_state_json": {"research_steps": [
                    {"type": "planning", "status": "completed"},
                    {"type": "researching", "status": "completed"}]}}

            def save_checkpoint(self, **kwargs):
                self.saved.append(list(kwargs["state"]["completed_phases"]))
                return "saved"

            def update_status(self, session_id, status, *args):
                self.status = status

        state = create_initial_state("旧问题", "resume-test")
        state.update(_resuming=True, _user_id=None,
                     completed_phases=["planning", "researching"])
        state["outline"] = [{"id": "a", "title": "旧大纲", "status": "researched"}]
        state["facts"] = [{"id": "f", "content": "旧事实"}]
        graph = DeepResearchGraph.__new__(DeepResearchGraph)
        graph.checkpoint_service = Checkpoints()
        graph.architect, graph.scout = Agent("architect"), Agent("scout")
        graph.data_analyst, graph.wizard = Agent("analyst"), Agent("wizard")
        graph.writer = Agent("writer", {"final_report": "已完成"})
        graph.critic = Agent("critic", {"phase": "completed", "quality_score": 8})
        events = [event async for event in graph._run_simplified(state)]
        self.assertEqual((graph.architect.calls, graph.scout.calls), (0, 0))
        self.assertEqual((graph.data_analyst.calls, graph.writer.calls, graph.critic.calls), (1, 1, 1))
        self.assertEqual(state["facts"], [{"id": "f", "content": "旧事实"}])
        self.assertEqual(graph.checkpoint_service.status, "completed")
        self.assertIn("reviewing", graph.checkpoint_service.saved[-1])
        self.assertTrue(any(event["type"] == "research_complete" for event in events))

    async def test_invalid_review_marks_checkpoint_failed(self):
        class FailingReview:
            name = "critic"

            async def process(self, state):
                raise ValueError("质量审核未返回 overall_assessment")

        class Checkpoints:
            status = "running"

            def load_full_checkpoint(self, session_id):
                return {"ui_state_json": {"research_steps": []}}

            def save_checkpoint(self, **kwargs):
                return "saved"

            def update_status(self, session_id, status, *args):
                self.status = status

        state = create_initial_state("旧问题", "invalid-review-test")
        state.update(_resuming=True, _user_id=None,
                     completed_phases=["planning", "researching", "analyzing", "writing"],
                     final_report="待审核报告")
        graph = DeepResearchGraph.__new__(DeepResearchGraph)
        graph.checkpoint_service = Checkpoints()
        graph.critic = FailingReview()
        events = [event async for event in graph._run_simplified(state)]
        self.assertEqual(graph.checkpoint_service.status, "failed")
        self.assertTrue(any(event["type"] == "error" for event in events))
        self.assertFalse(any(event["type"] == "research_complete" for event in events))


class WriterTests(unittest.IsolatedAsyncioTestCase):
    async def test_synthesis_retries_then_uses_saved_sections(self):
        writer = LeadWriter("test-only", "https://example.invalid/v1",
                            model="deepseek-v4-pro-0813")
        writer.call_llm = AsyncMock(side_effect=[
            IncompleteLLMResponseError("truncated"),
            IncompleteLLMResponseError("truncated again"),
        ])
        state = create_initial_state("家用储能", "writer-fallback")
        state["outline"] = [
            {"id": "market", "title": "市场概况"},
            {"id": "companies", "title": "代表企业"},
        ]
        state["draft_sections"] = {
            "market": "市场章节内容",
            "companies": "企业章节内容",
        }

        await writer._synthesize_report(state)

        self.assertEqual([call.kwargs["max_tokens"] for call in writer.call_llm.call_args_list],
                         [32768, 65536])
        self.assertTrue(all(call.kwargs["enable_thinking"]
                            for call in writer.call_llm.call_args_list))
        self.assertIn("## 市场概况", state["final_report"])
        self.assertIn("## 代表企业", state["final_report"])
        self.assertEqual(state["report_generation_mode"], "section_fallback")

    async def test_synthesis_retry_accepts_complete_report(self):
        writer = LeadWriter("test-only", "https://example.invalid/v1",
                            model="deepseek-v4-pro-0813")
        writer.call_llm = AsyncMock(side_effect=[
            IncompleteLLMResponseError("truncated"),
            json.dumps({"full_report": "完整报告", "references": []}),
        ])
        state = create_initial_state("家用储能", "writer-retry")
        state["facts"] = [{"content": "已检索事实", "source_url": "https://example.com"}]

        await writer._synthesize_report(state)

        self.assertEqual(state["final_report"], "完整报告")
        self.assertEqual(writer.call_llm.await_count, 2)

    async def test_no_evidence_still_writes_and_revises(self):
        writer = LeadWriter("test-only", "https://example.invalid/v1")
        state = create_initial_state("交通应用", "test")
        state["phase"] = "writing"
        state["outline"] = [{"id": "one", "title": "场景", "status": "pending"}]
        raw = "交通分析 [来源](https://invented.invalid) [1]"
        writer.call_llm = AsyncMock(side_effect=[
            json.dumps({"content": raw, "citations": [{"source": "invented"}]}),
            json.dumps({"full_report": raw, "references": [{"url": "https://invented.invalid"}]}),
            json.dumps({"revised_content": raw}),
        ])
        await writer.process(state)
        self.assertIn(DRAFT_NOTICE, state["final_report"])
        self.assertIn(DRAFT_NOTICE, state["draft_sections"]["one"])
        self.assertEqual(state["references"], [])
        self.assertNotIn("https://", state["final_report"])
        self.assertNotIn("[1]", state["final_report"])
        state["phase"] = "revising"
        await writer.process(state)
        self.assertIn(DRAFT_NOTICE, state["final_report"])
        self.assertEqual(writer.call_llm.await_count, 3)
        self.assertIn("没有可用检索事实", writer.call_llm.call_args.kwargs["user_prompt"])

    def test_evidence_backed_content_unchanged(self):
        state = {"facts": [{"content": "实际检索事实"}], "references": [{"url": "https://example.com"}]}
        report = "内容 [来源](https://example.com)"
        self.assertEqual(guard_draft(state, report), report)
        self.assertEqual(len(state["references"]), 1)

if __name__ == "__main__":
    unittest.main()
