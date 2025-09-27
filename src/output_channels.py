"""Output strategies for delivering Merge Champ summaries."""

from __future__ import annotations

import logging
from dataclasses import dataclass
import json
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from .utils import RANKING_EMOJIS, get_friendly_username, format_count

logger = logging.getLogger(__name__)


@dataclass
class RankedEntry:
    """Represents a ranked user entry."""

    username: str
    count: float
    emoji: str

    @property
    def friendly_name(self) -> str:
        return get_friendly_username(self.username)


def build_ranked_entries(sorted_data: List[Tuple[str, float]]) -> List[RankedEntry]:
    entries: List[RankedEntry] = []
    for idx, (username, count) in enumerate(sorted_data):
        emoji = RANKING_EMOJIS[idx] if idx < len(RANKING_EMOJIS) else "⭐"
        entries.append(RankedEntry(username=username, count=count, emoji=emoji))
    return entries


class BaseOutputStrategy:
    """Base class for delivery strategies."""

    def render(
        self,
        week_header: str,
        month_header: str,
    weekly_stats: Dict[str, Any],
    monthly_stats: Dict[str, Any],
    weekly_breakdown: List[Tuple[str, float]],
    monthly_breakdown: List[Tuple[str, float]],
        motivational_message: str,
        context: Dict[str, str],
    ) -> str:
        raise NotImplementedError

    def deliver(self, payload: str) -> bool:
        raise NotImplementedError

    def send(
        self,
        week_header: str,
        month_header: str,
    weekly_stats: Dict[str, Any],
    monthly_stats: Dict[str, Any],
    weekly_breakdown: List[Tuple[str, float]],
    monthly_breakdown: List[Tuple[str, float]],
        motivational_message: str,
        context: Dict[str, str],
    ) -> bool:
        payload = self.render(
            week_header,
            month_header,
            weekly_stats,
            monthly_stats,
            weekly_breakdown,
            monthly_breakdown,
            motivational_message,
            context,
        )
        return self.deliver(payload)


class ConsoleOutputStrategy(BaseOutputStrategy):
    """Render summary to the console."""

    def __init__(self, line_writer: Callable[[str], None] | None = None) -> None:
        self._line_writer = line_writer or print

    def _format_month_only(
        self,
        month_header: str,
    monthly_stats: Dict[str, Any],
        monthly_entries: List[RankedEntry],
        context: Dict[str, str],
    ) -> List[str]:
        width = 79

        def divider(char: str = "─") -> str:
            return char * width

        lines: List[str] = []
        lines.append("\n" + divider("="))
        lines.append("🎉 MERGE CHAMP RESULTS 🎉".center(width))
        lines.append(divider("="))
        if context.get("sample_mode") == "true":
            lines.append("📊 Using sample data for demonstration...".center(width))
        lines.append(month_header.center(width))
        lines.append(divider())
        lines.append(f"📊 Total MRs: {format_count(monthly_stats['total_mrs'])}".center(width))
        lines.append(f"👥 Participation: {monthly_stats['participation_rate']}%".center(width))
        month_top = get_friendly_username(monthly_stats['top_contributor']) if monthly_stats['top_contributor'] != 'No data' else 'No data'
        if month_top != 'No data':
            lines.append(f"🏆 {month_top[:45]}".center(width))
        lines.append(divider())
        lines.append("👥 TEAM BREAKDOWN".center(width))
        lines.append(divider())
        if monthly_entries:
            for entry in monthly_entries:
                lines.append(f"{entry.emoji} {entry.friendly_name}: {format_count(entry.count)}".center(width))
        else:
            lines.append("No merge requests recorded.".center(width))
        lines.append(divider())
        return lines

    def _format_columns(
        self,
        week_header: str,
        month_header: str,
    weekly_stats: Dict[str, Any],
    monthly_stats: Dict[str, Any],
        weekly_entries: List[RankedEntry],
        monthly_entries: List[RankedEntry],
    ) -> List[str]:
        column_width = 39
        total_width = column_width * 2 + 1

        def format_line(left: str, right: str) -> str:
            left_padded = left[:column_width].ljust(column_width)
            right_padded = (" " + right)[:column_width].ljust(column_width)
            return f"{left_padded}│{right_padded}"

        def format_centered(left: str, right: str) -> str:
            left_centered = left[:column_width].center(column_width)
            right_centered = right[:column_width].center(column_width)
            return f"{left_centered}│{right_centered}"

        def format_divider(middle: str = "┼") -> str:
            return "─" * (column_width + 1) + middle + "─" * column_width

        lines: List[str] = []
        lines.append("\n" + "=" * total_width)
        lines.append("🎉 MERGE CHAMP RESULTS 🎉".center(total_width))
        lines.append("=" * total_width)
        lines.append(format_centered(week_header, month_header))
        lines.append(format_divider())
        lines.append(
            format_centered(
                f"📊 Total MRs: {format_count(weekly_stats['total_mrs'])}",
                f"📊 Total MRs: {format_count(monthly_stats['total_mrs'])}"
            )
        )
        lines.append(
            format_centered(
                f"👥 Participation: {weekly_stats['participation_rate']}%",
                f"👥 Participation: {monthly_stats['participation_rate']}%"
            )
        )
        week_top = (
            get_friendly_username(weekly_stats['top_contributor'])
            if weekly_stats['top_contributor'] != 'No data'
            else 'No data'
        )
        month_top = (
            get_friendly_username(monthly_stats['top_contributor'])
            if monthly_stats['top_contributor'] != 'No data'
            else 'No data'
        )
        lines.append(format_centered(f"🏆 {week_top[:30]}", f"🏆 {month_top[:30]}"))
        lines.append(format_divider())
        lines.append(format_centered("👥 TEAM BREAKDOWN", "👥 TEAM BREAKDOWN"))
        lines.append(format_divider())

        max_lines = max(len(weekly_entries), len(monthly_entries))
        for idx in range(max_lines):
            weekly_line = (
                f"{weekly_entries[idx].emoji} {weekly_entries[idx].friendly_name[:28]}: {format_count(weekly_entries[idx].count)}"
                if idx < len(weekly_entries)
                else ""
            )
            monthly_line = (
                f"{monthly_entries[idx].emoji} {monthly_entries[idx].friendly_name[:28]}: {format_count(monthly_entries[idx].count)}"
                if idx < len(monthly_entries)
                else ""
            )
            lines.append(format_line(weekly_line, monthly_line))

        lines.append(format_divider("┴"))
        return lines

    def render(
        self,
        week_header: str,
        month_header: str,
    weekly_stats: Dict[str, Any],
    monthly_stats: Dict[str, Any],
    weekly_breakdown: List[Tuple[str, float]],
    monthly_breakdown: List[Tuple[str, float]],
        motivational_message: str,
        context: Dict[str, str],
    ) -> str:
        view_mode = context.get("view_mode", "combined")
        if view_mode == "monthly_only":
            monthly_entries = build_ranked_entries(monthly_breakdown)
            lines = self._format_month_only(
                month_header,
                monthly_stats,
                monthly_entries,
                context,
            )
        else:
            weekly_entries = build_ranked_entries(weekly_breakdown)
            monthly_entries = build_ranked_entries(monthly_breakdown)
            lines = self._format_columns(
                week_header,
                month_header,
                weekly_stats,
                monthly_stats,
                weekly_entries,
                monthly_entries,
            )
        lines.append("\n💬 " + motivational_message)
        lines.append("\n* These numbers make no judgement on quality. The goal is to")
        lines.append("  encourage working in small batches and frequent contributions.")
        lines.append("  Only MRs from gitlab.com are included and are counted on create.")
        if context.get("sample_mode") == "true":
            lines.insert(3, "📊 Using sample data for demonstration...")
        return "\n".join(lines)

    def deliver(self, payload: str) -> bool:
        for line in payload.splitlines():
            self._line_writer(line)
        return True


class TeamsOutputStrategy(BaseOutputStrategy):
    """Send celebratory summaries to Microsoft Teams via webhook."""

    def __init__(self, webhook_url: str, timeout: int = 10, debug_mode: bool = False) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout
        self._last_card_attachment: Optional[Dict[str, Any]] = None
        self._debug_mode = debug_mode
        self._last_request_body: Optional[Dict[str, Any]] = None

    @property
    def last_card_attachment(self) -> Optional[Dict[str, Any]]:
        return self._last_card_attachment

    @property
    def last_request_body(self) -> Optional[Dict[str, Any]]:
        return self._last_request_body

    @staticmethod
    def _build_breakdown_rows(entries: List[RankedEntry]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for entry in entries:
            rows.append(
                {
                    "type": "ColumnSet",
                    "spacing": "Small",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": f"{entry.emoji} {entry.friendly_name}",
                                    "wrap": True,
                                    "maxLines": 1,
                                }
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": format_count(entry.count),
                                    "wrap": False,
                                    "horizontalAlignment": "Right",
                                }
                            ],
                        },
                    ],
                }
            )
        return rows

    def render(
        self,
        week_header: str,
        month_header: str,
    weekly_stats: Dict[str, Any],
    monthly_stats: Dict[str, Any],
    weekly_breakdown: List[Tuple[str, float]],
    monthly_breakdown: List[Tuple[str, float]],
        motivational_message: str,
        context: Dict[str, str],
    ) -> str:
        view_mode = context.get("view_mode", "combined")
        weekly_entries = build_ranked_entries(weekly_breakdown) if view_mode != "monthly_only" else []
        monthly_entries = build_ranked_entries(monthly_breakdown)
        lines: List[str] = ["🎉 **Merge Champ Results** 🎉", ""]

        card_body: List[Dict[str, Any]] = [
            {
                "type": "TextBlock",
                "text": "🎉 Merge Champ Results 🎉",
                "weight": "Bolder",
                "size": "Large",
                "wrap": True,
            }
        ]

        if context.get("sample_mode") == "true":
            lines.extend(["_Sample data mode_", ""])
            card_body.append(
                {
                    "type": "TextBlock",
                    "text": "📊 Using sample data for demonstration",
                    "wrap": True,
                    "isSubtle": True,
                }
            )

        if view_mode != "monthly_only":
            lines.append(f"**{week_header}**")
            lines.append(f"- Total MRs: {format_count(weekly_stats['total_mrs'])}")
            lines.append(f"- Participation: {weekly_stats['participation_rate']}%")
            if weekly_stats['top_contributor'] != 'No data':
                friendly_week_top = get_friendly_username(weekly_stats['top_contributor'])
                lines.append(
                    "- Top Contributor: "
                    f"{friendly_week_top} ({format_count(weekly_stats['top_contributor_count'])} MRs)"
                )
            lines.append("- Team breakdown:")
            lines.extend(
                f"  {entry.emoji} {entry.friendly_name}: {format_count(entry.count)}" if entry.count else f"  {entry.emoji} {entry.friendly_name}: 0"
                for entry in weekly_entries
            )
            if not weekly_entries:
                lines.append("  - No merge requests recorded.")
            lines.append("")

            weekly_items: List[Dict[str, Any]] = [
                {
                    "type": "TextBlock",
                    "text": week_header,
                    "weight": "Bolder",
                    "wrap": True,
                },
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": f"📊 Total MRs: {format_count(weekly_stats['total_mrs'])}",
                                    "wrap": True,
                                    "maxLines": 1,
                                }
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": f"👥 Participation: {weekly_stats['participation_rate']}%",
                                    "wrap": False,
                                    "horizontalAlignment": "Right",
                                    "maxLines": 1,
                                }
                            ],
                        },
                    ],
                },
            ]
            if weekly_stats['top_contributor'] != 'No data':
                friendly_week_top = get_friendly_username(weekly_stats['top_contributor'])
                weekly_items.append(
                    {
                        "type": "TextBlock",
                        "text": f"🏆 Top Contributor: {friendly_week_top} ({format_count(weekly_stats['top_contributor_count'])} MRs)",
                        "wrap": True,
                    }
                )
            if weekly_entries:
                weekly_items.extend(self._build_breakdown_rows(weekly_entries))
            else:
                weekly_items.append(
                    {
                        "type": "TextBlock",
                        "text": "No merge requests recorded.",
                        "wrap": True,
                        "isSubtle": True,
                    }
                )

            card_body.append(
                {
                    "type": "Container",
                    "items": weekly_items,
                    "spacing": "Medium",
                    "style": "emphasis",
                }
            )

        lines.append(f"**{month_header}**")
        lines.append(f"- Total MRs: {format_count(monthly_stats['total_mrs'])}")
        lines.append(f"- Participation: {monthly_stats['participation_rate']}%")
        if monthly_stats['top_contributor'] != 'No data':
            friendly_month_top = get_friendly_username(monthly_stats['top_contributor'])
            lines.append(
                "- Top Contributor: "
                f"{friendly_month_top} ({format_count(monthly_stats['top_contributor_count'])} MRs)"
            )
        lines.append("- Team breakdown:")
        lines.extend(
            f"  {entry.emoji} {entry.friendly_name}: {format_count(entry.count)}" if entry.count else f"  {entry.emoji} {entry.friendly_name}: 0"
            for entry in monthly_entries
        )
        if not monthly_entries:
            lines.append("  - No merge requests recorded.")

        lines.append("")
        lines.append(f"💬 {motivational_message}")

        monthly_items: List[Dict[str, Any]] = [
            {
                "type": "TextBlock",
                "text": month_header,
                "weight": "Bolder",
                "wrap": True,
            },
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": f"📊 Total MRs: {format_count(monthly_stats['total_mrs'])}",
                                "wrap": True,
                                "maxLines": 1,
                            }
                        ],
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": f"👥 Participation: {monthly_stats['participation_rate']}%",
                                "wrap": False,
                                "horizontalAlignment": "Right",
                                "maxLines": 1,
                            }
                        ],
                    },
                ],
            },
        ]
        if monthly_stats['top_contributor'] != 'No data':
            friendly_month_top = get_friendly_username(monthly_stats['top_contributor'])
            monthly_items.append(
                {
                    "type": "TextBlock",
                    "text": f"🏆 Top Contributor: {friendly_month_top} ({format_count(monthly_stats['top_contributor_count'])} MRs)",
                    "wrap": True,
                }
            )
        if monthly_entries:
            monthly_items.extend(self._build_breakdown_rows(monthly_entries))
        else:
            monthly_items.append(
                {
                    "type": "TextBlock",
                    "text": "No merge requests recorded.",
                    "wrap": True,
                    "isSubtle": True,
                }
            )

        card_body.append(
            {
                "type": "Container",
                "items": monthly_items,
                "spacing": "Medium",
                "style": "emphasis",
            }
        )

        card_body.append(
            {
                "type": "TextBlock",
                "text": f"💬 {motivational_message}",
                "wrap": True,
                "separator": True,
            }
        )

        self._last_card_attachment = {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": card_body,
                "msteams": {
                    "width": "Full"
                },
            },
        }

        return "\n".join(lines)

    def _build_request_body(self, payload: str) -> Dict[str, Any]:
        body: Dict[str, Any] = {"text": payload, "type": "message"}
        if self._last_card_attachment:
            body["attachments"] = [self._last_card_attachment]
        return body

    def deliver(self, payload: str) -> bool:
        body = self._build_request_body(payload)
        self._last_request_body = body

        if self._debug_mode:
            print("\n🔍 Teams publish debug mode: request body")
            print(json.dumps(body, indent=2))
            logger.info("Teams publish debug mode active; skipping HTTP POST")
            return True

        if not self.webhook_url:
            logger.debug("Skipping Teams delivery because no webhook URL is configured")
            return False

        try:
            response = requests.post(
                self.webhook_url,
                json=body,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.info("Delivered merge summary to Microsoft Teams")
            return True
        except requests.RequestException as exc:
            logger.error("Failed to post summary to Microsoft Teams: %s", exc)
            return False
