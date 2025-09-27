"""
Data collection module for Merge Champ application.
Handles fetching merge request data from GitLab APIs.
"""

import requests
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging
from .config import config
from .utils import get_week_date_range, get_month_date_range, MergeCountAggregate

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
                        'web_url': mr.get('web_url', ''),
                        'project_id': project_id,
                        'iid': mr.get('iid'),
                        'changes_count': mr.get('changes_count'),
                        'statistics': mr.get('statistics') or mr.get('diff_stats')
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
                        
                        project_info = mr.get('project') or {}
                        project_id = (
                            project_info.get('id')
                            or mr.get('project_id')
                            or mr.get('target_project_id')
                            or mr.get('source_project_id')
                            or ''
                        )

                        all_merge_requests.append({
                            'author': author_username,
                            'title': mr.get('title', ''),
                            'created_at': mr.get('created_at', ''),
                            'merged_at': mr.get('merged_at', ''),
                            'web_url': mr.get('web_url', ''),
                            'project_name': project_name,
                            'project_id': project_id,
                            'iid': mr.get('iid'),
                            'changes_count': mr.get('changes_count'),
                            'statistics': mr.get('statistics') or mr.get('diff_stats')
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

    def get_merge_request_changes_count(self, project_id: str, mr_iid: Any) -> Optional[int]:
        """Fetch additional statistics for a merge request to determine lines changed."""
        try:
            if not project_id or not mr_iid:
                return None

            url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}"
            params = {
                'include_diverged_commits_count': False,
                'include_rebase_in_progress': False,
                'include_stats': True,
            }
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            details = response.json()

            candidates = [
                details.get('changes_count'),
                details.get('total_changes'),
                details.get('changes'),
            ]

            stats_provided = False
            statistics = details.get('statistics') or details.get('stats') or details.get('diff_stats')
            if isinstance(statistics, dict):
                stats_candidates = [
                    statistics.get(key)
                    for key in ('total', 'total_changes', 'changes')
                ]
                candidates.extend(stats_candidates)

                additions = self._try_parse_int(statistics.get('additions'))
                deletions = self._try_parse_int(statistics.get('deletions'))
                if additions is not None or deletions is not None:
                    stats_provided = True
                    total = (additions or 0) + (deletions or 0)
                    if total:
                        return total

                stats_provided = stats_provided or any(
                    self._try_parse_int(value) is not None and self._try_parse_int(value) != 0
                    for value in stats_candidates
                )

            additions = self._try_parse_int(details.get('additions'))
            deletions = self._try_parse_int(details.get('deletions'))
            if additions is not None or deletions is not None:
                stats_provided = True
                total = (additions or 0) + (deletions or 0)
                if total:
                    return total

            parsed_candidates = [self._try_parse_int(candidate) for candidate in candidates if candidate is not None]
            parsed_candidates = [value for value in parsed_candidates if value is not None]

            parsed_from_changes = None
            if not stats_provided:
                parsed_from_changes = self._fetch_lines_from_changes_endpoint(str(project_id), str(mr_iid))
                if parsed_from_changes is not None:
                    return parsed_from_changes

            if parsed_candidates:
                best_candidate = max(parsed_candidates)
                if parsed_from_changes is not None and parsed_from_changes > best_candidate:
                    return parsed_from_changes
                return best_candidate

            if parsed_from_changes is not None:
                return parsed_from_changes

        except requests.exceptions.RequestException as exc:
            logger.debug(
                "Unable to retrieve changes count for project %s MR %s: %s",
                project_id,
                mr_iid,
                exc,
            )

        return None

    def _fetch_lines_from_changes_endpoint(self, project_id: str, mr_iid: str) -> Optional[int]:
        """Fetch merge request changes endpoint and compute line counts by parsing diffs."""
        try:
            url = f"{self.gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            payload = response.json()

            changes_payload = []
            if isinstance(payload, dict):
                changes_payload = payload.get('changes') or []
            elif isinstance(payload, list):
                changes_payload = payload

            additions = 0
            deletions = 0
            for change in changes_payload:
                diff_text = change.get('diff') or ''
                add, delete = self._parse_diff(delta=diff_text)
                additions += add
                deletions += delete

            total = additions + deletions
            if total:
                logger.debug(
                    "Parsed %s additions and %s deletions for project %s MR %s via changes endpoint",
                    additions,
                    deletions,
                    project_id,
                    mr_iid,
                )
                return total

        except requests.exceptions.RequestException as exc:
            logger.debug(
                "Unable to retrieve diff changes for project %s MR %s: %s",
                project_id,
                mr_iid,
                exc,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug(
                "Unexpected error parsing diff for project %s MR %s: %s",
                project_id,
                mr_iid,
                exc,
            )

        return None

    @staticmethod
    def _parse_diff(delta: str) -> Tuple[int, int]:
        """Return additions and deletions for a diff string."""
        additions = 0
        deletions = 0
        for line in delta.splitlines():
            if not line:
                continue
            if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
                continue
            if line.startswith('+'):
                additions += 1
            elif line.startswith('-'):
                deletions += 1
        return additions, deletions

    @staticmethod
    def _try_parse_int(value: Any) -> Optional[int]:
        """Attempt to coerce a value to int, returning None on failure."""
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


class DataCollector:
    """Main data collector that handles GitLab data sources."""
    
    def __init__(self):
        """Initialize data collector with configured APIs."""
        self.gitlab_collector = None
        
        if config.gitlab_token:
            self.gitlab_collector = GitLabDataCollector(config.gitlab_token, config.gitlab_url)
    
    def get_weekly_data(
        self,
        offset_weeks: int = 0,
        reference: Optional[datetime] = None,
        enable_weighting: bool = True,
    ) -> MergeCountAggregate:
        """Get merge request data for the requested week window."""
        start_date, end_date = get_week_date_range(offset_weeks=offset_weeks, reference=reference)
        return self._collect_data(start_date, end_date, enable_weighting=enable_weighting)
    
    def get_monthly_data(
        self,
        offset_months: int = 0,
        reference: Optional[datetime] = None,
        enable_weighting: bool = True,
    ) -> MergeCountAggregate:
        """Get merge request data for the requested month window."""
        start_date, end_date = get_month_date_range(offset_months=offset_months, reference=reference)
        return self._collect_data(start_date, end_date, enable_weighting=enable_weighting)
    
    def _collect_data(
        self,
        start_date: datetime,
        end_date: datetime,
        enable_weighting: bool = True,
    ) -> MergeCountAggregate:
        """Collect merge request data from configured sources."""
        all_mrs = []
        
        # Collect from GitLab if configured
        if self.gitlab_collector:
            # Priority: Group > Project
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
        
        raw_counts = {member: 0.0 for member in config.team_members}
        weighted_counts = {member: 0.0 for member in config.team_members}
        apply_weighting = enable_weighting and bool(config.mr_weight_rules)

        for mr in all_mrs:
            author = mr.get('author', '')
            if author not in raw_counts:
                continue

            mr_id = mr.get('iid') or mr.get('id') or 'unknown'
            mr_link = self._extract_mr_link(mr)
            raw_counts[author] += 1.0
            lines_changed = self._determine_lines_changed(mr, apply_weighting)
            weight = config.get_weight_for_lines(lines_changed)
            previous_weighted = weighted_counts[author]
            weighted_counts[author] = previous_weighted + weight

            if apply_weighting:
                logger.info(
                    "MR %s by %s -> raw total %.1f, lines_changed=%s, weight applied=%.2f, weighted total %.2f (link: %s)",
                    mr_id,
                    author,
                    raw_counts[author],
                    lines_changed if lines_changed is not None else "unknown",
                    weight,
                    weighted_counts[author],
                    mr_link,
                )
            else:
                logger.info(
                    "MR %s by %s -> raw total %.1f (weighting disabled, link: %s)",
                    mr_id,
                    author,
                    raw_counts[author],
                    mr_link,
                )

        aggregate = MergeCountAggregate(raw=raw_counts, weighted=weighted_counts)
        aggregate.ensure_members(config.team_members)
        aggregate.round_weighted()

        logger.info(
            "Final merge request counts (raw vs weighted): %s vs %s",
            aggregate.raw,
            aggregate.weighted,
        )
        return aggregate

    def _extract_mr_link(self, mr: Dict[str, Any]) -> str:
        """Return a link to the merge request if present."""
        url = mr.get('web_url') or mr.get('url')
        if url:
            return str(url)

        project_path = mr.get('references', {}).get('full') if isinstance(mr.get('references'), dict) else None
        iid = mr.get('iid') or mr.get('id')
        if project_path and iid:
            return f"{config.gitlab_url.rstrip('/')}/{project_path}"

        return "N/A"

    def _determine_lines_changed(self, mr: Dict[str, Any], apply_weighting: bool) -> Optional[int]:
        """Determine how many lines changed for a merge request."""
        if not apply_weighting:
            return None

        author = mr.get('author', 'unknown')
        mr_id = mr.get('iid') or mr.get('id') or 'unknown'
        mr_link = self._extract_mr_link(mr)

        candidates = [
            mr.get('lines_changed'),
            mr.get('changes_count'),
        ]

        statistics = mr.get('statistics')
        if isinstance(statistics, dict):
            candidates.extend(
                statistics.get(key)
                for key in ('total_changes', 'total', 'changes')
            )

        for candidate in candidates:
            if candidate is None:
                continue
            try:
                lines = int(candidate)
                logger.info(
                    "MR %s by %s initial line estimate: %s (link: %s)",
                    mr_id,
                    author,
                    lines,
                    mr_link,
                )
                return lines
            except (TypeError, ValueError):
                continue

        if not self.gitlab_collector:
            return None

        project_id = (
            mr.get('project_id')
            or mr.get('target_project_id')
            or mr.get('source_project_id')
            or config.project_id
            or ''
        )
        iid = mr.get('iid')
        if not project_id or iid is None:
            logger.info(
                "MR %s by %s has no project identifier or IID for detail lookup; skipping line count fetch (link: %s)",
                mr_id,
                author,
                mr_link,
            )
            return None

        if not config.mr_weight_rules:
            logger.debug(
                "MR %s by %s weighting disabled; skipping detailed line count fetch",
                mr_id,
                author,
            )
            return None

        fetched_lines = self.gitlab_collector.get_merge_request_changes_count(str(project_id), iid)
        logger.info(
            "MR %s by %s fetched detail line count: %s (link: %s)",
            mr_id,
            author,
            fetched_lines if fetched_lines is not None else "unknown",
            mr_link,
        )
        return fetched_lines
    
    def has_valid_configuration(self) -> bool:
        """Check if the data collector has valid configuration."""
        has_token = bool(config.gitlab_token)
        has_source = bool(config.group_id or config.project_id)
        return has_token and has_source
