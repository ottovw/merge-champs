"""
Configuration management for Merge Champ application.
Handles environment variables and application settings.
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration class for Merge Champ application."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # GitLab Configuration
        self.gitlab_token = os.getenv('GITLAB_TOKEN')
        self.gitlab_url = os.getenv('GITLAB_URL', 'https://gitlab.com')
        
        # GitHub Configuration
        self.github_token = os.getenv('GITHUB_TOKEN')
        
        # Repository Configuration
        self.repository_url = os.getenv('REPOSITORY_URL')
        self.project_id = os.getenv('PROJECT_ID')
        self.group_id = os.getenv('GROUP_ID')
        
        # Team Configuration
        team_members_str = os.getenv('TEAM_MEMBERS', '')
        self.team_members = [member.strip() for member in team_members_str.split(',') if member.strip()]
        
        # Output Configuration
        self.output_dir = os.getenv('OUTPUT_DIR', 'output')
        
        # Display Configuration
        self.display_config = {
            'friendly_emojis': ['🏆', '🥈', '🥉', '⭐', '🎯', '💪', '🚀', '⚡'],
            'motivational_colors': True
        }
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate the configuration and log warnings for missing values."""
        if not self.gitlab_token and not self.github_token:
            logger.warning("No API tokens configured. Please set GITLAB_TOKEN or GITHUB_TOKEN")
        
        if not self.team_members:
            logger.warning("No team members configured. Using default example team.")
            self.team_members = ['john.doe', 'jane.smith', 'alice.johnson', 'bob.wilson']
        
        if not self.repository_url and not self.project_id and not self.group_id:
            logger.warning("No repository/project/group configured. Please set REPOSITORY_URL, PROJECT_ID, or GROUP_ID")
        
        logger.info(f"Configured for {len(self.team_members)} team members: {', '.join(self.team_members)}")
    
    def get_motivational_messages(self) -> Dict[str, List[str]]:
        """Return motivational messages for different scenarios."""
        return {
            'high_activity': [
                "🚀 Amazing work this week!",
                "🔥 The team is on fire!",
                "⚡ Incredible productivity!",
                "🏆 Champions at work!"
            ],
            'medium_activity': [
                "📈 Great progress everyone!",
                "💪 Keep up the good work!",
                "🎯 Team is hitting their stride!",
                "✨ Solid contributions!"
            ],
            'encouraging': [
                "🌟 Every contribution matters!",
                "👥 Together we build great things!",
                "🎉 Celebrating our team's efforts!",
                "💝 Teamwork makes the dream work!"
            ]
        }


# Global configuration instance
config = Config()
