import os
from typing import Optional

class Config:
    """Configuration settings for the Discord bot"""
    
    # Discord settings
    DISCORD_TOKEN: Optional[str] = os.getenv('DISCORD_TOKEN')
    
    # Google Sheets settings
    GOOGLE_CREDENTIALS_FILE: str = 'google-credentials.json'
    GOOGLE_CREDENTIALS_JSON: Optional[str] = os.getenv('GOOGLE_CREDENTIALS_JSON')
    GOOGLE_SHEET_URL: str = "https://docs.google.com/spreadsheets/d/11EyxXDDChFD91Be-_K5oMbLxbejIAUP6O54_pONAcPA/edit"
    
    # Cache settings
    CACHE_DURATION_MINUTES: int = int(os.getenv('CACHE_DURATION_MINUTES', '15'))
    
    # Bot settings
    COMMAND_PREFIX: str = os.getenv('COMMAND_PREFIX', '!')
    MAX_TEAMS_DISPLAY: int = int(os.getenv('MAX_TEAMS_DISPLAY', '20'))
    DEFAULT_RECOMMENDATION_COUNT: int = int(os.getenv('DEFAULT_RECOMMENDATION_COUNT', '3'))
    
    # Logging settings
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Odds API settings
    ODDS_API_KEY: Optional[str] = os.getenv('ODDS_API_KEY', '32995f018fd8d6a57f0d1e1290b5e62b')
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate the configuration settings
        
        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []
        
        if not cls.DISCORD_TOKEN:
            errors.append("DISCORD_TOKEN environment variable is required")
        
        if not cls.GOOGLE_CREDENTIALS_JSON and not os.path.exists(cls.GOOGLE_CREDENTIALS_FILE):
            errors.append(
                f"Google credentials not found. Please provide either:\n"
                f"1. A '{cls.GOOGLE_CREDENTIALS_FILE}' file, or\n"
                f"2. Set GOOGLE_CREDENTIALS_JSON environment variable"
            )
        
        return len(errors) == 0, errors
    
    @classmethod
    def print_config(cls):
        """Print current configuration (excluding sensitive data)"""
        print("=== Discord Bot Configuration ===")
        print(f"Command Prefix: {cls.COMMAND_PREFIX}")
        print(f"Cache Duration: {cls.CACHE_DURATION_MINUTES} minutes")
        print(f"Max Teams Display: {cls.MAX_TEAMS_DISPLAY}")
        print(f"Default Recommendations: {cls.DEFAULT_RECOMMENDATION_COUNT}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print(f"Discord Token: {'✓ Set' if cls.DISCORD_TOKEN else '✗ Missing'}")
        print(f"Google Credentials File: {'✓ Found' if os.path.exists(cls.GOOGLE_CREDENTIALS_FILE) else '✗ Not found'}")
        print(f"Google Credentials Env: {'✓ Set' if cls.GOOGLE_CREDENTIALS_JSON else '✗ Not set'}")
        print(f"Odds API Key: {'✓ Set' if cls.ODDS_API_KEY else '✗ Missing'}")
        print("=" * 35)

# Environment variable documentation
ENV_VARS_HELP = """
Required Environment Variables:
- DISCORD_TOKEN: Your Discord bot token

Optional Environment Variables:
- GOOGLE_CREDENTIALS_JSON: Google service account credentials as JSON string
- ODDS_API_KEY: The Odds API key for live betting odds (default: configured)
- CACHE_DURATION_MINUTES: How long to cache Google Sheets data (default: 15)
- COMMAND_PREFIX: Bot command prefix (default: !)
- MAX_TEAMS_DISPLAY: Maximum teams to show in stats (default: 20)
- DEFAULT_RECOMMENDATION_COUNT: Default number of team recommendations (default: 3)
- LOG_LEVEL: Logging level (default: INFO)

Google Credentials:
You can provide Google credentials in two ways:
1. Place a 'google-credentials.json' file in the project root
2. Set the GOOGLE_CREDENTIALS_JSON environment variable with the JSON content
"""

if __name__ == "__main__":
    # Print configuration help when run directly
    print(ENV_VARS_HELP)
    Config.print_config()
    
    is_valid, errors = Config.validate()
    if not is_valid:
        print("\n❌ Configuration Errors:")
        for error in errors:
            print(f"  • {error}")
    else:
        print("\n✅ Configuration is valid!")
