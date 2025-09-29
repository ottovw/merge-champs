#!/usr/bin/env python3
"""
Merge Champ - Main Application
A fun and engaging application to track and visualize merge request statistics.

Usage:
    python main.py [--sample]

Options:
    --sample        Use sample data for demonstration
"""

import argparse
import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import config
from src.data_collector import DataCollector
from src.output_channels import ConsoleOutputStrategy, TeamsOutputStrategy
from src.utils import (
    create_sample_data,
    calculate_team_stats,
    get_week_display_text,
    get_month_display_text,
    get_week_date_range,
    get_month_date_range,
    MergeCountAggregate,
    SAMPLE_TEAM_MEMBERS,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main application entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Merge Champ - Track team merge request statistics')
    parser.add_argument(
        '--sample',
        action='store_true',
        help='Use sample data for demonstration'
    )
    parser.add_argument(
        '--week-offset',
        type=int,
        default=None,
        help='Number of weeks to look back (0 = current week). Ignored if --week is provided.'
    )
    parser.add_argument(
        '--week',
        type=str,
        help='ISO date (YYYY-MM-DD) representing any day within the desired week.'
    )
    parser.add_argument(
        '--month-offset',
        type=int,
        default=None,
        help='Number of months to look back (0 = current month). Ignored if --month is provided.'
    )
    parser.add_argument(
        '--month',
        type=str,
        help='Target month in YYYY-MM format.'
    )
    parser.add_argument(
        '--publish-teams',
        action='store_true',
        help='Send the summary to Microsoft Teams when configured.'
    )
    parser.add_argument(
        '--publish-teams-debug',
        action='store_true',
        help='Print the Microsoft Teams request body instead of sending it.'
    )
    parser.add_argument(
        '--weighted',
        action='store_true',
        help='Use weighted merge request counts (defaults to raw).'
    )
    args = parser.parse_args()
    
    print("🏆 Welcome to Merge Champ! 🏆")
    print("Generating team merge request statistics...\n")
    
    try:
        # Determine reporting windows
        week_reference: Optional[datetime] = None
        week_offset_provided = args.week_offset is not None
        week_offset = args.week_offset if week_offset_provided else 0
        if week_offset < 0:
            logger.warning("Week offset cannot be negative; defaulting to 0")
            week_offset = 0
        if args.week and week_offset_provided:
            logger.info("Ignoring --week-offset because --week was provided")

        if args.week:
            try:
                week_reference = datetime.strptime(args.week, "%Y-%m-%d")
            except ValueError:
                print("❌ Invalid value for --week. Use YYYY-MM-DD format.")
                return 1
            week_offset = 0

        month_reference: Optional[datetime] = None
        month_offset_provided = args.month_offset is not None
        month_offset = args.month_offset if month_offset_provided else 0
        if month_offset < 0:
            logger.warning("Month offset cannot be negative; defaulting to 0")
            month_offset = 0
        if args.month and month_offset_provided:
            logger.info("Ignoring --month-offset because --month was provided")

        if args.month:
            try:
                month_reference = datetime.strptime(args.month, "%Y-%m")
            except ValueError:
                print("❌ Invalid value for --month. Use YYYY-MM format.")
                return 1
            month_offset = 0

        week_start, week_end = get_week_date_range(offset_weeks=week_offset, reference=week_reference)
        month_start, month_end = get_month_date_range(offset_months=month_offset, reference=month_reference)
        explicit_week = bool(args.week) or week_offset_provided
        explicit_month = bool(args.month) or month_offset_provided
        month_only = explicit_month and not explicit_week

        count_mode = 'weighted' if args.weighted else 'raw'
        if count_mode == 'weighted' and not config.mr_weight_rules:
            logger.info("Weighted count mode selected but no MR_WEIGHT_RULES configured; values will mirror raw counts.")
            count_mode = 'raw'
        weighting_enabled = count_mode == 'weighted'

        if config.mr_weight_rules:
            rule_summary = ", ".join(f"≤{threshold}:{weight}" for threshold, weight in config.mr_weight_rules)
        else:
            rule_summary = "none configured"
        logger.info("Using %s merge request counts (weight rules: %s)", count_mode, rule_summary)

        if args.sample:
            # Use sample data for demonstration
            week_seed_component = int(week_start.strftime('%Y%W'))
            month_seed_component = int(month_start.strftime('%Y%m'))
            sample_seed = week_seed_component * 1000 + month_seed_component
            logger.info("Generating sample data for demonstration with seed %s", sample_seed)
            sample_team_members = SAMPLE_TEAM_MEMBERS
            sample_data = create_sample_data(seed=sample_seed, team_members=sample_team_members)
            if month_only:
                weekly_aggregate = MergeCountAggregate.empty(sample_team_members)
            else:
                weekly_aggregate = sample_data['weekly'].ensure_members(sample_team_members)
            monthly_aggregate = sample_data['monthly'].ensure_members(sample_team_members)
        else:
            # Collect real data
            data_collector = DataCollector()
            
            if not data_collector.has_valid_configuration():
                print("⚠️  No valid API configuration found!")
                print("Either configure your GitLab token and project/group, or use --sample for demo data.")
                print("\nTo configure:")
                print("1. Copy .env.example to .env")
                print("2. Add your GitLab token and project/group information")
                print("3. List your team members")
                print("\nOr run with --sample to see a demonstration")
                return 1
            
            print("🔄 Collecting merge request data...")
            if month_only:
                weekly_aggregate = MergeCountAggregate.empty(config.team_members)
            else:
                weekly_aggregate = data_collector.get_weekly_data(
                    offset_weeks=week_offset,
                    reference=week_reference,
                    enable_weighting=weighting_enabled,
                )
            monthly_aggregate = data_collector.get_monthly_data(
                offset_months=month_offset,
                reference=month_reference,
                enable_weighting=weighting_enabled,
            )

        if month_only:
            weekly_counts = {}
            weekly_stats = calculate_team_stats(weekly_counts)
            sorted_weekly = []
        else:
            weekly_counts = weekly_aggregate.for_mode(count_mode)
            weekly_stats = calculate_team_stats(weekly_counts)
            sorted_weekly = sorted(weekly_counts.items(), key=lambda x: x[1], reverse=True)
        monthly_counts = monthly_aggregate.for_mode(count_mode)
        monthly_stats = calculate_team_stats(monthly_counts)
        sorted_monthly = sorted(monthly_counts.items(), key=lambda x: x[1], reverse=True)

        motivational_messages = config.get_motivational_messages()
        if monthly_stats['total_mrs'] >= 20:
            motivational_message = motivational_messages['high_activity'][0]
        elif monthly_stats['total_mrs'] >= 5:
            motivational_message = motivational_messages['medium_activity'][0]
        else:
            motivational_message = motivational_messages['encouraging'][0]

        week_header = get_week_display_text(week_start, week_end)
        month_header = get_month_display_text(month_start)

        context = {
            "sample_mode": "true" if args.sample else "false",
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "month_start": month_start.isoformat(),
            "month_end": month_end.isoformat(),
            "view_mode": "monthly_only" if month_only else "combined",
            "count_mode": count_mode,
            "has_weight_rules": "true" if config.mr_weight_rules else "false",
        }

        console_strategy = ConsoleOutputStrategy()
        console_strategy.send(
            week_header,
            month_header,
            weekly_stats,
            monthly_stats,
            sorted_weekly,
            sorted_monthly,
            motivational_message,
            context,
        )

        teams_notifications_enabled = bool(config.ms_teams_webhook_url) and config.enable_teams_notifications
        publish_debug = args.publish_teams_debug
        should_send_to_teams = teams_notifications_enabled and args.publish_teams

        if publish_debug or should_send_to_teams or args.publish_teams:
            webhook_url = config.ms_teams_webhook_url if teams_notifications_enabled else ""
            if args.publish_teams and not teams_notifications_enabled:
                raise RuntimeError("Teams publishing requested but webhook is not configured or notifications are disabled.")

            teams_strategy = TeamsOutputStrategy(webhook_url, debug_mode=publish_debug)
            delivered = teams_strategy.send(
                week_header,
                month_header,
                weekly_stats,
                monthly_stats,
                sorted_weekly,
                sorted_monthly,
                motivational_message,
                context,
            )

            if publish_debug:
                if delivered:
                    print("\n🧪 Teams publish debug mode enabled; request body printed above.")
                else:
                    raise RuntimeError("Teams publish debug mode failed to generate payload.")
            elif should_send_to_teams:
                if delivered:
                    print("\n📤 Shared summary with Microsoft Teams.")
                else:
                    raise RuntimeError("Failed to share summary with Microsoft Teams.")
        elif config.ms_teams_webhook_url and not args.publish_teams:
            print("\nℹ️ Teams notification not sent. Re-run with --publish-teams to share it.")


    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"\n❌ Error: {e}")
        print("Please check your configuration and try again.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
