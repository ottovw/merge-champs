"""Utility functions for the Merge Champ application."""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

RANKING_EMOJIS = ["🏆", "🥈", "🥉", "⭐", "🌟", "✨", "💫", "🌺", "🎸", "🎪", "🎭", "🎲"]
SAMPLE_TEAM_MEMBERS = [
    "luna.codes",
    "kai.tests",
    "nova.ops",
    "arya.data",
]


@dataclass
class MergeCountAggregate:
    """Stores raw and weighted merge request counts for a period."""

    raw: Dict[str, float]
    weighted: Dict[str, float]

    @classmethod
    def empty(cls, team_members: List[str]) -> "MergeCountAggregate":
        zero_map = {member: 0.0 for member in team_members}
        return cls(raw=dict(zero_map), weighted=dict(zero_map))

    def ensure_members(self, team_members: List[str]) -> "MergeCountAggregate":
        for member in team_members:
            self.raw.setdefault(member, 0.0)
            self.weighted.setdefault(member, 0.0)
        return self

    def for_mode(self, mode: str) -> Dict[str, float]:
        return self.weighted if mode == "weighted" else self.raw

    def round_weighted(self, digits: int = 2) -> None:
        for member, value in list(self.weighted.items()):
            self.weighted[member] = round(value, digits)


def format_count(value: float | int) -> str:
    """Format merge request counts, trimming trailing zeros for whole numbers."""
    if isinstance(value, (int, float)) and float(value).is_integer():
        return f"{int(value)}"
    return f"{float(value):.2f}".rstrip("0").rstrip(".")


def _normalize_start_of_day(date_value: datetime) -> datetime:
    """Return a datetime stripped to the start of the day (00:00:00)."""
    return datetime(date_value.year, date_value.month, date_value.day)


def _normalize_end_of_day(date_value: datetime) -> datetime:
    """Return a datetime set to the end of day (23:59:59)."""
    start = _normalize_start_of_day(date_value)
    return start + timedelta(hours=23, minutes=59, seconds=59)


def get_week_date_range(offset_weeks: int = 0, reference: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Return the Monday-Sunday window for the given offset from the reference week.

    Args:
        offset_weeks: Number of weeks in the past (0 = current week, 1 = previous week, etc.).
        reference: Optional datetime to use as the anchor; defaults to now.
    """
    if offset_weeks < 0:
        raise ValueError("offset_weeks must be zero or a positive integer")

    anchor = reference or datetime.now()
    anchor_start = _normalize_start_of_day(anchor)
    days_since_monday = anchor_start.weekday()
    current_monday = anchor_start - timedelta(days=days_since_monday)
    target_monday = current_monday - timedelta(weeks=offset_weeks)
    start_date = _normalize_start_of_day(target_monday)
    end_date = start_date + timedelta(days=6)
    end_date = _normalize_end_of_day(end_date)
    return start_date, end_date


def _shift_month(base: datetime, months: int) -> datetime:
    """Shift a datetime representing the first day of a month by a number of months."""
    year = base.year + (base.month - 1 + months) // 12
    month = (base.month - 1 + months) % 12 + 1
    return datetime(year, month, 1)


def get_month_date_range(offset_months: int = 0, reference: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Return the first-to-last day window for the requested month.

    Args:
        offset_months: Number of months in the past (0 = current month, 1 = previous month, etc.).
        reference: Optional datetime used to determine the base month; defaults to now.
    """
    if offset_months < 0:
        raise ValueError("offset_months must be zero or a positive integer")

    anchor = reference or datetime.now()
    current_month_start = datetime(anchor.year, anchor.month, 1)
    target_month_start = _shift_month(current_month_start, -offset_months)
    next_month_start = _shift_month(target_month_start, 1)
    end_date = next_month_start - timedelta(seconds=1)
    return target_month_start, end_date


def get_random_motivational_message(messages: List[str]) -> str:
    """Get a random motivational message from a list."""
    return random.choice(messages) if messages else "🎉 Great work team!"


def format_merge_request_data(data: List[Dict[str, Any]]) -> Dict[str, int]:
    """Format merge request data for visualization."""
    formatted_data = {}
    for item in data:
        author = item.get('author', 'Unknown')
        if author in formatted_data:
            formatted_data[author] += 1
        else:
            formatted_data[author] = 1
    return formatted_data


def calculate_team_stats(merge_data: Dict[str, float]) -> Dict[str, Any]:
    """Calculate team statistics from merge request data."""
    if not merge_data:
        return {
            'total_mrs': 0,
            'top_contributor': 'No data',
            'top_contributor_count': 0,
            'average_per_member': 0,
            'participation_rate': 0
        }
    
    total_mrs = sum(merge_data.values())
    top_contributor = max(merge_data.items(), key=lambda x: x[1]) if merge_data else ("No data", 0)
    average_per_member = total_mrs / len(merge_data) if merge_data else 0
    
    # Calculate participation rate (members with at least 1 MR)
    active_members = sum(1 for count in merge_data.values() if count > 0)
    participation_rate = (active_members / len(merge_data)) * 100 if merge_data else 0
    
    return {
        'total_mrs': round(total_mrs, 2),
        'top_contributor': top_contributor[0],
        'top_contributor_count': round(top_contributor[1], 2),
        'average_per_member': round(average_per_member, 2),
        'participation_rate': round(participation_rate, 1),
        'active_members': active_members
    }


def get_chart_title(period: str, stats: Dict[str, Any]) -> str:
    """Generate an engaging title based on the period and stats."""
    period_text = "This Week" if period == "week" else "This Month"
    
    if stats['total_mrs'] == 0:
        return f"🌱 {period_text}'s Merge Requests - Let's Get Started!"
    elif stats['total_mrs'] >= 20:
        return f"🚀 {period_text}'s Merge Champions - {stats['total_mrs']} MRs!"
    elif stats['total_mrs'] >= 10:
        return f"💪 {period_text}'s Strong Performance - {stats['total_mrs']} MRs!"
    else:
        return f"📈 {period_text}'s Progress - {stats['total_mrs']} MRs!"


def get_display_message(period: str, stats: Dict[str, Any]) -> str:
    """Generate a display message for terminal output."""
    title = get_chart_title(period, stats)
    
    if stats['total_mrs'] == 0:
        return f"{title}\n   No merge requests found for this period."
    
    lines = [title]
    lines.append(f"   Total MRs: {format_count(stats['total_mrs'])}")
    lines.append(
        "   Top Contributor: "
        f"{get_friendly_username(stats['top_contributor'])} "
        f"({format_count(stats['top_contributor_count'])} MRs)"
    )
    lines.append(f"   Team Participation: {stats['participation_rate']}%")
    
    return "\n".join(lines)


def create_sample_data(
    seed: Optional[int] = None,
    team_members: Optional[List[str]] = None,
) -> Dict[str, MergeCountAggregate]:
    """Create sample data for demonstration purposes.

    A deterministic seed can be provided to keep results stable across runs
    for the same selected reporting windows.
    """

    from .config import config

    effective_members = team_members or SAMPLE_TEAM_MEMBERS

    rng = random.Random(seed) if seed is not None else random

    weekly_raw: Dict[str, float] = {}
    weekly_weighted: Dict[str, float] = {}
    monthly_raw: Dict[str, float] = {}
    monthly_weighted: Dict[str, float] = {}

    for member in effective_members:
        weekly_count = rng.randint(0, 8)
        weekly_raw[member] = float(weekly_count)
        weighted_week = 0.0
        for _ in range(weekly_count):
            simulated_lines = rng.randint(1, 120)
            weighted_week += config.get_weight_for_lines(simulated_lines)
        weekly_weighted[member] = round(weighted_week, 2)

        monthly_multiplier = rng.randint(3, 5)
        monthly_count = weekly_count * monthly_multiplier
        monthly_raw[member] = float(monthly_count)
        weighted_month = 0.0
        for _ in range(monthly_count):
            simulated_lines = rng.randint(1, 160)
            weighted_month += config.get_weight_for_lines(simulated_lines)
        monthly_weighted[member] = round(weighted_month, 2)

    logger.info(
        "Generated sample data for demonstration with team: %s",
        ', '.join(effective_members),
    )

    return {
        'weekly': MergeCountAggregate(raw=weekly_raw, weighted=weekly_weighted),
        'monthly': MergeCountAggregate(raw=monthly_raw, weighted=monthly_weighted),
    }


def ensure_output_directory(output_path: str) -> None:
    """Ensure the output directory exists (kept for compatibility)."""
    import os
    os.makedirs(output_path, exist_ok=True)
    logger.info(f"Output directory ensured: {output_path}")


def get_friendly_username(username: str) -> str:
    """Convert username to a more friendly display format."""
    # Replace dots and underscores with spaces and title case
    friendly = username.replace('.', ' ').replace('_', ' ').title()
    return friendly


def get_week_display_text(start_date: datetime, end_date: datetime) -> str:
    """Create a friendly label for a Monday-Sunday window."""
    same_year = start_date.year == end_date.year
    start_format = start_date.strftime('%b %d') if same_year else start_date.strftime('%b %d, %Y')
    end_format = end_date.strftime('%b %d, %Y')
    return f"📅 WEEK ({start_format} - {end_format})"


def get_month_display_text(start_date: datetime) -> str:
    """Create a friendly label for the month represented by start_date."""
    return f"🗓️  {start_date.strftime('%B %Y')}"
