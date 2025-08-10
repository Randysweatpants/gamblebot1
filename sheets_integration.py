import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import asyncio
import logging
import os
from datetime import datetime, timedelta
import json
from collections import defaultdict

logger = logging.getLogger(__name__)

class SheetsIntegration:
    def __init__(self):
        self.client = None
        self.cached_data = None
        self.cache_timestamp = None
        self.cache_duration = timedelta(minutes=15)
        self.sheet_url = "https://docs.google.com/spreadsheets/d/11EyxXDDChFD91Be-_K5oMbLxbejIAUP6O54_pONAcPA/edit"

    def _initialize_client(self):
        try:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly"
            ]
            credentials_file = "google-credentials.json"
            if os.path.exists(credentials_file):
                logger.info("Loading credentials from google-credentials.json")
                creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
            else:
                creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
                if creds_json:
                    logger.info("Loading credentials from environment variable")
                    creds_dict = json.loads(creds_json)
                    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                else:
                    raise Exception("No Google credentials found.")
            self.client = gspread.authorize(creds)
            logger.info("Google Sheets client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            raise

    def _is_cache_valid(self):
        return self.cached_data is not None and self.cache_timestamp and (datetime.now() - self.cache_timestamp < self.cache_duration)

    async def get_advanced_stats(self, force_refresh=False):
        try:
            if not force_refresh and self._is_cache_valid():
                logger.info("Returning cached data")
                return self.cached_data.copy()

            if not self.client:
                self._initialize_client()

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._fetch_sheet_data)
            df = pd.DataFrame(data)

            if df.empty:
                logger.warning("No data retrieved from Google Sheets")
                return pd.DataFrame()

            df = self._process_data(df)
            self.cached_data = df.copy()
            self.cache_timestamp = datetime.now()

            logger.info(f"Successfully fetched {len(df)} records from Google Sheets")
            return df
        except Exception as e:
            logger.error(f"Error fetching data from Google Sheets: {e}")
            if self.cached_data is not None:
                logger.info("Returning expired cached data due to fetch error")
                return self.cached_data.copy()
            raise

    def _fetch_sheet_data(self):
        try:
            sheet = self.client.open_by_url(self.sheet_url)
            pitching_ws = sheet.worksheet("Pitching Stats")
            batting_ws = sheet.worksheet("Batting Stats")

            pitching_data = pitching_ws.get_all_records()
            batting_data = batting_ws.get_all_records()

            logger.info(f"Fetched {len(pitching_data)} records from worksheet: {pitching_ws.title}")
            logger.info(f"Fetched {len(batting_data)} records from worksheet: {batting_ws.title}")

            pitching_by_team = {}
            for row in pitching_data:
                team = row.get("Team")
                if team:
                    team_key = team.strip().lower()
                    if team_key not in pitching_by_team:
                        pitching_by_team[team_key] = row

            batting_by_team = {}
            for row in batting_data:
                team = row.get("Team")
                if team:
                    team_key = team.strip().lower()
                    if team_key not in batting_by_team:
                        batting_by_team[team_key] = row

            merged = {}
            for team_key in pitching_by_team:
                if team_key in batting_by_team:
                    merged_row = {}
                    merged_row.update(pitching_by_team[team_key])
                    merged_row.update(batting_by_team[team_key])
                    merged[team_key] = merged_row

            combined_data = list(merged.values())
            logger.info(f"Merged data: {len(combined_data)} combined team records from Batting + Pitching")
            return combined_data
        except Exception as e:
            raise Exception(f"Unexpected error accessing Google Sheets: {str(e)}")

    def _process_data(self, df):
        try:
            team_col = None
            if 'Teams' in df.columns:
                team_col = 'Teams'
            elif 'Team' in df.columns:
                team_col = 'Team'
            else:
                logger.warning("No 'Teams' or 'Team' column found in data")
                return pd.DataFrame()

            if team_col == 'Teams':
                df = df.rename(columns={'Teams': 'Team'})

            df = df[df['Team'].notna() & (df['Team'] != '')]

            numeric_columns = [
                'XBA', 'XSLG', 'WOBA', 'BA', 'OBP', 'SLG', 'XWOBA',
                'Exit Velocity', 'Launch Angle', 'Hard Hit %', 'Barrel %',
                'ERA', 'WHIP'
            ]

            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            if 'WOBA' in df.columns:
                df = df.sort_values('WOBA', ascending=False)
            elif 'XWOBA' in df.columns:
                df = df.sort_values('XWOBA', ascending=False)

            df = df.reset_index(drop=True)

            logger.info(f"Processed data: {len(df)} teams with columns: {list(df.columns)}")
            return df
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            return df

    def get_cache_info(self):
        if not self.cached_data:
            return {"status": "no_cache", "records": 0, "age": None}

        cache_age = datetime.now() - self.cache_timestamp if self.cache_timestamp else None
        is_valid = self._is_cache_valid()

        return {
            "status": "valid" if is_valid else "expired",
            "records": len(self.cached_data),
            "age": cache_age.total_seconds() if cache_age else None,
            "age_minutes": cache_age.total_seconds() / 60 if cache_age else None
        }




