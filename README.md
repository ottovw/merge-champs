# Merge Champ 🏆

A fun and engaging terminal application to track merge request statistics for your development team. Show off your team's "Merge Champ" of the week and month with beautiful terminal output featuring emojis, motivational messages, and celebration of contributions!

## Features

- 📊 **Weekly & Monthly Stats** - Beautiful 2-column terminal layout comparing weekly vs monthly activity
- 👥 **Team Member Tracking** - Track specific team members' contributions with unique emojis
- 🎨 **Beautiful Terminal Output** - Extensive use of colorful emojis and encouraging messages
- 🏆 **Gamification** - Celebrate your team's top contributors with rankings and achievements
- 🔧 **Multi-Platform Support** - Works with GitLab and GitHub APIs
- 🎯 **Unique Emoji System** - Each team member gets their own special emoji (🏆🥈🥉⭐🌟✨💫🌺🎸🎪🎭🎲+)
- 💬 **Motivational Messaging** - Dynamic encouragement based on team activity levels

## Quick Start

### 🚀 Try it now with sample data:
```bash
python main.py --sample
```

### 🔧 For real data:

1. **Install dependencies:** *(Already done if you're in VS Code)*
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure your team:**
   - Copy `.env.example` to `.env`
   - Add your API tokens and team member details

3. **Run the application:**
   ```bash
   python main.py
   ```

4. **View your stats:**
   - Beautiful terminal output with emojis and team statistics
   - Perfect for CI/CD integration or daily standup reports

## Configuration

Configure your team members and repository settings in the `.env` file:

```env
# GitLab Configuration
GITLAB_TOKEN=your_gitlab_token_here
GITLAB_URL=https://gitlab.com

# GitLab Data Source (choose one):
# Option 1: All projects in a group (recommended for teams)
GROUP_ID=your_group_id
# Option 2: Specific project only
PROJECT_ID=your_project_id_here

# GitHub Configuration (alternative to GitLab)
GITHUB_TOKEN=your_github_token_here
REPOSITORY_URL=https://github.com/owner/repository

# Team Members (comma-separated usernames)
TEAM_MEMBERS=john.doe, jane.doe
```

## Project Structure

```
merge-champ/
├── src/
│   ├── data_collector.py   # Collect merge request data
│   ├── config.py           # Configuration management
│   └── utils.py            # Utility functions
├── main.py                 # Main application
├── requirements.txt        # Python dependencies (simplified!)
└── README.md              # This file
```

## Terminal Output

The application provides beautiful terminal output with:

### 🎯 2-Column Layout
- **Left Column**: Weekly statistics (📅 WORK WEEK)
- **Right Column**: Monthly statistics (🗓️ THIS MONTH)
- Clear visual separation with elegant borders

### 📊 Key Metrics
- **📊 Total MRs**: Merge request counts for both periods
- **👥 Participation**: Team participation percentage
- **🏆 Top Contributors**: Highlighted champions with trophy emojis

### 🎪 Team Breakdown
Each team member gets a unique, encouraging emoji:
- 🏆 1st place (Trophy)
- 🥈 2nd place (Silver medal) 
- 🥉 3rd place (Bronze medal)
- ⭐🌟✨💫🌺🎸🎪🎭🎲 (And many more friendly emojis!)

### 💬 Motivational Features
- Dynamic messages based on activity levels
- Encouraging tone for all participants
- Celebration of team achievements
- Data summary with key insights

Perfect for CI/CD integration, daily standups, team dashboards, or sprint reviews!

## Customization

The application generates friendly, encouraging terminal output with:
- 🎨 **Extensive Emoji System**: 13+ unique emojis for team rankings
- 📊 **Smart Layout**: 2-column comparison format for easy reading
- 🏆 **Achievement Celebration**: Special recognition for top contributors  
- 💪 **Motivational Messaging**: Dynamic encouragement based on team activity
- � **Visual Hierarchy**: Clear separation of metrics with centered text and borders
- 🌈 **Inclusive Design**: Every team member gets recognition with unique emojis

Perfect for team dashboards, sprint reviews, CI/CD integration, or just celebrating your development team's hard work!
