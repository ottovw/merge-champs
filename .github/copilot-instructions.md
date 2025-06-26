<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Merge Champ Project Instructions

This is a Python terminal application for tracking merge request statistics. The application creates beautiful, encouraging terminal output to celebrate team contributions with emojis and motivational messaging.

## Key Guidelines:

1. **Visual Appeal**: All output should be modern, colorful, and encouraging. Use extensive emojis, friendly colors, and motivational messaging. The terminal output uses a 2-column layout for weekly vs monthly comparisons.

2. **Data Sources**: Support both GitLab and GitHub APIs for collecting merge request data.

3. **Output Types**: 
   - Terminal-based statistics display (primary feature)
   - Weekly activity summary (last 7 days)
   - Monthly summary (current month)
   - Team member rankings with unique emojis
   - Motivational messages based on activity levels

4. **Emoji System**: Use a diverse set of friendly emojis for team rankings:
   - 🏆 🥈 🥉 ⭐ 🌟 ✨ 💫 🌺 🎸 🎪 🎭 🎲 (and more)
   - Each team member gets a unique emoji regardless of ranking
   - Maintain encouraging tone for all participants

5. **Code Style**:
   - Use type hints where appropriate
   - Include comprehensive error handling
   - Add logging for debugging
   - Follow PEP 8 style guidelines

6. **Dependencies**: 
   - requests for API calls
   - python-dotenv for configuration
   - datetime for time calculations
   - logging for debugging

7. **Configuration**: Use environment variables for sensitive data like API tokens and team member lists.

8. **Output Format**: 
   - Beautiful terminal output with 2-column layout
   - Centered text with proper emoji alignment
   - Clear separation between weekly and monthly stats
   - Data summary section with key metrics
   - Motivational messaging at the end

9. **Sample Data**: Support `--sample` flag for demonstration without requiring API configuration.
