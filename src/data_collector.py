"""
Data collection module for Merge Champ application.
Handles fetching merge request data from GitLab and GitHub APIs.
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from .config import config
from .utils import get_date_range_last_week, get_date_range_current_month

logger = logging.getLogger(__name__)


class GitLabDataCollector:
    """Collects merge request data from GitLab API."""
    
    def __init__(self, token: str, gitlab_url: str = "https://gitlab.com"):
        """Initialize GitLab data collector."""
        self.token = token
        self.gitlab_url = gitlab_url.rstrip('/')
        self.headers = {'Authorization': f'Bearer {token}'}
    
    def get_merge_requests(self, project_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch merge requests for a project within a date range."""
        try:
            url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests"
            params = {
                'state': 'merged',
                'created_after': start_date.isoformat(),
                'created_before': end_date.isoformat(),
                'per_page': 100
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            merge_requests = response.json()
            
            # Filter by team members and format data
            filtered_mrs = []
            for mr in merge_requests:
                author_username = mr.get('author', {}).get('username', '')
                if author_username in config.team_members:
                    filtered_mrs.append({
                        'author': author_username,
                        'title': mr.get('title', ''),
                        'created_at': mr.get('created_at', ''),
                        'merged_at': mr.get('merged_at', ''),
                        'web_url': mr.get('web_url', '')
                    })
            
            logger.info(f"Fetched {len(filtered_mrs)} merge requests from GitLab project {project_id}")
            return filtered_mrs
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching GitLab project data: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []

    def get_group_merge_requests(self, group_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch merge requests for all projects in a group within a date range using group-level API."""
        try:
            # Use the group-level merge requests API endpoint
            url = f"{self.gitlab_url}/api/v4/groups/{group_id}/merge_requests"
            params = {
                'state': 'merged',
                'created_after': start_date.isoformat(),
                'created_before': end_date.isoformat(),
                'per_page': 100,
                'include_subgroups': True  # Include merge requests from subgroups
            }
            
            all_merge_requests = []
            page = 1
            
            while True:
                params['page'] = page
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                merge_requests = response.json()
                if not merge_requests:  # No more pages
                    break
                
                # Filter by team members and format data
                for mr in merge_requests:
                    author_username = mr.get('author', {}).get('username', '')
                    if author_username in config.team_members:
                        # Get project name from the project object in the MR
                        project_name = mr.get('project', {}).get('name', 'Unknown Project')
                        
                        all_merge_requests.append({
                            'author': author_username,
                            'title': mr.get('title', ''),
                            'created_at': mr.get('created_at', ''),
                            'merged_at': mr.get('merged_at', ''),
                            'web_url': mr.get('web_url', ''),
                            'project_name': project_name,
                            'project_id': mr.get('project', {}).get('id', '')
                        })
                
                # Check if there are more pages
                if len(merge_requests) < params['per_page']:
                    break
                
                page += 1
                logger.debug(f"Fetched page {page-1}, found {len([mr for mr in merge_requests if mr.get('author', {}).get('username', '') in config.team_members])} relevant MRs")
            
            logger.info(f"Fetched {len(all_merge_requests)} total merge requests from GitLab group {group_id} using group-level API")
            return all_merge_requests
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching GitLab group data: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []


class GitHubDataCollector:
    """Collects merge request (pull request) data from GitHub API."""
    
    def __init__(self, token: str):
        """Initialize GitHub data collector."""
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def get_pull_requests(self, repo_owner: str, repo_name: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch pull requests for a repository within a date range."""
        try:
            url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls"
            params = {
                'state': 'closed',
                'sort': 'created',
                'direction': 'desc',
                'per_page': 100
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            pull_requests = response.json()
            
            # Filter by date range, merge status, and team members
            filtered_prs = []
            for pr in pull_requests:
                # Check if PR was created in the date range
                created_at = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                if not (start_date <= created_at <= end_date):
                    continue
                
                # Check if PR was merged
                if not pr.get('merged_at'):
                    continue
                
                # Check if author is in team
                author_username = pr.get('user', {}).get('login', '')
                if author_username in config.team_members:
                    filtered_prs.append({
                        'author': author_username,
                        'title': pr.get('title', ''),
                        'created_at': pr.get('created_at', ''),
                        'merged_at': pr.get('merged_at', ''),
                        'web_url': pr.get('html_url', '')
                    })
            
            logger.info(f"Fetched {len(filtered_prs)} pull requests from GitHub")
            return filtered_prs
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching GitHub data: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return []


class DataCollector:
    """Main data collector that handles both GitLab and GitHub."""
    
    def __init__(self):
        """Initialize data collector with configured APIs."""
        self.gitlab_collector = None
        self.github_collector = None
        
        if config.gitlab_token:
            self.gitlab_collector = GitLabDataCollector(config.gitlab_token, config.gitlab_url)
        
        if config.github_token:
            self.github_collector = GitHubDataCollector(config.github_token)
    
    def get_weekly_data(self) -> Dict[str, int]:
        """Get merge request data for the last week."""
        start_date, end_date = get_date_range_last_week()
        return self._collect_data(start_date, end_date)
    
    def get_monthly_data(self) -> Dict[str, int]:
        """Get merge request data for the current month."""
        start_date, end_date = get_date_range_current_month()
        return self._collect_data(start_date, end_date)
    
    def _collect_data(self, start_date: datetime, end_date: datetime) -> Dict[str, int]:
        """Collect merge request data from configured sources."""
        all_mrs = []
        
        # Collect from GitLab if configured
        if self.gitlab_collector:
            # Priority: Group > Project > Repository URL
            if config.group_id:
                gitlab_mrs = self.gitlab_collector.get_group_merge_requests(
                    config.group_id, start_date, end_date
                )
                all_mrs.extend(gitlab_mrs)
                logger.info(f"Collected {len(gitlab_mrs)} MRs from GitLab group {config.group_id}")
            elif config.project_id:
                gitlab_mrs = self.gitlab_collector.get_merge_requests(
                    config.project_id, start_date, end_date
                )
                all_mrs.extend(gitlab_mrs)
                logger.info(f"Collected {len(gitlab_mrs)} MRs from GitLab project {config.project_id}")
        
        # Collect from GitHub if configured
        if self.github_collector and config.repository_url:
            # Extract owner and repo from URL
            try:
                # Handle URLs like https://github.com/owner/repo
                url_parts = config.repository_url.rstrip('/').split('/')
                if len(url_parts) >= 2:
                    repo_owner = url_parts[-2]
                    repo_name = url_parts[-1]
                    
                    github_mrs = self.github_collector.get_pull_requests(
                        repo_owner, repo_name, start_date, end_date
                    )
                    all_mrs.extend(github_mrs)
                    logger.info(f"Collected {len(github_mrs)} MRs from GitHub repository")
            except Exception as e:
                logger.error(f"Error parsing repository URL: {e}")
        
        # Count merge requests per team member
        mr_counts = {member: 0 for member in config.team_members}
        for mr in all_mrs:
            author = mr.get('author', '')
            if author in mr_counts:
                mr_counts[author] += 1
        
        logger.info(f"Final counts: {mr_counts}")
        return mr_counts
    
    def has_valid_configuration(self) -> bool:
        """Check if the data collector has valid configuration."""
        has_token = bool(config.gitlab_token or config.github_token)
        has_repo = bool(config.group_id or config.project_id or config.repository_url)
        return has_token and has_repo
