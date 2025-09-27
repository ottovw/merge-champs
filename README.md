# Merge Champ 🏆

Merge request highlights for your team, straight from the terminal.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # edit with your GitLab token, group/project, and team members
```

## Run it

| Scenario | Command |
| --- | --- |
| Demo with fake data | `python main.py --sample` |
| Live stats (raw counts) | `python main.py` |
| Live stats (weighted) | `python main.py --weighted` |
| Exact week | `python main.py --week 2025-09-01` |
| Exact month | `python main.py --month 2025-09` |
| Look back one week & one month | `python main.py --week-offset 1 --month-offset 1` |
| Export to Teams | `python main.py --publish-teams` |
| Inspect Teams payload only | `python main.py --publish-teams-debug` |

Smoke test the API wiring without sharing to Teams:

```bash
python scripts/live_smoke_test.py [--weighted] [--send-teams]
```

## Configuration

```env
GITLAB_TOKEN=...
GITLAB_URL=https://gitlab.com
GROUP_ID=...
PROJECT_ID=...
TEAM_MEMBERS=john.doe,jane.doe
MS_TEAMS_WEBHOOK_URL=...        # optional
ENABLE_TEAMS_NOTIFICATIONS=true  # optional
MR_WEIGHT_RULES=500:0.3,1000:0.6,2000:1.0  # optional
```

## Output preview

<!-- Replace this placeholder with your screenshot -->
![Terminal output placeholder](docs/output-placeholder.png)

Weekly vs monthly columns, emoji rankings, and motivational sign-offs keep things upbeat. Share it in standups, retros, or your favourite chat channel.
