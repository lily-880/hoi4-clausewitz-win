#!/usr/bin/env python3
"""Offline tests for scripts/live_trial.py pure helpers. No game access."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import live_trial as lt  # noqa: E402


def order(t, **kw):
    return {"order_seq": 1, "type": t, "subject": {"unit_ids": [1, 2]}, **kw}


class Expand(unittest.TestCase):
    def test_move_and_strategic_map_per_unit(self):
        self.assertEqual(lt._expand(order("move", target_province_ids=[5])),
                         [("move", 1, 5), ("move", 2, 5)])
        self.assertEqual(lt._expand(order("strategic_redeploy", target_province_ids=[5])),
                         [("strategic_redeploy", 1, 5), ("strategic_redeploy", 2, 5)])

    def test_cancel_only_current_movement(self):
        self.assertEqual(lt._expand(order("cancel", cancel_scope="current_movement")),
                         [("cancel", 1, None), ("cancel", 2, None)])
        self.assertTrue(isinstance(lt._expand(order("cancel", cancel_scope="all_queued")), str))

    def test_unverified_types_refused(self):
        for t in ("attack", "support_attack", "retreat", "create_army", "train"):
            self.assertTrue(lt._expand(order(t, target_province_ids=[5])).startswith("UNSUPPORTED"))

    def test_multi_target_and_army_subject_refused(self):
        self.assertIsInstance(lt._expand(order("move", target_province_ids=[5, 6])), str)
        self.assertIsInstance(lt._expand(order("move", target_province_ids=[5],
                                               path_province_ids=[4, 5])), str)
        o = order("move", target_province_ids=[5])
        o["subject"] = {"army_ids": [10]}
        self.assertIsInstance(lt._expand(o), str)

    def test_gate_closed_at_import(self):
        import os
        self.assertNotIn("CLAUSEWITZ_ALLOW_POST", os.environ)
        self.assertFalse(lt.MARKER.exists())


if __name__ == "__main__":
    unittest.main()
