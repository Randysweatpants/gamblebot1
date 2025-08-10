"""
Odds API Integration for Sports Betting Data
Fetches live betting odds for MLB games to calculate Expected Value (EV+)
"""

import requests
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

class OddsAPI:
    """Integration with The Odds API for live betting data"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_api_key()
        self.base_url = "https://api.the-odds-api.com/v4"
        self.sport = "baseball_mlb"
        self.regions = "us"  # US bookmakers
        self.markets = "h2h"  # Head-to-head (moneyline)
        self.odds_format = "american"
        
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment or config"""
        import os
        from config import Config
        return Config.ODDS_API_KEY
    
    async def get_live_odds(self) -> List[Dict]:
        """Fetch live MLB odds from multiple sportsbooks"""
        if not self.api_key:
            logger.error("No Odds API key provided")
            return []
        
        url = f"{self.base_url}/sports/{self.sport}/odds"
        params = {
            'apiKey': self.api_key,
            'regions': self.regions,
            'markets': self.markets,
            'oddsFormat': self.odds_format,
            'dateFormat': 'iso'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Fetched odds for {len(data)} games")
                        return data
                    else:
                        logger.error(f"Odds API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching odds: {e}")
            return []
    
    def convert_american_to_probability(self, american_odds: int) -> float:
        """Convert American odds to implied probability"""
        if american_odds > 0:
            return 100 / (american_odds + 100)
        else:
            return abs(american_odds) / (abs(american_odds) + 100)
    
    def convert_american_to_decimal(self, american_odds: int) -> float:
        """Convert American odds to decimal odds"""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
    
    def calculate_expected_value(self, true_probability: float, odds: int) -> float:
        """Calculate Expected Value (EV) for a bet
        
        EV = (True Probability × Decimal Odds) - 1
        Positive EV indicates a profitable bet
        """
        decimal_odds = self.convert_american_to_decimal(odds)
        ev = (true_probability * decimal_odds) - 1
        return ev
    
    def find_best_odds(self, game_odds: Dict, team_name: str) -> Optional[Tuple[str, int]]:
        """Find the best odds for a specific team across all sportsbooks"""
        best_odds = None
        best_bookmaker = None
        
        for bookmaker in game_odds.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if market['key'] == 'h2h':
                    for outcome in market['outcomes']:
                        if self._normalize_team_name(outcome['name']) == self._normalize_team_name(team_name):
                            odds = outcome['price']
                            if best_odds is None or odds > best_odds:  # Higher American odds = better for bettor
                                best_odds = odds
                                best_bookmaker = bookmaker['title']
        
        return (best_bookmaker, best_odds) if best_odds else None
    
    def _normalize_team_name(self, team_name: str) -> str:
        """Normalize team names for matching between sheets and odds API"""
        # Common team name mappings
        name_mappings = {
            'Cleveland Guardians': 'Cleveland Guardians',
            'Baltimore Orioles': 'Baltimore Orioles',
            'Colorado Rockies': 'Colorado Rockies',
            'Arizona Diamondbacks': 'Arizona Diamondbacks',
            'Los Angeles Angels': 'Los Angeles Angels',
            'LA Angels': 'Los Angeles Angels',
            'New York Yankees': 'New York Yankees',
            'NY Yankees': 'New York Yankees',
            'Boston Red Sox': 'Boston Red Sox',
            'Houston Astros': 'Houston Astros',
            'Seattle Mariners': 'Seattle Mariners',
            'Texas Rangers': 'Texas Rangers',
            'Oakland Athletics': 'Oakland Athletics',
            'Kansas City Royals': 'Kansas City Royals',
            'Minnesota Twins': 'Minnesota Twins',
            'Detroit Tigers': 'Detroit Tigers',
            'Chicago White Sox': 'Chicago White Sox',
            'Toronto Blue Jays': 'Toronto Blue Jays',
            'Tampa Bay Rays': 'Tampa Bay Rays',
            'Atlanta Braves': 'Atlanta Braves',
            'New York Mets': 'New York Mets',
            'NY Mets': 'New York Mets',
            'Philadelphia Phillies': 'Philadelphia Phillies',
            'Miami Marlins': 'Miami Marlins',
            'Washington Nationals': 'Washington Nationals',
            'Milwaukee Brewers': 'Milwaukee Brewers',
            'Chicago Cubs': 'Chicago Cubs',
            'Cincinnati Reds': 'Cincinnati Reds',
            'Pittsburgh Pirates': 'Pittsburgh Pirates',
            'St. Louis Cardinals': 'St. Louis Cardinals',
            'San Diego Padres': 'San Diego Padres',
            'Los Angeles Dodgers': 'Los Angeles Dodgers',
            'LA Dodgers': 'Los Angeles Dodgers',
            'San Francisco Giants': 'San Francisco Giants',
            'SF Giants': 'San Francisco Giants'
        }
        
        # Clean and normalize the name
        cleaned_name = team_name.strip()
        return name_mappings.get(cleaned_name, cleaned_name)
    
    async def get_ev_opportunities(self, team_stats_df, min_ev: float = 0.05) -> List[Dict]:
        """Find positive EV betting opportunities based on team stats and live odds
        
        Args:
            team_stats_df: DataFrame with team statistics and calculated probabilities
            min_ev: Minimum EV threshold for recommendations (default 5%)
        
        Returns:
            List of EV+ betting opportunities
        """
        odds_data = await self.get_live_odds()
        ev_opportunities = []
        
        if not odds_data:
            logger.warning("No odds data available")
            return ev_opportunities
        
        # Process each game's odds
        for game in odds_data:
            home_team = game.get('home_team')
            away_team = game.get('away_team')
            commence_time = game.get('commence_time')
            
            # Check if we have stats for these teams
            for team_name in [home_team, away_team]:
                normalized_name = self._normalize_team_name(team_name)
                team_stats = team_stats_df[
                    team_stats_df['Team'].str.contains(normalized_name, case=False, na=False)
                ]
                
                if not team_stats.empty:
                    team_row = team_stats.iloc[0]
                    
                    # Calculate true win probability based on team stats
                    # This uses our prediction engine's scoring system
                    true_probability = self._calculate_win_probability(team_row)
                    
                    # Find best odds for this team
                    odds_info = self.find_best_odds(game, team_name)
                    if odds_info:
                        bookmaker, odds = odds_info
                        
                        # Calculate Expected Value
                        ev = self.calculate_expected_value(true_probability, odds)
                        
                        if ev >= min_ev:  # Positive EV opportunity
                            ev_opportunities.append({
                                'team': team_name,
                                'opponent': away_team if team_name == home_team else home_team,
                                'game_time': commence_time,
                                'bookmaker': bookmaker,
                                'odds': odds,
                                'true_probability': true_probability,
                                'implied_probability': self.convert_american_to_probability(odds),
                                'expected_value': ev,
                                'ev_percentage': ev * 100,
                                'team_stats': {
                                    'WOBA': team_row.get('WOBA', 'N/A'),
                                    'XBA': team_row.get('XBA', 'N/A'),
                                    'XSLG': team_row.get('XSLG', 'N/A'),
                                    'XWOBA': team_row.get('XWOBA', 'N/A')
                                }
                            })
        
        # Sort by EV percentage (highest first)
        ev_opportunities.sort(key=lambda x: x['ev_percentage'], reverse=True)
        
        logger.info(f"Found {len(ev_opportunities)} EV+ opportunities")
        return ev_opportunities
    
    def _calculate_win_probability(self, team_stats: Dict) -> float:
        """Calculate win probability based on team's advanced statistics
        
        This is a simplified model - in practice, you'd want more sophisticated
        modeling including opponent adjustments, home field advantage, etc.
        """
        # Extract key metrics
        woba = float(team_stats.get('WOBA', 0.320)) if team_stats.get('WOBA', 'N/A') != 'N/A' else 0.320
        xba = float(team_stats.get('XBA', 0.250)) if team_stats.get('XBA', 'N/A') != 'N/A' else 0.250
        xslg = float(team_stats.get('XSLG', 0.400)) if team_stats.get('XSLG', 'N/A') != 'N/A' else 0.400
        xwoba = float(team_stats.get('XWOBA', 0.320)) if team_stats.get('XWOBA', 'N/A') != 'N/A' else 0.320
        
        # Weighted scoring system (similar to prediction_engine.py)
        # Higher values indicate better offensive performance
        woba_score = max(0, (woba - 0.300) / 0.100)  # Normalize around league average
        xba_score = max(0, (xba - 0.240) / 0.050)
        xslg_score = max(0, (xslg - 0.380) / 0.100)
        xwoba_score = max(0, (xwoba - 0.300) / 0.100)
        
        # Weighted composite score
        composite_score = (
            woba_score * 0.35 +      # Weighted On-Base Average (highest weight)
            xwoba_score * 0.25 +     # Expected wOBA
            xslg_score * 0.25 +      # Expected Slugging
            xba_score * 0.15         # Expected Batting Average
        )
        
        # Convert to probability (0.4 to 0.6 range for most teams)
        # Elite teams can go higher, poor teams lower
        base_probability = 0.50  # Average team
        probability = base_probability + (composite_score * 0.15)
        
        # Clamp between reasonable bounds
        probability = max(0.25, min(0.75, probability))
        
        return probability

# Example usage and testing
async def test_odds_api():
    """Test function for odds API integration"""
    odds_api = OddsAPI()
    
    # Test fetching live odds
    odds = await odds_api.get_live_odds()
    print(f"Fetched {len(odds)} games")
    
    if odds:
        game = odds[0]
        print(f"Sample game: {game['away_team']} @ {game['home_team']}")
        
        # Test odds conversion
        sample_odds = -110
        prob = odds_api.convert_american_to_probability(sample_odds)
        decimal = odds_api.convert_american_to_decimal(sample_odds)
        print(f"American odds {sample_odds}: {prob:.3f} probability, {decimal:.3f} decimal")
        
        # Test EV calculation
        true_prob = 0.55  # 55% chance to win
        ev = odds_api.calculate_expected_value(true_prob, sample_odds)
        print(f"EV with {true_prob} true probability: {ev:.3f} ({ev*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(test_odds_api())