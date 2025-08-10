# Baseball Betting Discord Bot

## Overview

This is a Discord bot that provides baseball betting predictions by analyzing advanced statistics from Google Sheets and integrating live betting odds for Expected Value (EV+) calculations. The bot generates data-driven top 5 betting picks by combining statistical analysis with real-time odds from multiple sportsbooks, providing comprehensive betting recommendations through Discord commands.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Architecture
The application follows a modular architecture with clear separation of concerns:

- **Discord Bot Layer**: Handles user interactions and command processing
- **Data Integration Layer**: Manages Google Sheets connectivity and data caching
- **Prediction Engine**: Analyzes statistical data and generates betting recommendations
- **Configuration Management**: Centralized configuration with environment variable support

### Technology Stack
- **Discord.py**: Bot framework for Discord integration
- **Google Sheets API**: Data source for advanced baseball statistics
- **The Odds API**: Live betting odds and sportsbook data integration
- **Pandas/NumPy**: Data processing and statistical analysis
- **Python asyncio**: Asynchronous operations for bot responsiveness
- **aiohttp**: Asynchronous HTTP requests for odds API integration

## Key Components

### 1. Discord Bot (main.py)
- **Purpose**: Main bot orchestration and command handling
- **Architecture Decision**: Uses discord.py with command extensions for structured command processing
- **Key Features**:
  - Asynchronous command processing
  - Global error handling
  - Integration with prediction, sheets, and odds API components
  - Enhanced commands: `!ev_plus_picks`, `!top5_picks`, `!smart_picks` for advanced betting analysis
  - Smart picks: Combines EV+ odds with statistical scoring for optimal betting recommendations

### 2. Google Sheets Integration (sheets_integration.py)
- **Purpose**: Fetches and caches advanced baseball statistics
- **Architecture Decision**: Implements caching (15-minute duration) to reduce API calls and improve performance
- **Authentication**: Supports both file-based and environment variable credentials
- **Data Source**: Specific Google Sheet containing advanced baseball metrics (WOBA, XBA, XSLG, XWOBA)

### 3. Prediction Engine (prediction_engine.py)
- **Purpose**: Analyzes team statistics and generates betting recommendations with EV+ calculations
- **Architecture Decision**: Enhanced with Odds API integration for live betting data
- **Statistical Metrics**: Focuses on advanced sabermetrics (WOBA, XWOBA, XSLG, XBA)
- **Enhanced Features**:
  - Expected Value (EV+) calculations using live odds
  - Data-driven top 5 picks combining statistics with betting opportunities
  - Smart picks algorithm that combines EV+ odds with statistical team scoring
  - Opponent-adjusted statistical analysis for enhanced accuracy
  - Confidence scoring system for betting recommendations
  - Integration with multiple sportsbooks through Odds API

### 4. Odds API Integration (odds_api.py)
- **Purpose**: Fetches live betting odds for EV+ calculations
- **Architecture Decision**: Asynchronous API calls with comprehensive error handling
- **Key Features**:
  - Live MLB odds from multiple sportsbooks
  - American odds conversion to probabilities and decimal format
  - Expected Value calculations for betting opportunities
  - Team name normalization for matching with statistical data
  - Best odds finding across multiple bookmakers

### 5. Configuration Management (config.py)
- **Purpose**: Centralized configuration with validation
- **Architecture Decision**: Class-based configuration with environment variable support
- **Features**: Built-in validation and configuration printing capabilities
- **Optional**: ODDS_API_KEY for live betting odds integration

## Data Flow

1. **User Command**: User issues Discord command (e.g., `!advanced_stats`)
2. **Cache Check**: Bot checks if cached Google Sheets data is still valid
3. **Data Retrieval**: If cache expired, fetch fresh data from Google Sheets
4. **Statistical Analysis**: Prediction engine processes data using weighted algorithms
5. **Response Generation**: Bot formats and sends recommendations to Discord channel

## External Dependencies

### Primary Dependencies
- **Discord API**: Core bot functionality and user interaction
- **Google Sheets API**: Statistical data source
- **Google Cloud Service Account**: Authentication for Sheets access

### Python Packages
- `discord.py`: Discord bot framework
- `gspread`: Google Sheets API wrapper
- `google-auth`: Google authentication
- `pandas`: Data manipulation and analysis
- `numpy`: Numerical computations

## Deployment Strategy

### Environment Configuration
The bot supports flexible deployment through environment variables:

- **Authentication**: Supports both file-based (`google-credentials.json`) and environment variable (`GOOGLE_CREDENTIALS_JSON`) for Google credentials
- **Discord Integration**: Requires `DISCORD_TOKEN` environment variable
- **Customizable Settings**: Cache duration, command prefix, display limits, and logging levels

### Key Configuration Variables
- `DISCORD_TOKEN`: Discord bot authentication token
- `GOOGLE_CREDENTIALS_JSON`: Google service account credentials (JSON format)
- `CACHE_DURATION_MINUTES`: Data cache duration (default: 15 minutes)
- `COMMAND_PREFIX`: Bot command prefix (default: `!`)
- `MAX_TEAMS_DISPLAY`: Maximum teams to show (default: 20)

### Deployment Considerations
- **Credentials Management**: Secure handling of Discord and Google API credentials
- **Error Handling**: Comprehensive error handling for API failures and invalid commands
- **Performance**: Caching strategy to minimize API calls while maintaining data freshness
- **Scalability**: Modular design allows for easy extension of commands and statistical analysis

### Security Features
- Input validation for user commands
- Secure credential management with multiple authentication methods
- Configuration validation on startup
- Sensitive data exclusion from configuration printing