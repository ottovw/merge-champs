#!/usr/bin/env python3
"""Quick helper script to run a live Merge Champ smoke test."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Optional

# Ensure project modules are importable when running from scripts directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import config
from src.data_collector import DataCollector
from src.output_channels import TeamsOutputStrategy
from src.utils import (
    MergeCountAggregate,
    calculate_team_stats,
    format_count,
    get_month_date_range,
    get_month_display_text,
    get_week_date_range,
    get_week_display_text,
)

logger = logging.getLogger("merge-champ-smoke")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a live Merge Champ smoke test using the configured GitLab environment."
    )
    parser.add_argument(
        "--week-offset",
        type=int,
        default=0,
        help="Number of weeks to look back (0 = current week).",
    )
    parser.add_argument(
        "--week",
        type=str,
        help="ISO date (YYYY-MM-DD) representing any day within the desired week.",
    )
    parser.add_argument(
        "--month-offset",
        type=int,
        default=0,
        help="Number of months to look back (0 = current month).",
    )
    parser.add_argument(
        "--month",
        type=str,
        help="Target month in YYYY-MM format.",
    )
    parser.add_argument(
        "--send-teams",
        action="store_true",
        help="Send the rendered summary to Microsoft Teams using the configured webhook.",
    )
    parser.add_argument(
        "--weighted",
        action="store_true",
        help="Use weighted merge request counts (defaults to raw).",
    )
    return parser.parse_args()


def _resolve_week(reference: Optional[str], offset: int) -> tuple[datetime, datetime, int, Optional[datetime]]:
    week_reference: Optional[datetime] = None
    week_offset = max(offset, 0)
    if offset < 0:
        logger.warning("Week offset cannot be negative; defaulting to 0")
    if reference:
        try:
            week_reference = datetime.strptime(reference, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Invalid value for --week. Use YYYY-MM-DD format.") from exc
        week_offset = 0
    return get_week_date_range(offset_weeks=week_offset, reference=week_reference) + (week_offset, week_reference)


def _resolve_month(reference: Optional[str], offset: int) -> tuple[datetime, datetime, int, Optional[datetime]]:
    month_reference: Optional[datetime] = None
    month_offset = max(offset, 0)
    if offset < 0:
        logger.warning("Month offset cannot be negative; defaulting to 0")
    if reference:
        try:
            month_reference = datetime.strptime(reference, "%Y-%m")
        except ValueError as exc:
            raise ValueError("Invalid value for --month. Use YYYY-MM format.") from exc
        month_offset = 0
    return (
        *get_month_date_range(offset_months=month_offset, reference=month_reference),
        month_offset,
        month_reference,
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    args = parse_args()

    print("🔍 Running live Merge Champ smoke test...")

    try:
        week_start, week_end, week_offset, week_reference = _resolve_week(args.week, args.week_offset)
        month_start, month_end, month_offset, month_reference = _resolve_month(args.month, args.month_offset)
    except ValueError as exc:
        print(f"❌ {exc}")
        return 1

    collector = DataCollector()
    if not collector.has_valid_configuration():
        print("⚠️  Live smoke test requires valid GitLab credentials and either PROJECT_ID or GROUP_ID.")
        print("Please review your .env configuration and try again.")
        return 1

    print("🔄 Collecting data from GitLab...")
    explicit_week = bool(args.week) or week_offset != 0
    explicit_month = bool(args.month) or month_offset != 0
    month_only = explicit_month and not explicit_week

    count_mode = "weighted" if args.weighted else "raw"
    weighting_enabled = count_mode == "weighted"
    if count_mode == "weighted" and not config.mr_weight_rules:
        logger.info("Weighted count mode selected but MR_WEIGHT_RULES are not configured; values will mirror raw counts.")

    if month_only:
        weekly_aggregate = MergeCountAggregate.empty(config.team_members)
    else:
        weekly_aggregate = collector.get_weekly_data(
            offset_weeks=week_offset,
            reference=week_reference,
            enable_weighting=weighting_enabled,
        )
    monthly_aggregate = collector.get_monthly_data(
        offset_months=month_offset,
        reference=month_reference,
        enable_weighting=weighting_enabled,
    )

    weekly_counts = weekly_aggregate.for_mode(count_mode) if not month_only else {}
    monthly_counts = monthly_aggregate.for_mode(count_mode)

    weekly_stats = calculate_team_stats(weekly_counts)
    monthly_stats = calculate_team_stats(monthly_counts)

    week_header = get_week_display_text(week_start, week_end)
    month_header = get_month_display_text(month_start)

    if not month_only:
        print("\n=== Weekly Summary ===")
        print(week_header)
        print(f"Total MRs: {format_count(weekly_stats['total_mrs'])}")
        print(f"Participation: {weekly_stats['participation_rate']}%")
        print(
            "Top Contributor: "
            f"{weekly_stats['top_contributor']} ({format_count(weekly_stats['top_contributor_count'])} MRs)"
        )
        for username, count in sorted(weekly_counts.items(), key=lambda item: item[1], reverse=True):
            print(f" - {username}: {format_count(count)}")
    else:
        print("\n(Weekly summary omitted: monthly report requested.)")

    print("\n=== Monthly Summary ===")
    print(month_header)
    print(f"Total MRs: {format_count(monthly_stats['total_mrs'])}")
    print(f"Participation: {monthly_stats['participation_rate']}%")
    print(
        "Top Contributor: "
        f"{monthly_stats['top_contributor']} ({format_count(monthly_stats['top_contributor_count'])} MRs)"
    )
    for username, count in sorted(monthly_counts.items(), key=lambda item: item[1], reverse=True):
        print(f" - {username}: {format_count(count)}")

    print(f"\n🧮 Count mode: {count_mode.capitalize()}")
    if count_mode == "weighted" and config.mr_weight_rules:
        rule_summary = ", ".join(f"≤{threshold}:{weight}" for threshold, weight in config.mr_weight_rules)
        print(f"⚖️  Weight rules: {rule_summary}")

    if args.send_teams:
        if not config.ms_teams_webhook_url:
            print("⚠️  Cannot send to Teams: MS_TEAMS_WEBHOOK_URL is not configured.")
        elif not config.enable_teams_notifications:
            print("⚠️  Teams notifications are disabled via ENABLE_TEAMS_NOTIFICATIONS.")
        else:
            print("📤 Sending summary to Microsoft Teams...")
            teams_strategy = TeamsOutputStrategy(config.ms_teams_webhook_url)
            entries_week = sorted(weekly_counts.items(), key=lambda item: item[1], reverse=True) if not month_only else []
            entries_month = sorted(monthly_counts.items(), key=lambda item: item[1], reverse=True)

            motivational_messages = config.get_motivational_messages()
            if monthly_stats['total_mrs'] >= 20:
                motivational_message = motivational_messages['high_activity'][0]
            elif monthly_stats['total_mrs'] >= 5:
                motivational_message = motivational_messages['medium_activity'][0]
            else:
                motivational_message = motivational_messages['encouraging'][0]

            delivered = teams_strategy.send(
                week_header,
                month_header,
                weekly_stats,
                monthly_stats,
                entries_week,
                entries_month,
                motivational_message,
                {
                    "sample_mode": "false",
                    "week_start": week_start.isoformat(),
                    "week_end": week_end.isoformat(),
                    "month_start": month_start.isoformat(),
                    "month_end": month_end.isoformat(),
                    "view_mode": "monthly_only" if month_only else "combined",
                    "count_mode": count_mode,
                    "has_weight_rules": "true" if config.mr_weight_rules else "false",
                },
            )
            if delivered:
                print("✅ Teams notification delivered.")
            else:
                print("⚠️  Failed to deliver to Teams. Check logs for details.")

    print("\n🎉 Smoke test complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
