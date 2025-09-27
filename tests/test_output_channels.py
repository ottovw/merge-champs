import io
import unittest
from contextlib import redirect_stdout
from typing import Dict, List, Tuple

from src.output_channels import ConsoleOutputStrategy, TeamsOutputStrategy


class OutputStrategyRenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.week_header = "📅 WEEK (Sep 01 - Sep 07, 2025)"
        self.month_header = "🗓️  September 2025"
        self.weekly_stats: Dict[str, int | float | str] = {
            "total_mrs": 5,
            "top_contributor": "alice.smith",
            "top_contributor_count": 3,
            "participation_rate": 60.0,
            "average_per_member": 2.5,
        }
        self.monthly_stats: Dict[str, int | float | str] = {
            "total_mrs": 20,
            "top_contributor": "bob.jones",
            "top_contributor_count": 7,
            "participation_rate": 80.0,
            "average_per_member": 5.0,
        }
        self.weekly_breakdown: List[Tuple[str, int]] = [
            ("alice.smith", 3),
            ("bob.jones", 2),
        ]
        self.monthly_breakdown: List[Tuple[str, int]] = [
            ("bob.jones", 7),
            ("alice.smith", 5),
            ("carol", 3),
        ]
        self.context = {
            "sample_mode": "true",
            "view_mode": "combined",
            "count_mode": "raw",
            "has_weight_rules": "false",
        }
        self.motivational_message = "Keep shipping those delightful MRs!"

    def test_console_strategy_render_outputs_two_column_layout(self) -> None:
        strategy = ConsoleOutputStrategy()

        payload = strategy.render(
            self.week_header,
            self.month_header,
            self.weekly_stats,  # type: ignore[arg-type]
            self.monthly_stats,  # type: ignore[arg-type]
            self.weekly_breakdown,
            self.monthly_breakdown,
            self.motivational_message,
            self.context,
        )

        self.assertIn("🎉 MERGE CHAMP RESULTS 🎉", payload)
        self.assertIn("📊 Using sample data for demonstration", payload)
        self.assertIn("🏆 Alice Smith", payload)
        self.assertIn("🥈 Bob Jones", payload)
        self.assertNotIn("🧮 Count mode", payload)
        self.assertNotIn("⚖️ Weighted merge scoring enabled", payload)
        self.assertIn("💬 Keep shipping those delightful MRs!", payload)

    def test_teams_strategy_render_formats_markdown_payload(self) -> None:
        strategy = TeamsOutputStrategy(webhook_url="https://example.com/webhook")

        payload = strategy.render(
            self.week_header,
            self.month_header,
            self.weekly_stats,  # type: ignore[arg-type]
            self.monthly_stats,  # type: ignore[arg-type]
            self.weekly_breakdown,
            self.monthly_breakdown,
            self.motivational_message,
            self.context,
        )

        self.assertIn("🎉 **Merge Champ Results** 🎉", payload)
        self.assertIn("_Sample data mode_", payload)
        self.assertIn("**📅 WEEK (Sep 01 - Sep 07, 2025)**", payload)
        self.assertIn("Top Contributor: Alice Smith (3 MRs)", payload)
        self.assertIn("Top Contributor: Bob Jones (7 MRs)", payload)
        self.assertNotIn("Count mode", payload)
        self.assertNotIn("⚖️ Weighted merge scoring enabled", payload)
        self.assertIn("💬 Keep shipping those delightful MRs!", payload)

        attachment = strategy.last_card_attachment
        self.assertIsNotNone(attachment)
        assert attachment is not None  # narrow type for type checkers
        self.assertEqual(attachment.get("contentType"), "application/vnd.microsoft.card.adaptive")
        content = attachment.get("content", {})
        self.assertEqual(content.get("type"), "AdaptiveCard")
        self.assertEqual(content.get("version"), "1.4")
        body = content.get("body", [])
        self.assertTrue(any(
            isinstance(item, dict)
            and item.get("type") == "TextBlock"
            and isinstance(item.get("text"), str)
            and "Merge Champ Results" in item["text"]
            for item in body
        ))

    def test_console_strategy_month_only_renders_single_column(self) -> None:
        strategy = ConsoleOutputStrategy()
        context = {
            "sample_mode": "false",
            "view_mode": "monthly_only",
            "count_mode": "raw",
            "has_weight_rules": "false",
        }

        payload = strategy.render(
            self.week_header,
            self.month_header,
            self.weekly_stats,  # type: ignore[arg-type]
            self.monthly_stats,  # type: ignore[arg-type]
            self.weekly_breakdown,
            self.monthly_breakdown,
            self.motivational_message,
            context,
        )

        self.assertNotIn("📅 WEEK", payload)
        self.assertIn("🗓️  September 2025", payload)
        self.assertIn("Bob Jones: 7", payload)
        self.assertNotIn("🧮 Count mode", payload)
        self.assertNotIn("⚖️ Weighted merge scoring enabled", payload)

    def test_teams_strategy_month_only_skips_week_section(self) -> None:
        strategy = TeamsOutputStrategy(webhook_url="https://example.com/webhook")
        context = {
            "sample_mode": "false",
            "view_mode": "monthly_only",
            "count_mode": "raw",
            "has_weight_rules": "false",
        }

        payload = strategy.render(
            self.week_header,
            self.month_header,
            self.weekly_stats,  # type: ignore[arg-type]
            self.monthly_stats,  # type: ignore[arg-type]
            self.weekly_breakdown,
            self.monthly_breakdown,
            self.motivational_message,
            context,
        )

        self.assertNotIn("**📅 WEEK", payload)
        self.assertIn("**🗓️  September 2025**", payload)
        self.assertIn("Top Contributor: Bob Jones (7 MRs)", payload)
        self.assertNotIn("Count mode", payload)
        self.assertNotIn("⚖️ Weighted merge scoring enabled", payload)

        attachment = strategy.last_card_attachment
        self.assertIsNotNone(attachment)
        assert attachment is not None
        content = attachment.get("content", {})
        body = content.get("body", [])

        text_elements: List[str] = []
        for element in body:
            if isinstance(element, dict):
                if isinstance(element.get("text"), str):
                    text_elements.append(element["text"])
                for sub_item in element.get("items", []) if isinstance(element.get("items"), list) else []:
                    if isinstance(sub_item, dict) and isinstance(sub_item.get("text"), str):
                        text_elements.append(sub_item["text"])

        self.assertIn(self.month_header, text_elements)
        self.assertTrue(any("💬" in text for text in text_elements))
        self.assertFalse(any("⚖️" in text for text in text_elements))

    def test_console_strategy_weighted_mode_omits_count_mode(self) -> None:
        strategy = ConsoleOutputStrategy()
        weighted_context = {
            **self.context,
            "count_mode": "weighted",
            "has_weight_rules": "true",
        }

        payload = strategy.render(
            self.week_header,
            self.month_header,
            self.weekly_stats,  # type: ignore[arg-type]
            self.monthly_stats,  # type: ignore[arg-type]
            self.weekly_breakdown,
            self.monthly_breakdown,
            self.motivational_message,
            weighted_context,
        )

        self.assertNotIn("Count mode", payload)
        self.assertNotIn("⚖️ Weighted merge scoring enabled using configured thresholds.", payload)

    def test_teams_strategy_weighted_mode_omits_count_mode(self) -> None:
        strategy = TeamsOutputStrategy(webhook_url="https://example.com/webhook")
        weighted_context = {
            **self.context,
            "count_mode": "weighted",
            "has_weight_rules": "true",
        }

        payload = strategy.render(
            self.week_header,
            self.month_header,
            self.weekly_stats,  # type: ignore[arg-type]
            self.monthly_stats,  # type: ignore[arg-type]
            self.weekly_breakdown,
            self.monthly_breakdown,
            self.motivational_message,
            weighted_context,
        )

        self.assertNotIn("Count mode", payload)
        self.assertNotIn("⚖️ Weighted merge scoring enabled using configured thresholds.", payload)
        attachment = strategy.last_card_attachment
        self.assertIsNotNone(attachment)
        assert attachment is not None
        content = attachment.get("content", {})
        body = content.get("body", [])
        self.assertFalse(any(
            isinstance(item, dict)
            and isinstance(item.get("text"), str)
            and "⚖️ Weighted merge scoring enabled using configured thresholds." in item["text"]
            for item in body
        ))

    def test_teams_strategy_debug_mode_prints_request_body(self) -> None:
        strategy = TeamsOutputStrategy(webhook_url="", debug_mode=True)
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            result = strategy.send(
                self.week_header,
                self.month_header,
                self.weekly_stats,  # type: ignore[arg-type]
                self.monthly_stats,  # type: ignore[arg-type]
                self.weekly_breakdown,
                self.monthly_breakdown,
                self.motivational_message,
                self.context,
            )

        self.assertTrue(result)
        output = buffer.getvalue()
        self.assertIn("Teams publish debug mode", output)

        request_body = strategy.last_request_body
        self.assertIsNotNone(request_body)
        assert request_body is not None
        self.assertEqual(request_body["type"], "message")
        self.assertIn("attachments", request_body)
        self.assertTrue(isinstance(request_body["attachments"], list))


if __name__ == "__main__":
    unittest.main()
