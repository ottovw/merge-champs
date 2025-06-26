#!/usr/bin/env python3
"""
Merge Champ - Main Application
A fun and engaging application to track and visualize merge request stat        # Generate motivational message based on combined stats
        motivational_messages = config.get_motivational_messages()
        total_combined = weekly_stats['total_mrs'] + monthly_stats['total_mrs']
        if total_combined >= 35:
            message = motivational_messages['high_activity'][0]
        elif total_combined >= 15:
            message = motivational_messages['medium_activity'][0]
        else:
            message = motivational_messages['encouraging'][0]e:
    python main.py [--sample]
    
Options:
    --sample        Use sample data for demonstration
"""

import argparse
import sys
import os
import logging
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import config
from src.data_collector import DataCollector
from src.utils import create_sample_data, calculate_team_stats, get_friendly_username, get_week_display_text, get_month_display_text

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
    parser.add_argument('--sample', action='store_true', 
                       help='Use sample data for demonstration')
    args = parser.parse_args()
    
    print("🏆 Welcome to Merge Champ! 🏆")
    print("Generating team merge request statistics...\n")
    
    try:
        if args.sample:
            # Use sample data for demonstration
            print("📊 Using sample data for demonstration...")
            sample_data = create_sample_data()
            weekly_data = sample_data['weekly']
            monthly_data = sample_data['monthly']
        else:
            # Collect real data
            data_collector = DataCollector()
            
            if not data_collector.has_valid_configuration():
                print("⚠️  No valid API configuration found!")
                print("Either configure your API tokens and repository, or use --sample for demo data.")
                print("\nTo configure:")
                print("1. Copy .env.example to .env")
                print("2. Add your API tokens and repository information")
                print("3. List your team members")
                print("\nOr run with --sample to see a demonstration")
                return
            
            print("🔄 Collecting merge request data...")
            weekly_data = data_collector.get_weekly_data()
            monthly_data = data_collector.get_monthly_data()
        
        # Display results in 2-column layout
        COLUMN_WIDTH = 39
        TOTAL_WIDTH = COLUMN_WIDTH * 2 + 1  # +1 for the separator
        
        print("\n" + "=" * TOTAL_WIDTH)
        print("🎉 MERGE CHAMP RESULTS 🎉".center(TOTAL_WIDTH))
        print("=" * TOTAL_WIDTH)
        
        # Create 2-column layout
        weekly_stats = calculate_team_stats(weekly_data)
        monthly_stats = calculate_team_stats(monthly_data)
        
        def format_line(left_text, right_text):
            """Format a line with consistent column widths and separator."""
            left_padded = left_text[:COLUMN_WIDTH].ljust(COLUMN_WIDTH)
            # Add padding to the right column for better visual spacing
            right_padded = (" " + right_text)[:COLUMN_WIDTH].ljust(COLUMN_WIDTH)
            return f"{left_padded}│{right_padded}"
        
        def format_centered_line(left_text, right_text):
            """Format a line with centered text in each column."""
            left_centered = left_text[:COLUMN_WIDTH].center(COLUMN_WIDTH)
            right_centered = right_text[:COLUMN_WIDTH].center(COLUMN_WIDTH)
            return f"{left_centered}│{right_centered}"
        
        def format_full_line(middle_char='┼'):
            """Format a full line with centered headers and separator."""
            return "─" * (COLUMN_WIDTH+1) + middle_char + "─" * COLUMN_WIDTH
        
        # Column headers
        week_header = get_week_display_text()
        month_header = get_month_display_text()
        print(format_centered_line(week_header, month_header))
        print(format_full_line())
        
        # Stats summary
        print(format_centered_line(f"📊 Total MRs: {weekly_stats['total_mrs']}", f"📊 Total MRs: {monthly_stats['total_mrs']}"))
        print(format_centered_line(f"👥 Participation: {weekly_stats['participation_rate']}%", f"👥 Participation: {monthly_stats['participation_rate']}%"))
        
        # Top contributor
        weekly_top = get_friendly_username(weekly_stats['top_contributor'])
        monthly_top = get_friendly_username(monthly_stats['top_contributor'])
        print(format_centered_line(f"🏆 {weekly_top[:30]}", f"🏆 {monthly_top[:30]}"))
        #print(format_centered_line(f"({weekly_stats['top_contributor_count']} MRs)", f"({monthly_stats['top_contributor_count']} MRs)"))
        
        print(format_full_line())
        
        # Team breakdown headers
        print(format_centered_line("👥 TEAM BREAKDOWN", "👥 TEAM BREAKDOWN"))
        print(format_full_line())
        
        # Sort data for both columns
        sorted_weekly = sorted(weekly_data.items(), key=lambda x: x[1], reverse=True)
        sorted_monthly = sorted(monthly_data.items(), key=lambda x: x[1], reverse=True)
        
        # Get emojis for rankings
        emojis = ["🏆", "🥈", "🥉", "⭐", "🌟", "✨", "💫", "🌺", "🎸", "🎪", "🎭", "🎲"]
        
        # Display team breakdown side by side
        max_lines = max(len(sorted_weekly), len(sorted_monthly))
        
        for i in range(max_lines):
            # Weekly column
            if i < len(sorted_weekly):
                username, count = sorted_weekly[i]
                emoji = emojis[i] if i < len(emojis) else "⭐"
                friendly_name = get_friendly_username(username)
                weekly_text = f"{emoji} {friendly_name[:28]}: {count}"
            else:
                weekly_text = ""
            
            # Monthly column  
            if i < len(sorted_monthly):
                username, count = sorted_monthly[i]
                emoji = emojis[i] if i < len(emojis) else "⭐"
                friendly_name = get_friendly_username(username)
                monthly_text = f"{emoji} {friendly_name[:28]}: {count}"
            else:
                monthly_text = ""
            
            print(format_line(weekly_text, monthly_text))
        
        print(format_full_line("┴"))
        
        # Motivational message
        motivational_messages = config.get_motivational_messages()
        if monthly_stats['total_mrs'] >= 20:
            message = motivational_messages['high_activity'][0]
        elif monthly_stats['total_mrs'] >= 5:
            message = motivational_messages['medium_activity'][0]
        else:
            message = motivational_messages['encouraging'][0]
        
        print(f"\n💬 {message}")

        print("\n* These numbers make no judgement on quality. The goal is to")
        print("  encourage working in small batches and frequent contributions.")
        print("  Only MRs from gitlab.com are included and are counted on create.")


    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"\n❌ Error: {e}")
        print("Please check your configuration and try again.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
