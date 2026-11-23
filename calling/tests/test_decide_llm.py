#!/usr/bin/env python3
"""Offline tests for decide_llm with a fake model. No network, no game."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "calling"))

import decide_llm  # noqa: E402
import generalissimo_output as g  # noqa: E402

GT = {"year": 1936, "month": 1, "day": 5, "hour": 12}


def doc(allow=True):
    return {"meta": {"game_time": GT, "allow_write": allow, "geography_scope": {"kind": "global"},
                     "player_country": {"index": 44, "tag": "ETH"}},
            "policy": {"stance": "annihilate"},
            "world": {"own_units": [{"unit_id": 1, "province_id": 10, "organization": 50},
                                    {"unit_id": 2, "province_id": 10, "organization": 45}],
                      "provinces": [{"province_id": 10, "neighbors": [11, 30],
                                     "controller": {"index": 44}}],
                      "visible_units": [], "combats": [], "wars": []}}


def reply(obj):
    text = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return {"choices": [{"message": {"content": text}}], "usage": {"total_tokens": 10}}


class DecideLLM(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._saved = (decide_llm._call, decide_llm.api_key, decide_llm.ARCHIVE)
        decide_llm.ARCHIVE = Path(self.tmp.name)
        decide_llm.api_key = lambda: "test-key"
        self.calls = []

        def restore():
            decide_llm._call, decide_llm.api_key, decide_llm.ARCHIVE = self._saved
        self.addCleanup(restore)

    def fake(self, obj):
        def _c(messages, key):
            self.calls.append(messages)
            if isinstance(obj, Exception):
                raise obj
            return reply(obj)
        decide_llm._call = _c

    def test_observation_only_never_calls_model(self):
        self.fake({"orders": []})
        out = decide_llm.decide(doc(allow=False))
        self.assertEqual(self.calls, [])
        self.assertEqual(out["orders"], [])

    def test_no_key_falls_back_without_call(self):
        self.fake({"orders": []})
        decide_llm.api_key = lambda: None
        out = decide_llm.decide(doc())
        self.assertEqual(self.calls, [])
        self.assertTrue(any("DEEPSEEK_API_KEY" in r for r in out["brief"]["risks"]))

    def test_valid_orders_accepted_invalid_dropped(self):
        self.fake({"orders": [
            {"type": "move", "unit_id": 1, "target": 11, "reason": "前出"},
            {"type": "move", "unit_id": 999, "target": 11},        # unknown unit
            {"type": "build_division", "unit_id": 2, "target": 11},  # not allowed
            {"type": "cancel", "unit_id": 2}],
            "intent": "稳住", "summary": "局势平稳。", "risks": ["敌军集结"]})
        d = doc()
        out = decide_llm.decide(d)
        self.assertEqual(g.validate_output(out, d), [])
        self.assertEqual([(o["type"], o["subject"]["unit_ids"]) for o in out["orders"]],
                         [("move", [1]), ("cancel", [2])])
        self.assertTrue(out["brief"]["summary"].startswith("【大模型】"))
        self.assertTrue(any("2 条命令不合规" in r for r in out["brief"]["risks"]))
        rec = json.loads(next(Path(self.tmp.name).glob("llm_*.json")).read_text(encoding="utf-8"))
        self.assertEqual(len(rec["dropped"]), 2)
        self.assertNotIn("test-key", json.dumps(rec))

    def test_garbage_reply_falls_back_to_rules(self):
        self.fake("这不是 JSON")
        out = decide_llm.decide(doc())
        self.assertTrue(any("大模型本拍不可用" in r for r in out["brief"]["risks"]))

    def test_network_error_falls_back(self):
        import urllib.error
        self.fake(urllib.error.URLError("offline"))
        out = decide_llm.decide(doc())
        self.assertEqual(g.validate_output(out, doc()), [])

    def test_digest_is_compact_and_has_no_evidence(self):
        dig = decide_llm.digest(doc())
        self.assertEqual(dig["stance"], "annihilate")
        self.assertEqual(dig["own_units"][0], {"id": 1, "name": "#1", "prov": 10, "org": 50, "hp": 0})


if __name__ == "__main__":
    unittest.main()
