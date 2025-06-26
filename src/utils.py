"""
Utility functions for the Merge Champ application.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def get_date_range_last_week() -> tuple[datetime, datetime]:
    """Get the start and end dates for the work week (Saturday to Friday for data, Monday to Friday for display)."""
    today = datetime.now()
    # Calculate days since Monday (0=Monday, 6=Sunday)
    days_since_monday = today.weekday()
    
    # Get the Monday of current week
    monday = today - timedelta(days=days_since_monday)
    
    # For data collection: Start from Saturday (2 days before Monday)
    # This captures weekend work that contributes to the work week
    start_date = datetime(monday.year, monday.month, monday.day) - timedelta(days=2)
    
    # End on Friday of current week (4 days after Monday)
    friday = monday + timedelta(days=4)
    # Set to end of Friday (23:59:59)
    end_date = datetime(friday.year, friday.month, friday.day, 23, 59, 59)
    
    return start_date, end_date


def get_date_range_current_month() -> tuple[datetime, datetime]:
    """Get the start and end dates for the current month."""
    now = datetime.now()
    start_date = datetime(now.year, now.month, 1)
    end_date = now
    return start_date, end_date


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


def calculate_team_stats(merge_data: Dict[str, int]) -> Dict[str, Any]:
    """Calculate team statistics from merge request data."""
    if not merge_data:
        return {
            'total_mrs': 0,
            'top_contributor': 'No data',
            'average_per_member': 0,
            'participation_rate': 0
        }
    
    total_mrs = sum(merge_data.values())
    top_contributor = max(merge_data.items(), key=lambda x: x[1])
    average_per_member = total_mrs / len(merge_data) if merge_data else 0
    
    # Calculate participation rate (members with at least 1 MR)
    active_members = sum(1 for count in merge_data.values() if count > 0)
    participation_rate = (active_members / len(merge_data)) * 100 if merge_data else 0
    
    return {
        'total_mrs': total_mrs,
        'top_contributor': top_contributor[0],
        'top_contributor_count': top_contributor[1],
        'average_per_member': round(average_per_member, 1),
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
    lines.append(f"   Total MRs: {stats['total_mrs']}")
    lines.append(f"   Top Contributor: {get_friendly_username(stats['top_contributor'])} ({stats['top_contributor_count']} MRs)")
    lines.append(f"   Team Participation: {stats['participation_rate']}%")
    
    return "\n".join(lines)


def create_sample_data() -> Dict[str, Dict[str, int]]:
    """Create sample data for demonstration purposes."""
    from .config import config
    team_members = config.team_members if config.team_members else ['john.doe', 'jane.smith', 'alice.johnson', 'bob.wilson']
    
    # Generate realistic sample data
    weekly_data = {}
    monthly_data = {}
    
    for member in team_members:
        # Weekly data (0-8 MRs per week)
        weekly_data[member] = random.randint(0, 8)
        # Monthly data (weekly * 3-5 for realistic monthly totals)
        monthly_data[member] = weekly_data[member] * random.randint(3, 5)
    
    logger.info(f"Generated sample data for demonstration with team: {', '.join(team_members)}")
    return {
        'weekly': weekly_data,
        'monthly': monthly_data
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


def get_week_display_text() -> str:
    """Get a formatted display text for the work week (Monday to Friday)."""
    today = datetime.now()
    # Calculate days since Monday (0=Monday, 6=Sunday)
    days_since_monday = today.weekday()
    
    # Get the Monday of current week for display
    monday = today - timedelta(days=days_since_monday)
    # Get the Friday of current week for display
    friday = monday + timedelta(days=4)
    
    return f"📅 WORK WEEK ({monday.strftime('%b %d')} - {friday.strftime('%b %d')})"


def get_month_display_text() -> str:
    """Get a formatted display text for the current month."""
    now = datetime.now()
    return f"🗓️  THIS MONTH ({now.strftime('%B %Y')})"
