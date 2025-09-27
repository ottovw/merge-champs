"""
Configuration management for Merge Champ application.
Handles environment variables and application settings.
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv, find_dotenv
import logging

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
dotenv_path = find_dotenv(usecwd=True)
if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path, override=True)
    logger.debug("Loaded environment variables from %s", dotenv_path)
else:
    load_dotenv(override=True)
    logger.debug("Loaded environment variables using default search path")


class Config:
    """Configuration class for Merge Champ application."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        # GitLab Configuration
        self.gitlab_token = os.getenv('GITLAB_TOKEN')
        self.gitlab_url = os.getenv('GITLAB_URL', 'https://gitlab.com')

        # Repository Configuration
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

        # Notification Configuration
        self.ms_teams_webhook_url = os.getenv('MS_TEAMS_WEBHOOK_URL')
        teams_flag_raw = os.getenv('ENABLE_TEAMS_NOTIFICATIONS', 'true')
        self.enable_teams_notifications = teams_flag_raw.strip().lower() not in {'false', '0', 'no'}

        # Merge Request Weighting Configuration
        mr_weight_rules_raw = os.getenv('MR_WEIGHT_RULES', '')
        self.mr_weight_rules = self._parse_weight_rules(mr_weight_rules_raw)
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate the configuration and log warnings for missing values."""
        if self.gitlab_token:
            token_value = self.gitlab_token.strip()
            if token_value.lower().startswith("your_gitlab_token"):
                logger.warning("Detected placeholder GitLab token in .env; treating as missing.")
                self.gitlab_token = None

        if self.project_id:
            project_value = self.project_id.strip()
            if project_value.lower().startswith("your_project_id"):
                logger.warning("Detected placeholder project ID in .env; treating as missing.")
                self.project_id = None

        if self.group_id:
            group_value = self.group_id.strip()
            if group_value.lower().startswith("your_group_id"):
                logger.warning("Detected placeholder group ID in .env; treating as missing.")
                self.group_id = None

        normalized_team = [member.lower() for member in self.team_members]
        placeholder_team = ['john.doe', 'jane.smith', 'alice.johnson', 'bob.wilson']

        if not self.gitlab_token:
            logger.warning("No GitLab API token configured. Please set GITLAB_TOKEN")
        
        if not self.team_members:
            logger.warning("No team members configured. Using default example team.")
            self.team_members = ['john.doe', 'jane.smith', 'alice.johnson', 'bob.wilson']
        elif normalized_team == placeholder_team:
            logger.warning("Team members are still set to example placeholders. Update TEAM_MEMBERS for accurate stats.")
        
        if not self.project_id and not self.group_id:
            logger.warning("No GitLab project or group configured. Please set PROJECT_ID or GROUP_ID")
        
        if self.ms_teams_webhook_url and not self.enable_teams_notifications:
            logger.info("MS Teams webhook provided but notifications disabled via ENABLE_TEAMS_NOTIFICATIONS=false")

        logger.info(f"Configured for {len(self.team_members)} team members: {', '.join(self.team_members)}")
    
        if self.mr_weight_rules:
            pretty_rules = ", ".join(f"≤{threshold} -> {weight}" for threshold, weight in self.mr_weight_rules)
            logger.info("Merge request weighting rules active: %s", pretty_rules)
        else:
            logger.info("Merge request weighting rules not configured; raw counts will be used for weighting calculations.")

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

    def _parse_weight_rules(self, rules_str: str) -> List[Tuple[int, float]]:
        """Parse MR weight rules (e.g., "5:0.2,15:0.5") into sorted threshold tuples."""
        parsed_rules: List[Tuple[int, float]] = []
        if not rules_str:
            return parsed_rules

        segments = [segment.strip() for segment in re.split(r'[;,]', rules_str) if segment.strip()]
        for segment in segments:
            if ':' not in segment:
                logger.warning("Ignoring invalid MR weight rule '%s' (missing ':').", segment)
                continue
            threshold_part, weight_part = segment.split(':', 1)
            try:
                threshold = int(threshold_part.strip())
                weight = float(weight_part.strip())
            except ValueError:
                logger.warning("Ignoring invalid MR weight rule '%s' (non-numeric values).", segment)
                continue
            if threshold < 0:
                logger.warning("Ignoring MR weight rule '%s' (negative threshold).", segment)
                continue
            if weight <= 0:
                logger.warning("Ignoring MR weight rule '%s' (non-positive weight).", segment)
                continue
            parsed_rules.append((threshold, weight))

        parsed_rules.sort(key=lambda rule: rule[0])
        return parsed_rules

    def get_weight_for_lines(self, lines_changed: Optional[int]) -> float:
        """Return the weighting factor for a merge request based on lines changed."""
        if not self.mr_weight_rules or lines_changed is None:
            return 1.0

        for threshold, weight in self.mr_weight_rules:
            if lines_changed <= threshold:
                return max(0.0, min(weight, 1.0))

        return 1.0


# Global configuration instance
config = Config()
