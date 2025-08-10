import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any
from odds_api import OddsAPI

logger = logging.getLogger(__name__)

class PredictionEngine:
    """Engine for analyzing team statistics and generating betting predictions"""
    
    def __init__(self):
        # Initialize Odds API integration
        self.odds_api = OddsAPI()
        
        # Weights for different statistical categories (updated for actual column names)
        self.stat_weights = {
            'WOBA': 0.35,      # Weighted On-Base Average - primary metric
            'XWOBA': 0.25,     # Expected wOBA
            'XSLG': 0.25,      # Expected Slugging Percentage
            'XBA': 0.15        # Expected Batting Average
        }
        
        # Thresholds for rating teams
        self.rating_thresholds = {
            'excellent': 0.80,
            'very_good': 0.65,
            'good': 0.50,
            'average': 0.35,
            'below_average': 0.20
        }
    
    def get_best_teams(self, df: pd.DataFrame, count: int = 3) -> List[Dict[str, Any]]:
        """
        Get the best teams to bet on based on advanced statistics
        
        Args:
            df (pd.DataFrame): DataFrame with team statistics
            count (int): Number of teams to return
            
        Returns:
            List[Dict]: List of team recommendations with scores and analysis
        """
        try:
            if df.empty:
                logger.warning("Empty DataFrame provided to prediction engine")
                return []
            
            # Calculate composite scores for each team
            df_scored = self._calculate_team_scores(df)
            
            if df_scored.empty:
                logger.warning("No teams could be scored")
                return []
            
            # Get top teams
            top_teams = df_scored.head(count)
            
            # Generate recommendations
            recommendations = []
            for _, row in top_teams.iterrows():
                recommendation = self._create_team_recommendation(row)
                recommendations.append(recommendation)
            
            logger.info(f"Generated {len(recommendations)} team recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating team recommendations: {e}")
            return []
    
    def _calculate_team_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate composite scores for teams based on available statistics"""
        try:
            df_work = df.copy()
            
            # Initialize score
            df_work['composite_score'] = 0.0
            df_work['score_components'] = df_work.apply(lambda x: [], axis=1)
            
            total_weight_used = 0.0
            
            # Calculate weighted score based on available statistics
            for stat, weight in self.stat_weights.items():
                if stat in df_work.columns:
                    # Normalize the statistic (convert to 0-1 scale)
                    stat_values = pd.to_numeric(df_work[stat], errors='coerce')
                    
                    if stat_values.notna().sum() > 0:  # If we have valid values
                        # Normalize to 0-1 scale
                        stat_min = stat_values.min()
                        stat_max = stat_values.max()
                        
                        if stat_max > stat_min:
                            normalized = (stat_values - stat_min) / (stat_max - stat_min)
                            
                            # Add to composite score
                            df_work['composite_score'] += normalized.fillna(0) * weight
                            total_weight_used += weight
                            
                            # Track which stats were used
                            df_work['score_components'] = df_work.apply(
                                lambda row: row['score_components'] + [stat] 
                                if pd.notna(stat_values.loc[row.name]) 
                                else row['score_components'], 
                                axis=1
                            )
            
            # Normalize final score by total weight used
            if total_weight_used > 0:
                df_work['composite_score'] = df_work['composite_score'] / total_weight_used
            
            # Sort by composite score
            df_work = df_work.sort_values('composite_score', ascending=False)
            
            logger.info(f"Calculated scores for {len(df_work)} teams using weight total: {total_weight_used}")
            return df_work
            
        except Exception as e:
            logger.error(f"Error calculating team scores: {e}")
            return pd.DataFrame()
    
    def _create_team_recommendation(self, team_row: pd.Series) -> Dict[str, Any]:
        """Create a detailed recommendation for a team"""
        try:
            team_name = team_row.get('Team', 'Unknown Team')
            score = team_row.get('composite_score', 0.0)
            components = team_row.get('score_components', [])
            
            # Determine confidence level
            confidence = min(95, max(50, int(score * 100)))
            
            # Generate reasons based on strong statistics
            reasons = self._generate_reasons(team_row, components)
            
            # Determine overall rating
            rating = self._get_rating_from_score(score)
            
            recommendation = {
                'team': team_name,
                'score': score,
                'confidence': confidence,
                'reasons': reasons,
                'rating': rating,
                'stats_used': components
            }
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error creating team recommendation: {e}")
            return {
                'team': 'Unknown Team',
                'score': 0.0,
                'confidence': 50,
                'reasons': ['Analysis error'],
                'rating': 'Unknown',
                'stats_used': []
            }
    
    def _generate_reasons(self, team_row: pd.Series, components: List[str]) -> List[str]:
        """Generate human-readable reasons for the recommendation"""
        reasons = []
        
        try:
            # Check for standout statistics
            for stat in components:
                value = team_row.get(stat)
                if pd.notna(value):
                    if stat == 'wOBA' and value >= 0.360:
                        reasons.append("Excellent overall hitting (high wOBA)")
                    elif stat == 'OPS+' and value >= 115:
                        reasons.append("Above-average offensive production")
                    elif stat == 'xSLG' and value >= 0.480:
                        reasons.append("Strong expected power numbers")
                    elif stat == 'xBA' and value >= 0.270:
                        reasons.append("High expected batting average")
                    elif stat == 'wRC+' and value >= 110:
                        reasons.append("Superior run creation ability")
                    elif stat == 'ISO' and value >= 0.180:
                        reasons.append("Good power hitting metrics")
            
            # Add general reasons if no specific ones found
            if not reasons:
                if len(components) >= 4:
                    reasons.append("Strong across multiple offensive categories")
                elif len(components) >= 2:
                    reasons.append("Good performance in key statistics")
                else:
                    reasons.append("Limited data available")
            
            # Limit to 3 most important reasons
            return reasons[:3]
            
        except Exception as e:
            logger.error(f"Error generating reasons: {e}")
            return ["Statistical analysis"]
    
    def _get_rating_from_score(self, score: float) -> str:
        """Convert numerical score to rating description"""
        if score >= self.rating_thresholds['excellent']:
            return "Excellent"
        elif score >= self.rating_thresholds['very_good']:
            return "Very Good"
        elif score >= self.rating_thresholds['good']:
            return "Good"
        elif score >= self.rating_thresholds['average']:
            return "Average"
        elif score >= self.rating_thresholds['below_average']:
            return "Below Average"
        else:
            return "Poor"
    
    def assess_single_team(self, team_row: pd.Series) -> Dict[str, str]:
        """Provide an assessment for a single team"""
        try:
            # Calculate score for this team (normalize against typical values)
            score = 0.0
            factors = []
            
            # Use typical league averages for normalization
            league_averages = {
                'wOBA': 0.320,
                'OPS+': 100,
                'xSLG': 0.430,
                'xBA': 0.250,
                'wRC+': 100,
                'ISO': 0.150
            }
            
            for stat, avg in league_averages.items():
                if stat in team_row and pd.notna(team_row[stat]):
                    value = float(team_row[stat])
                    # Simple above/below average scoring
                    if value > avg:
                        score += (value / avg - 1) * self.stat_weights.get(stat, 0.1)
                        if value > avg * 1.1:  # 10% above average
                            factors.append(f"Strong {stat}")
                    else:
                        score -= (1 - value / avg) * self.stat_weights.get(stat, 0.1)
                        if value < avg * 0.9:  # 10% below average
                            factors.append(f"Weak {stat}")
            
            # Normalize score to 0-1 range
            score = max(0, min(1, score + 0.5))
            
            rating = self._get_rating_from_score(score)
            
            # Generate analysis
            if score > 0.7:
                analysis = "Strong betting candidate with multiple favorable metrics"
            elif score > 0.5:
                analysis = "Decent option with some positive indicators"
            elif score > 0.3:
                analysis = "Average team with mixed statistical performance"
            else:
                analysis = "Below-average team, consider avoiding"
            
            if factors:
                analysis += f". Key factors: {', '.join(factors[:3])}"
            
            return {
                'rating': rating,
                'analysis': analysis,
                'score': score
            }
            
        except Exception as e:
            logger.error(f"Error assessing single team: {e}")
            return {
                'rating': 'Unknown',
                'analysis': 'Unable to analyze team statistics',
                'score': 0.0
            }
    
    async def get_ev_plus_picks(self, df: pd.DataFrame, count: int = 5, min_ev: float = 0.05) -> List[Dict[str, Any]]:
        """
        Get top EV+ betting opportunities by combining team stats with live odds
        
        Args:
            df (pd.DataFrame): DataFrame with team statistics
            count (int): Number of picks to return (default: 5)
            min_ev (float): Minimum EV threshold (default: 5%)
            
        Returns:
            List[Dict]: List of EV+ betting opportunities
        """
        try:
            logger.info("Calculating EV+ opportunities...")
            
            # Get EV opportunities from odds API
            ev_opportunities = await self.odds_api.get_ev_opportunities(df, min_ev)
            
            if not ev_opportunities:
                logger.warning("No EV+ opportunities found")
                return []
            
            # Enhance each opportunity with our prediction analysis
            enhanced_picks = []
            for opportunity in ev_opportunities[:count]:
                # Find team in our dataset
                team_name = opportunity['team']
                team_stats = df[df['Team'].str.contains(team_name.split()[-1], case=False, na=False)]
                
                if not team_stats.empty:
                    team_row = team_stats.iloc[0]
                    team_assessment = self.assess_single_team(team_row)
                    
                    enhanced_pick = {
                        **opportunity,
                        'prediction_rating': team_assessment['rating'],
                        'prediction_analysis': team_assessment['analysis'],
                        'prediction_score': team_assessment['score'],
                        'confidence_level': self._calculate_confidence(opportunity, team_assessment)
                    }
                    enhanced_picks.append(enhanced_pick)
                else:
                    # Add without prediction analysis if team not in our dataset
                    enhanced_picks.append({
                        **opportunity,
                        'prediction_rating': 'Unknown',
                        'prediction_analysis': 'Team not in statistical dataset',
                        'prediction_score': 0.0,
                        'confidence_level': 'Low'
                    })
            
            logger.info(f"Generated {len(enhanced_picks)} EV+ picks")
            return enhanced_picks
            
        except Exception as e:
            logger.error(f"Error generating EV+ picks: {e}")
            return []
    
    def _calculate_confidence(self, opportunity: Dict, assessment: Dict) -> str:
        """Calculate confidence level for an EV+ opportunity"""
        try:
            ev_percentage = opportunity.get('ev_percentage', 0)
            prediction_score = assessment.get('score', 0)
            
            # High confidence: Good EV + Strong team stats
            if ev_percentage >= 10 and prediction_score >= 0.6:
                return 'High'
            # Medium confidence: Decent EV or good stats
            elif ev_percentage >= 5 or prediction_score >= 0.5:
                return 'Medium'
            else:
                return 'Low'
                
        except Exception:
            return 'Low'
    
    async def get_data_driven_picks(self, df: pd.DataFrame, count: int = 5) -> List[Dict[str, Any]]:
        """
        Get top 5 data-driven picks combining statistical analysis with live betting odds
        This is the main method for generating betting recommendations
        
        Args:
            df (pd.DataFrame): DataFrame with team statistics  
            count (int): Number of picks to return
            
        Returns:
            List[Dict]: Top betting picks with comprehensive analysis
        """
        try:
            logger.info("Generating data-driven betting picks...")
            
            # First, get our statistical best teams
            stat_picks = self.get_best_teams(df, count * 2)  # Get more for filtering
            
            # Then, get EV+ opportunities with live odds
            ev_picks = await self.get_ev_plus_picks(df, count * 2, min_ev=0.02)  # Lower threshold for more options
            
            # Combine and rank picks
            combined_picks = self._combine_and_rank_picks(stat_picks, ev_picks, count)
            
            logger.info(f"Generated {len(combined_picks)} data-driven picks")
            return combined_picks
            
        except Exception as e:
            logger.error(f"Error generating data-driven picks: {e}")
            return []
    
    def _combine_and_rank_picks(self, stat_picks: List[Dict], ev_picks: List[Dict], count: int) -> List[Dict]:
        """Combine statistical picks with EV+ picks and rank by overall value"""
        try:
            # Create a comprehensive ranking system
            all_picks = {}
            
            # Add EV+ picks with high priority (they have live odds data)
            for pick in ev_picks:
                team_name = pick['team']
                pick['source'] = 'EV_PLUS'
                pick['composite_score'] = self._calculate_composite_score(pick, has_odds=True)
                all_picks[team_name] = pick
            
            # Add statistical picks if not already included
            for pick in stat_picks:
                team_name = pick['team']
                if team_name not in all_picks:
                    # Convert statistical pick format to match EV picks
                    converted_pick = {
                        'team': team_name,
                        'odds': 'N/A',
                        'expected_value': 0.0,
                        'ev_percentage': 0.0,
                        'true_probability': 0.0,
                        'implied_probability': 0.0,
                        'bookmaker': 'N/A',
                        'game_time': 'TBD',
                        'prediction_rating': pick.get('rating', 'Unknown'),
                        'prediction_analysis': pick.get('reasons', ['Statistical analysis'])[0] if pick.get('reasons') else 'Strong statistical indicators',
                        'prediction_score': pick.get('score', 0),
                        'confidence_level': 'Medium',
                        'source': 'STATISTICAL',
                        'team_stats': pick.get('stats', {})
                    }
                    converted_pick['composite_score'] = self._calculate_composite_score(converted_pick, has_odds=False)
                    all_picks[team_name] = converted_pick
            
            # Sort by composite score and return top picks
            ranked_picks = sorted(all_picks.values(), key=lambda x: x['composite_score'], reverse=True)
            
            return ranked_picks[:count]
            
        except Exception as e:
            logger.error(f"Error combining picks: {e}")
            return []
    
    def _calculate_composite_score(self, pick: Dict, has_odds: bool) -> float:
        """Calculate a composite score for ranking picks"""
        try:
            score = 0.0
            
            # EV component (40% weight if available)
            if has_odds and pick.get('ev_percentage', 0) > 0:
                score += pick['ev_percentage'] * 0.4
            
            # Statistical prediction component (40% weight)  
            prediction_score = pick.get('prediction_score', 0)
            score += prediction_score * 40
            
            # Confidence boost (20% weight)
            confidence = pick.get('confidence_level', 'Low')
            confidence_multiplier = {'High': 1.0, 'Medium': 0.7, 'Low': 0.4}.get(confidence, 0.4)
            score += confidence_multiplier * 20
            
            return score
            
        except Exception:
            return 0.0
