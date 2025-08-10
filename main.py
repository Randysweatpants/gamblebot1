import discord
from discord.ext import commands
import asyncio
import os
import logging
from sheets_integration import SheetsIntegration
from prediction_engine import PredictionEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration - now with message content intent enabled in Discord Developer Portal
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize components
sheets_integration = SheetsIntegration()
prediction_engine = PredictionEngine()

@bot.event
async def on_ready():
    """Event triggered when bot is ready"""
    logger.info(f'{bot.user} has connected to Discord!')
    print(f'{bot.user} has connected to Discord!')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash commands")
        print(f"Synced {len(synced)} slash commands - Use /picks or /ev_picks")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")
        print(f"Failed to sync slash commands: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use `!help` to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required argument. Check the command usage.")
    else:
        logger.error(f"Unexpected error: {error}")
        await ctx.send(f"❌ An unexpected error occurred: {str(error)}")

@bot.command(name="ping")
async def ping(ctx):
    """Test command to check if bot is responsive"""
    await ctx.send("🏓 Pong! Bot is online and ready for betting predictions!")

@bot.command(name="advanced_stats")
async def advanced_stats(ctx, team_count: int = 5):
    """Display advanced statistics for top teams"""
    try:
        await ctx.send("📊 Fetching advanced statistics from Google Sheets...")
        
        # Get data from Google Sheets
        df = await sheets_integration.get_advanced_stats()
        
        if df.empty:
            await ctx.send("❌ No advanced statistics data available at this time.")
            return
        
        # Limit team count to reasonable range
        team_count = max(1, min(team_count, 20))
        top_teams = df.head(team_count)
        
        # Format the message
        msg = f"📊 **Top {team_count} Teams by Advanced Stats:**\n\n"
        
        for idx, row in top_teams.iterrows():
            team_name = row.get('Team', 'Unknown Team')
            xba = row.get('XBA', 'N/A')
            xslg = row.get('XSLG', 'N/A')
            woba = row.get('WOBA', 'N/A')
            xwoba = row.get('XWOBA', 'N/A')
            
            msg += f"**{idx + 1}. {team_name}**\n"
            msg += f"   • WOBA: {woba}\n"
            msg += f"   • XBA: {xba}\n"
            msg += f"   • XSLG: {xslg}\n"
            msg += f"   • XWOBA: {xwoba}\n\n"
        
        # Discord has a 2000 character limit for messages
        if len(msg) > 1900:
            msg = msg[:1900] + "...\n\n*Message truncated due to length*"
        
        await ctx.send(msg)
        
    except Exception as e:
        logger.error(f"Error in advanced_stats command: {e}")
        await ctx.send(f"❌ Error retrieving advanced statistics: {str(e)}")

@bot.command(name="best_teams_to_win")
async def best_teams_to_win(ctx, count: int = 3):
    """Get the best teams to bet on based on advanced statistics"""
    try:
        await ctx.send("🎯 Analyzing teams for best betting opportunities...")
        
        # Get data from Google Sheets
        df = await sheets_integration.get_advanced_stats()
        
        if df.empty:
            await ctx.send("❌ No data available for team analysis.")
            return
        
        # Get predictions from the prediction engine
        recommendations = prediction_engine.get_best_teams(df, count)
        
        if not recommendations:
            await ctx.send("❌ Unable to generate team recommendations at this time.")
            return
        
        # Format recommendations
        msg = f"🏆 **Top {len(recommendations)} Teams to Bet On:**\n\n"
        
        for i, rec in enumerate(recommendations, 1):
            team = rec['team']
            score = rec['score']
            reasons = rec['reasons']
            confidence = rec['confidence']
            
            msg += f"**{i}. {team}** (Confidence: {confidence}%)\n"
            msg += f"   📈 Score: {score:.2f}\n"
            msg += f"   💡 Key factors: {', '.join(reasons)}\n\n"
        
        msg += "⚠️ *Remember: This is for informational purposes only. Bet responsibly!*"
        
        # Check message length
        if len(msg) > 1900:
            msg = msg[:1900] + "...\n\n*Message truncated*"
        
        await ctx.send(msg)
        
    except Exception as e:
        logger.error(f"Error in best_teams_to_win command: {e}")
        await ctx.send(f"❌ Error generating team recommendations: {str(e)}")

@bot.command(name="team_lookup")
async def team_lookup(ctx, *, team_name: str):
    """Look up specific team statistics"""
    try:
        # Get data from Google Sheets
        df = await sheets_integration.get_advanced_stats()
        
        if df.empty:
            await ctx.send("❌ No data available for team lookup.")
            return
        
        # Search for the team (case-insensitive)
        team_data = df[df['Team'].str.contains(team_name, case=False, na=False)]
        
        if team_data.empty:
            await ctx.send(f"❌ No team found matching '{team_name}'. Please check the spelling.")
            return
        
        # Get the first match
        team_row = team_data.iloc[0]
        team_name = team_row.get('Team', 'Unknown Team')
        
        # Format team stats
        msg = f"📊 **{team_name} Advanced Statistics:**\n\n"
        
        stats_to_show = ['xBA', 'xSLG', 'wOBA', 'OPS+', 'ISO', 'BABIP', 'wRC+']
        
        for stat in stats_to_show:
            value = team_row.get(stat, 'N/A')
            msg += f"• **{stat}**: {value}\n"
        
        # Add prediction assessment
        assessment = prediction_engine.assess_single_team(team_row)
        msg += f"\n🎯 **Betting Assessment**: {assessment['rating']}\n"
        msg += f"💭 **Analysis**: {assessment['analysis']}\n"
        
        await ctx.send(msg)
        
    except Exception as e:
        logger.error(f"Error in team_lookup command: {e}")
        await ctx.send(f"❌ Error looking up team data: {str(e)}")

@bot.command(name="refresh_data")
async def refresh_data(ctx):
    """Manually refresh data from Google Sheets"""
    try:
        await ctx.send("🔄 Refreshing data from Google Sheets...")
        
        # Force refresh the data
        df = await sheets_integration.get_advanced_stats(force_refresh=True)
        
        if df.empty:
            await ctx.send("❌ No data retrieved during refresh.")
            return
        
        team_count = len(df)
        await ctx.send(f"✅ Data refreshed successfully! {team_count} teams loaded.")
        
    except Exception as e:
        logger.error(f"Error in refresh_data command: {e}")
        await ctx.send(f"❌ Error refreshing data: {str(e)}")

@bot.command(name="ev_plus_picks")
async def ev_plus_picks(ctx, count: int = 5):
    """Get EV+ betting opportunities with live odds"""
    try:
        await ctx.send("💰 Searching for EV+ betting opportunities with live odds...")
        
        # Get data from Google Sheets
        df = await sheets_integration.get_advanced_stats()
        
        if df.empty:
            await ctx.send("❌ No team data available for EV+ analysis.")
            return
        
        # Get EV+ picks from prediction engine
        ev_picks = await prediction_engine.get_ev_plus_picks(df, count)
        
        if not ev_picks:
            await ctx.send("⚠️ No EV+ opportunities found at this time. This could mean:\n• No live MLB games available\n• No positive EV opportunities in current odds\n• Odds API key not configured\n\nUse `!best_teams_to_win` for statistical analysis without live odds.")
            return
        
        # Format EV+ picks
        msg = f"💰 **Top {len(ev_picks)} EV+ Betting Opportunities:**\n\n"
        
        for i, pick in enumerate(ev_picks, 1):
            team = pick['team']
            opponent = pick.get('opponent', 'TBD')
            ev_pct = pick.get('ev_percentage', 0)
            odds = pick.get('odds', 'N/A')
            bookmaker = pick.get('bookmaker', 'N/A')
            confidence = pick.get('confidence_level', 'Medium')
            rating = pick.get('prediction_rating', 'Unknown')
            
            msg += f"**{i}. {team}** vs {opponent}\n"
            msg += f"   📈 EV: +{ev_pct:.1f}% | Odds: {odds} ({bookmaker})\n"
            msg += f"   🎯 Rating: {rating} | Confidence: {confidence}\n"
            
            # Add analysis if available
            analysis = pick.get('prediction_analysis', '')
            if analysis and len(analysis) < 60:
                msg += f"   💡 {analysis}\n"
            
            msg += "\n"
        
        msg += "⚠️ *EV+ = Expected Value positive. Bet responsibly!*"
        
        # Check message length
        if len(msg) > 1900:
            msg = msg[:1900] + "...\n\n*Message truncated*"
        
        await ctx.send(msg)
        
    except Exception as e:
        logger.error(f"Error in ev_plus_picks command: {e}")
        await ctx.send(f"❌ Error finding EV+ opportunities: {str(e)}")

@bot.command(name="top5_picks")
async def top5_picks(ctx):
    """Get data-driven top 5 betting picks combining statistics with live odds"""
    try:
        await ctx.send("🎯 Generating top 5 data-driven betting picks...")
        
        # Get data from Google Sheets
        df = await sheets_integration.get_advanced_stats()
        
        if df.empty:
            await ctx.send("❌ No team data available for analysis.")
            return
        
        # Get comprehensive data-driven picks
        picks = await prediction_engine.get_data_driven_picks(df, 5)
        
        if not picks:
            await ctx.send("❌ Unable to generate picks at this time.")
            return
        
        # Format the picks
        msg = "🏆 **TOP 5 DATA-DRIVEN BETTING PICKS**\n\n"
        
        for i, pick in enumerate(picks, 1):
            team = pick['team']
            source = pick.get('source', 'STATISTICAL')
            confidence = pick.get('confidence_level', 'Medium')
            rating = pick.get('prediction_rating', 'Good')
            
            # Emoji for pick ranking
            emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            emoji = emojis[i-1] if i-1 < len(emojis) else f"{i}️⃣"
            
            msg += f"{emoji} **{team}** ({confidence} Confidence)\n"
            msg += f"   📊 Rating: {rating}\n"
            
            # Add odds info if available
            if source == 'EV_PLUS' and pick.get('odds', 'N/A') != 'N/A':
                ev_pct = pick.get('ev_percentage', 0)
                odds = pick.get('odds')
                bookmaker = pick.get('bookmaker', 'Multiple')
                msg += f"   💰 EV: +{ev_pct:.1f}% | Odds: {odds} ({bookmaker})\n"
            else:
                msg += f"   📈 Source: Statistical Analysis\n"
            
            # Add key stats
            stats = pick.get('team_stats', {})
            if stats:
                woba = stats.get('WOBA', 'N/A')
                xba = stats.get('XBA', 'N/A') 
                msg += f"   📋 WOBA: {woba} | XBA: {xba}\n"
            
            msg += "\n"
        
        msg += "🔍 **Analysis Method:**\n"
        msg += "• Statistical modeling with advanced baseball metrics\n"
        msg += "• Live odds integration when available\n" 
        msg += "• Expected Value (EV) calculations\n\n"
        msg += "⚠️ *For informational purposes. Bet responsibly!*"
        
        # Check message length
        if len(msg) > 1900:
            msg = msg[:1900] + "...\n\n*Message truncated*"
        
        await ctx.send(msg)
        
    except Exception as e:
        logger.error(f"Error in top5_picks command: {e}")
        await ctx.send(f"❌ Error generating top 5 picks: {str(e)}")

# Slash Commands (Work without Message Content Intent)
@bot.tree.command(name="picks", description="Get top 5 data-driven betting picks")
async def slash_picks(interaction: discord.Interaction):
    """Slash command for top 5 data-driven picks"""
    try:
        await interaction.response.defer()
        
        # Get data from Google Sheets
        df = await sheets_integration.get_advanced_stats()
        
        if df.empty:
            await interaction.followup.send("No team data available for analysis.")
            return
        
        # Get comprehensive data-driven picks
        picks = await prediction_engine.get_data_driven_picks(df, 5)
        
        if not picks:
            await interaction.followup.send("Unable to generate picks at this time.")
            return
        
        # Format the picks
        msg = "**TOP 5 DATA-DRIVEN BETTING PICKS**\n\n"
        
        for i, pick in enumerate(picks, 1):
            team = pick['team']
            source = pick.get('source', 'STATISTICAL')
            confidence = pick.get('confidence_level', 'Medium')
            rating = pick.get('prediction_rating', 'Good')
            
            emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
            emoji = emojis[i-1] if i-1 < len(emojis) else f"{i}."
            
            msg += f"{emoji} **{team}** ({confidence} Confidence)\n"
            msg += f"   Rating: {rating}\n"
            
            # Add odds info if available
            if source == 'EV_PLUS' and pick.get('odds', 'N/A') != 'N/A':
                ev_pct = pick.get('ev_percentage', 0)
                odds = pick.get('odds')
                bookmaker = pick.get('bookmaker', 'Multiple')
                msg += f"   EV: +{ev_pct:.1f}% | Odds: {odds} ({bookmaker})\n"
            else:
                msg += f"   Source: Statistical Analysis\n"
            
            msg += "\n"
        
        msg += "**Analysis Method:**\n"
        msg += "• Statistical modeling with advanced baseball metrics\n"
        msg += "• Live odds integration when available\n" 
        msg += "• Expected Value (EV) calculations\n\n"
        msg += "*For informational purposes. Bet responsibly!*"
        
        # Check message length
        if len(msg) > 1900:
            msg = msg[:1900] + "...\n\n*Message truncated*"
        
        await interaction.followup.send(msg)
        
    except Exception as e:
        logger.error(f"Error in slash_picks command: {e}")
        await interaction.followup.send(f"Error generating picks: {str(e)}")

@bot.tree.command(name="ev_picks", description="Get EV+ betting opportunities with live odds")
async def slash_ev_picks(interaction: discord.Interaction, count: int = 5):
    """Slash command for EV+ picks"""
    try:
        await interaction.response.defer()
        
        # Get data from Google Sheets
        df = await sheets_integration.get_advanced_stats()
        
        if df.empty:
            await interaction.followup.send("No team data available for EV+ analysis.")
            return
        
        # Get EV+ picks from prediction engine
        ev_picks = await prediction_engine.get_ev_plus_picks(df, count)
        
        if not ev_picks:
            await interaction.followup.send("No EV+ opportunities found at this time. This could mean:\n• No live MLB games available\n• No positive EV opportunities in current odds\n• Try statistical analysis instead.")
            return
        
        # Format EV+ picks
        msg = f"**Top {len(ev_picks)} EV+ Betting Opportunities:**\n\n"
        
        for i, pick in enumerate(ev_picks, 1):
            team = pick['team']
            opponent = pick.get('opponent', 'TBD')
            ev_pct = pick.get('ev_percentage', 0)
            odds = pick.get('odds', 'N/A')
            bookmaker = pick.get('bookmaker', 'N/A')
            confidence = pick.get('confidence_level', 'Medium')
            rating = pick.get('prediction_rating', 'Unknown')
            
            msg += f"**{i}. {team}** vs {opponent}\n"
            msg += f"   EV: +{ev_pct:.1f}% | Odds: {odds} ({bookmaker})\n"
            msg += f"   Rating: {rating} | Confidence: {confidence}\n\n"
        
        msg += "*EV+ = Expected Value positive. Bet responsibly!*"
        
        # Check message length
        if len(msg) > 1900:
            msg = msg[:1900] + "...\n\n*Message truncated*"
        
        await interaction.followup.send(msg)
        
    except Exception as e:
        logger.error(f"Error in slash_ev_picks command: {e}")
        await interaction.followup.send(f"Error finding EV+ opportunities: {str(e)}")

@bot.tree.command(name="stats", description="Show top teams by advanced statistics")
async def slash_stats(interaction: discord.Interaction, count: int = 5):
    """Slash command for advanced stats"""
    try:
        await interaction.response.defer()
        
        # Get data from Google Sheets
        df = await sheets_integration.get_advanced_stats()
        
        if df.empty:
            await interaction.followup.send("No advanced statistics data available.")
            return
        
        # Limit team count to reasonable range
        team_count = max(1, min(count, 20))
        top_teams = df.head(team_count)
        
        # Format the message
        msg = f"**Top {team_count} Teams by Advanced Stats:**\n\n"
        
        for idx, row in top_teams.iterrows():
            team_name = row.get('Team', 'Unknown Team')
            xba = row.get('XBA', 'N/A')
            xslg = row.get('XSLG', 'N/A')
            woba = row.get('WOBA', 'N/A')
            xwoba = row.get('XWOBA', 'N/A')
            
            msg += f"**{idx + 1}. {team_name}**\n"
            msg += f"   • WOBA: {woba}\n"
            msg += f"   • XBA: {xba}\n"
            msg += f"   • XSLG: {xslg}\n"
            msg += f"   • XWOBA: {xwoba}\n\n"
        
        # Check message length
        if len(msg) > 1900:
            msg = msg[:1900] + "...\n\n*Message truncated*"
        
        await interaction.followup.send(msg)
        
    except Exception as e:
        logger.error(f"Error in slash_stats command: {e}")
        await interaction.followup.send(f"Error retrieving statistics: {str(e)}")

def get_ev_bets_with_stats(ev_bets, team_stats_df):
    """Combine EV bets with Google Sheets statistical data for enhanced recommendations"""
    if team_stats_df.empty:
        return ev_bets  # fallback if sheet fails

    ranked_bets = []

    for bet in ev_bets:
        team_name = bet.get('team', '')
        opponent = bet.get('opponent', '')
        
        # Find team stats in our dataframe
        team_stat = team_stats_df[team_stats_df['Team'].str.contains(team_name.split()[-1], case=False, na=False)]
        opponent_stat = team_stats_df[team_stats_df['Team'].str.contains(opponent.split()[-1], case=False, na=False)] if opponent else pd.DataFrame()

        # Calculate combined statistical score
        team_score = 0
        opponent_score = 0
        
        if not team_stat.empty:
            team_row = team_stat.iloc[0]
            # Use our weighted scoring system
            woba = float(team_row.get('WOBA', 0.320)) if team_row.get('WOBA', 'N/A') != 'N/A' else 0.320
            xwoba = float(team_row.get('XWOBA', 0.320)) if team_row.get('XWOBA', 'N/A') != 'N/A' else 0.320
            xslg = float(team_row.get('XSLG', 0.400)) if team_row.get('XSLG', 'N/A') != 'N/A' else 0.400
            xba = float(team_row.get('XBA', 0.250)) if team_row.get('XBA', 'N/A') != 'N/A' else 0.250
            
            # Normalized scoring (higher is better)
            team_score = (
                (woba - 0.300) * 35 +
                (xwoba - 0.300) * 25 +
                (xslg - 0.380) * 25 +
                (xba - 0.240) * 15
            )
        
        if not opponent_stat.empty:
            opp_row = opponent_stat.iloc[0]
            # Opponent score (lower opponent score is better for our team)
            opp_woba = float(opp_row.get('WOBA', 0.320)) if opp_row.get('WOBA', 'N/A') != 'N/A' else 0.320
            opp_xwoba = float(opp_row.get('XWOBA', 0.320)) if opp_row.get('XWOBA', 'N/A') != 'N/A' else 0.320
            opp_xslg = float(opp_row.get('XSLG', 0.400)) if opp_row.get('XSLG', 'N/A') != 'N/A' else 0.400
            opp_xba = float(opp_row.get('XBA', 0.250)) if opp_row.get('XBA', 'N/A') != 'N/A' else 0.250
            
            opponent_score = (
                (opp_woba - 0.300) * 35 +
                (opp_xwoba - 0.300) * 25 +
                (opp_xslg - 0.380) * 25 +
                (opp_xba - 0.240) * 15
            )

        # Combined score: our team's strength minus opponent's strength
        combined_score = team_score - (opponent_score * 0.5)  # Weight opponent less
        bet["score_boost"] = combined_score
        bet["team_score"] = team_score
        bet["opponent_score"] = opponent_score
        ranked_bets.append(bet)

    return sorted(ranked_bets, key=lambda x: x.get("score_boost", 0), reverse=True)[:5]

@bot.command(name="smart_picks")
async def smart_picks(ctx):
    """Smart MLB picks combining EV+ opportunities with advanced statistical analysis"""
    try:
        await ctx.send("🤖 Generating smart MLB picks (EV + Statistical Analysis)...")
        
        # Get data from Google Sheets
        df = await sheets_integration.get_advanced_stats()
        
        if df.empty:
            await ctx.send("❌ No team data available for smart picks analysis.")
            return
        
        # Get EV+ opportunities
        ev_bets = await prediction_engine.get_ev_plus_picks(df, 10)  # Get more for filtering
        
        if not ev_bets:
            await ctx.send("⚠️ No EV+ opportunities found at this time. This could mean:\n• No live MLB games available\n• No positive EV opportunities in current odds\n• Odds API may need configuration\n\nTry `!best_teams_to_win` for statistical analysis.")
            return
        
        # Combine EV with statistical analysis
        smart_bets = get_ev_bets_with_stats(ev_bets, df)
        
        if not smart_bets:
            await ctx.send("❌ Unable to generate smart picks at this time.")
            return
        
        # Format the message
        msg = "🤖 **SMART MLB PICKS (EV+ & Statistical Analysis)**\n\n"
        
        for idx, bet in enumerate(smart_bets, 1):
            team = bet['team']
            opponent = bet.get('opponent', 'TBD')
            ev_pct = bet.get('ev_percentage', 0)
            odds = bet.get('odds', 'N/A')
            bookmaker = bet.get('bookmaker', 'N/A')
            score_boost = bet.get('score_boost', 0)
            confidence = bet.get('confidence_level', 'Medium')
            
            msg += f"**{idx}. {team}** vs {opponent}\n"
            msg += f"   💰 EV: +{ev_pct:.1f}% | Odds: {odds} ({bookmaker})\n"
            msg += f"   🧮 Statistical Score: {score_boost:.1f} | {confidence} Confidence\n"
            
            # Add game time if available
            game_time = bet.get('game_time', '')
            if game_time and game_time != 'TBD':
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(game_time.replace('Z', '+00:00'))
                    formatted_time = dt.strftime('%I:%M %p ET')
                    msg += f"   🕒 Game Time: {formatted_time}\n"
                except:
                    pass
            
            msg += "\n"
        
        msg += "🔍 **Analysis Method:**\n"
        msg += "• Expected Value (EV) from live sportsbook odds\n"
        msg += "• Advanced sabermetrics (WOBA, XBA, XSLG, XWOBA)\n"
        msg += "• Opponent-adjusted statistical scoring\n"
        msg += "• Combined ranking for optimal betting value\n\n"
        msg += "⚠️ *Smart picks combine math with statistics. Bet responsibly!*"
        
        # Check message length
        if len(msg) > 1900:
            msg = msg[:1900] + "...\n\n*Message truncated*"
        
        await ctx.send(msg)
        
    except Exception as e:
        logger.error(f"Error in smart_picks command: {e}")
        await ctx.send(f"❌ Error generating smart picks: {str(e)}")

@bot.tree.command(name="smart_picks", description="Smart MLB picks combining EV+ with statistical analysis")
async def slash_smart_picks(interaction: discord.Interaction):
    """Slash command version of smart picks"""
    try:
        await interaction.response.defer()
        
        # Get data from Google Sheets
        df = await sheets_integration.get_advanced_stats()
        
        if df.empty:
            await interaction.followup.send("No team data available for smart picks analysis.")
            return
        
        # Get EV+ opportunities
        ev_bets = await prediction_engine.get_ev_plus_picks(df, 10)
        
        if not ev_bets:
            await interaction.followup.send("No EV+ opportunities found at this time. Try statistical analysis instead.")
            return
        
        # Combine EV with statistical analysis
        smart_bets = get_ev_bets_with_stats(ev_bets, df)
        
        if not smart_bets:
            await interaction.followup.send("Unable to generate smart picks at this time.")
            return
        
        # Format the message (similar to above but shorter for slash commands)
        msg = "**SMART MLB PICKS (EV+ & Stats)**\n\n"
        
        for idx, bet in enumerate(smart_bets, 1):
            team = bet['team']
            opponent = bet.get('opponent', 'TBD')
            ev_pct = bet.get('ev_percentage', 0)
            odds = bet.get('odds', 'N/A')
            bookmaker = bet.get('bookmaker', 'N/A')
            score_boost = bet.get('score_boost', 0)
            
            msg += f"**{idx}. {team}** vs {opponent}\n"
            msg += f"   EV: +{ev_pct:.1f}% | Odds: {odds} ({bookmaker})\n"
            msg += f"   Score: {score_boost:.1f}\n\n"
        
        msg += "*Combines EV+ odds with advanced baseball stats*"
        
        if len(msg) > 1900:
            msg = msg[:1900] + "...\n*Truncated*"
        
        await interaction.followup.send(msg)
        
    except Exception as e:
        logger.error(f"Error in slash_smart_picks command: {e}")
        await interaction.followup.send(f"Error generating smart picks: {str(e)}")

@bot.command(name="status")
async def status(ctx):
    """Check bot and Google Sheets connectivity status"""
    try:
        # Test Google Sheets connection
        try:
            df = await sheets_integration.get_advanced_stats()
            if df.empty:
                sheets_status = "⚠️ Connected but no data found"
            else:
                sheets_status = f"✅ Connected ({len(df)} teams loaded)"
        except Exception as e:
            if "Permission denied" in str(e):
                sheets_status = "❌ Permission denied - Sheet not shared with service account"
            elif "not found" in str(e).lower():
                sheets_status = "❌ Google Sheet not found"
            else:
                sheets_status = f"❌ Connection failed: {str(e)[:50]}..."
        
        # Get cache info
        cache_info = sheets_integration.get_cache_info()
        cache_status = f"Cache: {cache_info['status']} ({cache_info['records']} records)"
        
        status_msg = f"""
🤖 **Bot Status Report**

**Discord Connection:** ✅ Online and ready
**Google Sheets:** {sheets_status}
**Data Cache:** {cache_status}

**Need Help?**
If Google Sheets shows permission error, you need to:
1. Get the service account email from your Google Cloud Console
2. Share your Google Sheet with that email address
3. Grant "Viewer" permissions

Use `!help_betting` for command information.
        """
        await ctx.send(status_msg)
        
    except Exception as e:
        await ctx.send(f"❌ Error checking status: {str(e)}")

@bot.command(name="help_betting")
async def help_betting(ctx):
    """Show help information for betting commands"""
    help_text = """
🎲 **Sports Betting Bot Commands:**

**📊 Data Commands:**
• `!advanced_stats [count]` - Show top teams by advanced stats (default: 5)
• `!team_lookup <team_name>` - Look up specific team statistics
• `!refresh_data` - Manually refresh data from Google Sheets
• `!status` - Check bot and Google Sheets connection status

**🎯 Prediction Commands:**
• `!best_teams_to_win [count]` - Get best teams to bet on (default: 3)
• `!ev_plus_picks [count]` - Find EV+ betting opportunities with live odds (default: 5)
• `!top5_picks` - Get data-driven top 5 betting picks (combines stats + odds)

**⚙️ Utility Commands:**
• `!ping` - Test bot connectivity
• `!help_betting` - Show this help message

**💡 Tips:**
• All predictions are based on advanced statistical analysis
• Data is sourced from Google Sheets with real advanced metrics
• Remember to bet responsibly and within your means!

**⚠️ Disclaimer:** This bot provides analysis for informational purposes only. Always do your own research before placing any bets.
    """
    await ctx.send(help_text)

async def main():
    """Main function to run the bot"""
    # Get Discord token from environment
    discord_token = os.getenv('DISCORD_TOKEN')
    
    if not discord_token:
        print("❌ Error: DISCORD_TOKEN environment variable not set!")
        print("Please set your Discord bot token in the environment variables.")
        return
    
    try:
        # Start the bot
        await bot.start(discord_token)
    except discord.LoginFailure:
        print("❌ Error: Invalid Discord token!")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user.")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
