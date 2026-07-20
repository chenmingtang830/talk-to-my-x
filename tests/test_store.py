from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from x_feed_loop.store import (  # noqa: E402
    FeedLoopError,
    apply_memory,
    build_context,
    capture_reaction,
    ensure_layout,
    export_preferences,
    import_preferences,
    ingest_posts,
    mark_published,
    migrate_legacy,
    rollback_memory,
    save_draft,
    signal_post,
)


def post(post_id: str = "100", text: str = "A useful post") -> dict[str, object]:
    return {
        "id": post_id,
        "text": text,
        "author": "alice",
        "name": "Alice",
        "url": f"https://x.com/alice/status/{post_id}",
        "source": "timeline",
        "metrics": {"like_count": 2},
    }


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        ensure_layout(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def read(self, relative: str) -> dict[str, object]:
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def ingest(self, post_id: str = "100") -> None:
        ingest_posts([post(post_id)], "timeline", self.root)

    def capture(self, card_id: str = "card_1", post_id: str = "100") -> None:
        capture_reaction(
            {
                "id": card_id,
                "sources": [post_id],
                "raw_reaction": "This changes the framing.",
                "questions": ["What would falsify it?"],
            },
            self.root,
        )

    def test_layout_seeds_preferences_and_memory(self) -> None:
        for relative in ("preferences.md", "memory/USER.md", "memory/TASTE.md", "memory/VOICE.md"):
            self.assertTrue((self.root / relative).read_text(encoding="utf-8").startswith("#"))

    def test_ingest_deduplicates_and_updates(self) -> None:
        first = ingest_posts({"posts": [post()]}, "timeline", self.root)
        second = ingest_posts([post()], "timeline", self.root)
        changed = ingest_posts([post(text="Revised text")], "timeline", self.root)
        self.assertEqual(first["created"], 1)
        self.assertEqual(second["unchanged"], 1)
        self.assertEqual(changed["updated"], 1)
        self.assertEqual(self.read("posts/100.json")["text"], "Revised text")

    def test_ingest_honors_migrated_seen_state(self) -> None:
        (self.root / "state" / "seen.json").write_text('{"home":["100"]}\n', encoding="utf-8")
        self.ingest()
        self.assertEqual(self.read("posts/100.json")["status"], "seen")
        self.assertEqual(build_context(self.root)["posts"], [])

    def test_post_validation_rejects_unsafe_ids_and_urls(self) -> None:
        with self.assertRaises(FeedLoopError):
            ingest_posts([post("../escape")], "timeline", self.root)
        invalid = post()
        invalid["url"] = "http://localhost/post"
        with self.assertRaises(FeedLoopError):
            ingest_posts([invalid], "timeline", self.root)
        mismatch = post()
        mismatch["source"] = "bookmarks"
        with self.assertRaises(FeedLoopError):
            ingest_posts([mismatch], "timeline", self.root)

    def test_signal_and_context_filtering(self) -> None:
        ingest_posts([post("100"), post("101")], "timeline", self.root)
        signal_post("100", "selected", self.root)
        signal_post("101", "skipped", self.root)
        context = build_context(self.root)
        self.assertEqual([item["id"] for item in context["posts"]], ["100"])
        self.assertEqual(self.read("posts/100.json")["signals"][-1]["kind"], "selected")

    def test_reaction_card_updates_and_marks_source_explored(self) -> None:
        self.ingest()
        self.capture()
        capture_reaction(
            {
                "id": "card_1",
                "sources": ["100"],
                "raw_reaction": "Now I see a distribution constraint.",
                "connections": ["Distribution thesis"],
                "status": "developing",
            },
            self.root,
        )
        card = self.read("reactions/card_1.json")
        self.assertEqual(len(card["reactions"]), 2)
        self.assertEqual(card["raw_reaction"], "Now I see a distribution constraint.")
        self.assertEqual(card["status"], "developing")
        source = self.read("posts/100.json")
        self.assertEqual(source["status"], "explored")
        self.assertEqual(source["signals"][-1]["kind"], "explored")

    def test_reaction_requires_source_and_raw_reaction(self) -> None:
        with self.assertRaises(FeedLoopError):
            capture_reaction({"sources": [], "raw_reaction": "idea"}, self.root)
        with self.assertRaises(FeedLoopError):
            capture_reaction({"sources": [post()], "raw_reaction": ""}, self.root)

    def test_draft_revisions_and_card_linkage(self) -> None:
        self.ingest()
        self.capture()
        base = {"id": "draft_1", "text": "First version", "sources": ["100"], "card_ids": ["card_1"]}
        first = save_draft(base, self.root)
        second = save_draft({**base, "text": "Edited version"}, self.root)
        draft = self.read("drafts/draft_1.json")
        self.assertEqual(first["revision"], 1)
        self.assertEqual(second["revision"], 2)
        self.assertEqual([row["text"] for row in draft["revisions"]], ["First version", "Edited version"])
        self.assertEqual(self.read("reactions/card_1.json")["draft_ids"], ["draft_1"])

    def test_draft_schema_validation(self) -> None:
        self.ingest()
        with self.assertRaises(FeedLoopError):
            save_draft({"text": "x", "thread": ["y"], "sources": ["100"]}, self.root)
        with self.assertRaises(FeedLoopError):
            save_draft({"text": "x" * 281, "sources": ["100"]}, self.root)
        with self.assertRaises(FeedLoopError):
            save_draft({"text": "ungrounded", "sources": []}, self.root)

    def test_mark_published_records_result_once(self) -> None:
        self.ingest()
        save_draft({"id": "draft_1", "text": "Draft", "sources": ["100"]}, self.root)
        result = mark_published(
            "draft_1",
            {
                "tweet_ids": ["200"],
                "urls": ["https://x.com/alice/status/200"],
                "text": "Final text",
            },
            self.root,
        )
        self.assertEqual(result["urls"], ["https://x.com/alice/status/200"])
        self.assertEqual(self.read("drafts/draft_1.json")["text"], "Final text")
        with self.assertRaises(FeedLoopError):
            mark_published("draft_1", {"tweet_ids": ["201"], "urls": ["https://x.com/a/status/201"]}, self.root)

    def test_memory_apply_and_rollback(self) -> None:
        self.ingest()
        self.capture()
        before_taste = (self.root / "memory" / "TASTE.md").read_text(encoding="utf-8")
        result = apply_memory(
            {
                "taste_md": "# Taste\n\nPrefer first-principles arguments.",
                "voice_md": "# Voice\n\nUse direct openings.",
                "evidence_card_ids": ["card_1"],
                "rationale": ["The reaction challenged the premise directly."],
            },
            self.root,
        )
        snapshot = self.read(f"history/memory/{result['snapshot_id']}.json")
        self.assertEqual(snapshot["evidence_card_ids"], ["card_1"])
        self.assertIn("first-principles", (self.root / "memory" / "TASTE.md").read_text(encoding="utf-8"))
        rollback_memory(result["snapshot_id"], self.root)
        self.assertEqual((self.root / "memory" / "TASTE.md").read_text(encoding="utf-8"), before_taste)

    def test_memory_requires_existing_evidence(self) -> None:
        with self.assertRaises(FeedLoopError):
            apply_memory(
                {
                    "taste_md": "# Taste\n\nNew",
                    "voice_md": "# Voice\n\nNew",
                    "evidence_card_ids": ["missing"],
                    "rationale": ["Because"],
                },
                self.root,
            )

    def test_preferences_round_trip_and_backup(self) -> None:
        bundle = export_preferences(self.root)
        bundle["preferences_md"] = "# Preferences\n\nFocus on tools.\n"
        result = import_preferences(bundle, self.root)
        self.assertIn("preferences_md", result["changed"])
        self.assertIn("Focus on tools", (self.root / "preferences.md").read_text(encoding="utf-8"))
        self.assertTrue(Path(result["backup"]).exists())

    def test_legacy_migration(self) -> None:
        legacy_temp = tempfile.TemporaryDirectory()
        self.addCleanup(legacy_temp.cleanup)
        legacy = Path(legacy_temp.name)
        (legacy / "memory").mkdir()
        (legacy / ".state").mkdir()
        (legacy / "drafts").mkdir()
        (legacy / "briefs").mkdir()
        (legacy / "sessions").mkdir()
        (legacy / "prompt.md").write_text("# X-LiveCast preferences\n", encoding="utf-8")
        (legacy / "memory" / "USER.md").write_text("# User\n\nLegacy\n", encoding="utf-8")
        (legacy / "memory" / "TASTE.md").write_text("# Taste\n\nLegacy\n", encoding="utf-8")
        (legacy / ".state" / "seen.json").write_text('{"home":["100"]}\n', encoding="utf-8")
        (legacy / "drafts" / "old.json").write_text('{"id":"old"}\n', encoding="utf-8")
        (legacy / "briefs" / "old.json").write_text('{}\n', encoding="utf-8")
        (legacy / "sessions" / "old.json").write_text('{}\n', encoding="utf-8")

        report = migrate_legacy(legacy, self.root)
        self.assertIn("preferences.md", report["migrated"])
        self.assertEqual(report["skipped"]["briefs"], 1)
        self.assertEqual(report["skipped"]["sessions"], 1)
        self.assertTrue((self.root / "drafts" / "old.json").exists())
        self.assertIn("X Feed Loop", (self.root / "preferences.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
