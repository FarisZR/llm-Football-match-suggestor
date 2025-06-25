import time
import os
from football_suggester import config
from football_suggester.api_client import fetch_upcoming_games
from football_suggester.blacklist import load_blacklist, filter_games
from football_suggester.llm_handler import load_system_prompt, get_interesting_games
from football_suggester.calendar_manager import get_caldav_client, get_calendar, add_match_to_calendar

# Initialize logger from config
logger = config.get_logger(__name__)

def main():
    """
    Main function to run the football suggester service.
    """
    logger.info("Starting Football Suggester Service...")

    # --- Configuration Check ---
    if not config.API_FOOTBALL_KEY:
        logger.error("CRITICAL: API_FOOTBALL_KEY is not set. Service cannot proceed.")
        return
    if not config.CALDAV_URL: # CALDAV_USERNAME/PASSWORD might be in URL or not needed for public cals
        logger.error("CRITICAL: CALDAV_URL is not set. Service cannot proceed to add events.")
        # Depending on desired behavior, we could allow it to run up to LLM suggestions
        # but for now, let's assume calendar integration is key.
        return
    if not config.LLM_API_KEY or not config.LLM_MODEL:
        logger.warning("LLM_API_KEY or LLM_MODEL is not set. LLM suggestions will be skipped.")
        # Allow proceeding without LLM, perhaps just logging fetched games or similar?
        # For this service, LLM is core, so we might want to error out or have a fallback.
        # For now, it will try and fail in llm_handler, returning empty list.

    # --- Load Blacklist ---
    logger.info(f"Loading blacklist from: {config.BLACKLIST_FILE_PATH}")
    blacklist_rules = load_blacklist(config.BLACKLIST_FILE_PATH)
    if not os.path.exists(config.BLACKLIST_FILE_PATH): # load_blacklist logs a warning
        logger.info("No blacklist file found, so no blacklist rules will be applied beyond defaults in load_blacklist.")


    # --- Fetch Upcoming Games ---
    # Consider making days_ahead, league_id, season configurable if needed
    days_to_fetch = int(os.getenv('FETCH_DAYS_AHEAD', '7'))

    # --- Determine League Fetching Strategy ---
    all_games_raw = [] # Renamed to avoid confusion with `all_games` var name later if needed by other logic

    # Use a set to ensure league IDs are unique if TARGET_LEAGUE_ID overlaps with WHITELIST_MODE_LEAGUE_IDS
    # However, the logic below prioritizes WHITELIST_MODE_LEAGUE_IDS, so direct overlap isn't an issue.

    if config.WHITELIST_MODE_LEAGUE_IDS:
        logger.info(f"Whitelist mode active. Fetching games for league IDs: {config.WHITELIST_MODE_LEAGUE_IDS}")
        for league_id_wl in config.WHITELIST_MODE_LEAGUE_IDS:
            # Season is typically not required here, relying on date range.
            # TARGET_SEASON could be used globally if set, but usually None for whitelist mode.
            # For simplicity, season is not passed per whitelisted league, relying on global TARGET_SEASON if any.
            # However, it's better to keep it simple: season=None for whitelist mode.
            current_target_season = os.getenv('TARGET_SEASON', None) # Allow global season override if really needed

            logger.debug(f"Fetching for whitelisted league ID: {league_id_wl}, season: {current_target_season or 'None'}")
            games_for_league = fetch_upcoming_games(
                days_ahead=days_to_fetch,
                league_id=str(league_id_wl),
                season=current_target_season
            )
            if games_for_league:
                all_games_raw.extend(games_for_league)
            # Optional: Add a small delay between API calls if fetching many leagues to be polite to the API
            if len(config.WHITELIST_MODE_LEAGUE_IDS) > 1:
                time.sleep(0.5) # 0.5s delay if multiple leagues in whitelist

    elif os.getenv('TARGET_LEAGUE_ID'):
        target_league_id_str = os.getenv('TARGET_LEAGUE_ID')
        # TARGET_SEASON is optional, api_client handles it being None
        target_season_str = os.getenv('TARGET_SEASON', None)
        logger.info(f"Target league mode active. Fetching for League ID: {target_league_id_str}" +
                    (f", Season: {target_season_str}" if target_season_str else " (season not specified)."))

        all_games_raw = fetch_upcoming_games(
            days_ahead=days_to_fetch,
            league_id=target_league_id_str,
            season=target_season_str
        )
    else:
        logger.info(f"Broad mode active. Fetching all available games for the next {days_to_fetch} days. This may take a while and retrieve many games.")
        all_games_raw = fetch_upcoming_games(days_ahead=days_to_fetch)

    if not all_games_raw:
        logger.info("No upcoming games fetched based on the current strategy (Whitelist, Target League, or Broad). Run finished.")
        return
    logger.info(f"Fetched {len(all_games_raw)} games initially.")

    # --- Filter Games with Blacklist ---
    # Ensure blacklist_rules is defined (it's loaded earlier)
    filtered_games = filter_games(all_games_raw, blacklist_rules)

    if not filtered_games:
        logger.info("No games remaining after blacklist filtering. Run finished.")
        return
    logger.info(f"{len(filtered_games)} games remaining after blacklist filtering.")

    # --- Get Interesting Games from LLM ---
    # Load system prompt
    logger.info(f"Loading system prompt from: {config.SYSTEM_PROMPT_FILE_PATH}")
    system_prompt = load_system_prompt(config.SYSTEM_PROMPT_FILE_PATH)
    if not os.path.exists(config.SYSTEM_PROMPT_FILE_PATH): # load_system_prompt logs a warning
         logger.info("No system prompt file found, a default prompt will be used by the LLM handler.")


    suggested_fixture_ids = get_interesting_games(filtered_games, system_prompt)

    if not suggested_fixture_ids:
        logger.info("LLM did not suggest any games, or an error occurred. Exiting.")
        return

    logger.info(f"LLM suggested {len(suggested_fixture_ids)} games: {suggested_fixture_ids}")

    # Create a map of fixture_id to game_info for easy lookup
    games_map = {game['fixture']['id']: game for game in filtered_games if game.get('fixture')}

    suggested_games_info = []
    for fid in suggested_fixture_ids:
        if fid in games_map:
            suggested_games_info.append(games_map[fid])
        else:
            logger.warning(f"LLM suggested fixture ID {fid} which was not found in the filtered list. Skipping.")

    if not suggested_games_info:
        logger.info("None of the LLM suggested fixture IDs were found in the available games list. Exiting.")
        return

    # --- Add Suggested Games to Calendar ---
    caldav_client = get_caldav_client()
    if not caldav_client:
        logger.error("Failed to connect to CalDAV server. Cannot add events to calendar.")
        # Log the suggested games so user can manually add them?
        for game_to_log in suggested_games_info:
            home = game_to_log.get('teams',{}).get('home',{}).get('name','N/A')
            away = game_to_log.get('teams',{}).get('away',{}).get('name','N/A')
            date = game_to_log.get('fixture',{}).get('date','N/A')
            logger.info(f"Suggested game (not added to calendar): {home} vs {away} on {date} (ID: {game_to_log.get('fixture',{}).get('id')})")
        return

    calendar_obj = get_calendar(caldav_client) # Uses CALDAV_CALENDAR_NAME from config
    if not calendar_obj:
        logger.error("Failed to get a calendar. Cannot add events.")
        # Log suggested games
        for game_to_log in suggested_games_info:
            home = game_to_log.get('teams',{}).get('home',{}).get('name','N/A')
            away = game_to_log.get('teams',{}).get('away',{}).get('name','N/A')
            date = game_to_log.get('fixture',{}).get('date','N/A')
            logger.info(f"Suggested game (not added to calendar): {home} vs {away} on {date} (ID: {game_to_log.get('fixture',{}).get('id')})")
        return

    logger.info(f"Using calendar: {str(calendar_obj.url)}")

    successful_adds = 0
    failed_adds = 0
    for game_to_add in suggested_games_info:
        fixture_id_log = game_to_add.get('fixture', {}).get('id', 'N/A')
        logger.info(f"Attempting to add game ID {fixture_id_log} to calendar...")
        try:
            if add_match_to_calendar(game_to_add, calendar=calendar_obj):
                successful_adds += 1
            else:
                failed_adds += 1
        except Exception as e:
            logger.error(f"Unexpected error when trying to add game ID {fixture_id_log} to calendar: {e}", exc_info=True)
            failed_adds +=1

        # Optional: Add a small delay to avoid overwhelming the CalDAV server if adding many events
        # time.sleep(1)

    logger.info(f"Calendar processing complete. Successfully added: {successful_adds}, Failed to add: {failed_adds}.")
    logger.info("Football Suggester Service finished.")

if __name__ == "__main__":
    # Load .env file explicitly for local development when running main.py directly
    # config.py already does this if .env is in its expected relative path,
    # but this ensures it if main.py is run from project root and .env is also there.
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        logger.info(f"Loaded environment variables from {dotenv_path} for main execution.")
        # Re-initialize any config variables that might have been None before .env was loaded by config.py
        # This is a bit redundant if config.py always loads .env correctly relative to its own path.
        # However, explicit loading here can catch cases where CWD matters for .env loading.
        config.API_FOOTBALL_KEY = os.getenv('API_FOOTBALL_KEY')
        config.CALDAV_URL = os.getenv('CALDAV_URL')
        config.LLM_API_KEY = os.getenv('LLM_API_KEY')
        # etc. for other critical vars if needed

    main()
