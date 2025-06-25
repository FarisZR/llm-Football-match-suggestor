import caldav
from caldav.lib.error import DAVError, AuthorizationError, ProppatchError
from datetime import datetime, timedelta, timezone
import pytz # For robust timezone handling
from football_suggester.config import get_logger, CALDAV_URL, CALDAV_USERNAME, CALDAV_PASSWORD, CALDAV_CALENDAR_NAME

logger = get_logger(__name__)

# VEVENT template for creating calendar events
VEVENT_TEMPLATE = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//FootballSuggester//NONSGML v1.0//EN
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{dtstamp}
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:{summary}
DESCRIPTION:{description}
LOCATION:{location}
END:VEVENT
END:VCALENDAR
"""

def get_caldav_client(url=None, username=None, password=None):
    """
    Connects to the CalDAV server and returns a client object.
    Uses configuration from config.py if parameters are not provided.
    """
    url = url or CALDAV_URL
    username = username or CALDAV_USERNAME
    password = password or CALDAV_PASSWORD

    if not url:
        logger.error("CalDAV URL is not configured. Cannot connect to calendar server.")
        return None

    try:
        # If username and password are in the URL, caldav library might handle it.
        # Otherwise, pass them explicitly.
        if username and password:
            client = caldav.DAVClient(url=url, username=username, password=password)
        else:
            # This handles URLs that might have embedded credentials or use other auth methods if supported by the server
            client = caldav.DAVClient(url=url)

        logger.info(f"Successfully connected to CalDAV server at {url.split('@')[-1] if '@' in url else url}") # Avoid logging credentials
        return client
    except (DAVError, AuthorizationError) as e:
        logger.error(f"Failed to connect to CalDAV server at {url.split('@')[-1] if '@' in url else url}. Error: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while connecting to CalDAV server: {e}")
        return None


def get_calendar(client: caldav.DAVClient, calendar_name: str = None):
    """
    Retrieves a specific calendar from the CalDAV server.
    If calendar_name is provided, it tries to find that calendar.
    Otherwise, it tries to get the principal's primary calendar or the first available one.
    """
    calendar_name = calendar_name or CALDAV_CALENDAR_NAME

    try:
        principal = client.principal()
        calendars = principal.calendars()

        if not calendars:
            logger.error("No calendars found for the user.")
            return None

        if calendar_name:
            for cal in calendars:
                # Calendar display name might be in cal.name or cal.get_property("DAV::displayname")
                # cal.name is often the URL component. Let's try displayname if available.
                display_name_prop = cal.get_property("DAV::displayname")
                if display_name_prop and str(display_name_prop) == calendar_name:
                    logger.info(f"Found calendar by display name: '{calendar_name}'")
                    return cal
                # Fallback to checking cal.name or part of URL if displayname doesn't match
                if calendar_name in str(cal.url): # cal.name might be just the ID/URL part
                     logger.info(f"Found calendar by URL component: '{calendar_name}' in {cal.url}")
                     return cal
            logger.warning(f"Calendar with name/URL component '{calendar_name}' not found. Will try to use the first available calendar.")
            # If specific calendar not found by name, could fall back to first or error
            # For now, let's be strict if a name was given.
            logger.error(f"Specified calendar '{calendar_name}' not found. Available calendars: {[str(c.get_property('DAV::displayname') or c.url) for c in calendars]}")
            return None

        # If no specific name, try to find a common default or just use the first one
        # Common default names: 'calendar', 'default', 'events'
        default_names = ['calendar', 'default', 'events']
        for cal in calendars:
            display_name_prop = cal.get_property("DAV::displayname")
            if display_name_prop and str(display_name_prop).lower() in default_names:
                 logger.info(f"Using calendar '{str(display_name_prop)}' as a default.")
                 return cal

        logger.info(f"No specific or default calendar name matched. Using the first available calendar: {str(calendars[0].get_property('DAV::displayname') or calendars[0].url)}")
        return calendars[0] # Return the first calendar if no name is specified or matched

    except DAVError as e:
        logger.error(f"Error accessing calendars: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting calendar: {e}")
        return None


def _generate_event_uid(fixture_id: int) -> str:
    """Generates a unique ID for the event based on the fixture ID."""
    return f"football-suggester-fixture-{fixture_id}@my-domain.com" # Domain can be arbitrary

def _format_datetime_for_caldav(dt_str: str) -> str:
    """
    Parses an ISO 8601 datetime string and formats it for CalDAV (YYYYMMDDTHHMMSSZ).
    Ensures the datetime is in UTC.
    """
    try:
        dt_obj = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        # Ensure it's UTC
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc) # Assume UTC if no tzinfo
        else:
            dt_obj = dt_obj.astimezone(timezone.utc)
        return dt_obj.strftime("%Y%m%dT%H%M%SZ")
    except ValueError:
        logger.error(f"Could not parse date string: {dt_str}. Using current time as fallback.")
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def add_match_to_calendar(game_info: dict, calendar: caldav.Calendar = None) -> bool:
    """
    Adds a single football match to the specified CalDAV calendar.

    Args:
        game_info (dict): A dictionary containing the match details.
                          Expected keys: 'fixture', 'league', 'teams'.
                          'fixture' should have 'id', 'date', 'venue.name', 'venue.city'.
                          'league' should have 'name', 'country', 'round'.
                          'teams' should have 'home.name', 'away.name'.
        calendar (caldav.Calendar, optional): The caldav.Calendar object to add the event to.
                                              If None, will try to connect and get a calendar.

    Returns:
        bool: True if the event was added successfully, False otherwise.
    """
    if not calendar:
        client = get_caldav_client()
        if not client: return False
        calendar_obj = get_calendar(client)
        if not calendar_obj: return False
        # This is a bit problematic as `calendar` is used as a parameter name and a local var
        # Let's rename the local var to avoid confusion
        target_calendar = calendar_obj
    else:
        target_calendar = calendar


    try:
        fixture = game_info.get('fixture', {})
        league = game_info.get('league', {})
        teams = game_info.get('teams', {})
        venue = fixture.get('venue', {})

        fixture_id = fixture.get('id')
        if not fixture_id:
            logger.error("Fixture ID missing, cannot create calendar event.")
            return False

        uid = _generate_event_uid(fixture_id)

        # Check if event already exists by UID
        try:
            existing_event = target_calendar.event_by_uid(uid)
            if existing_event:
                logger.info(f"Event for fixture ID {fixture_id} (UID: {uid}) already exists. Skipping.")
                # Optionally, update the event here if needed:
                # existing_event.data = new_vevent_data
                # existing_event.save()
                return True # Considered success as event is present
        except caldav.error.NotFoundError:
            logger.debug(f"No existing event found for UID {uid}. Proceeding to create.")
        except Exception as e: # Broad catch for other potential issues with event_by_uid
            logger.warning(f"Could not reliably check for existing event UID {uid} due to: {e}. Will attempt to create.")


        dt_start_str = fixture.get('date')
        if not dt_start_str:
            logger.error(f"Fixture date missing for ID {fixture_id}. Cannot create event.")
            return False

        dt_start_caldav = _format_datetime_for_caldav(dt_start_str)

        # Assume match duration of 2 hours if not specified
        dt_start_obj = datetime.fromisoformat(dt_start_str.replace("Z", "+00:00"))
        if dt_start_obj.tzinfo is None: # Ensure it's timezone-aware for arithmetic
            dt_start_obj = pytz.utc.localize(dt_start_obj)
        else:
            dt_start_obj = dt_start_obj.astimezone(pytz.utc)

        dt_end_obj = dt_start_obj + timedelta(hours=2)
        dt_end_caldav = dt_end_obj.strftime("%Y%m%dT%H%M%SZ")

        dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        home_team = teams.get('home', {}).get('name', 'N/A')
        away_team = teams.get('away', {}).get('name', 'N/A')
        summary = f"⚽️ {home_team} vs {away_team} ({league.get('name', 'League')})"

        description_parts = [
            f"Match: {home_team} vs {away_team}",
            f"League: {league.get('name', 'N/A')}, {league.get('country', 'N/A')}",
            f"Round: {league.get('round', 'N/A')}",
            f"Fixture ID: {fixture_id}",
            f"Kick-off: {dt_start_str}",
        ]
        if venue.get('name') and venue.get('city'):
            description_parts.append(f"Venue: {venue.get('name')}, {venue.get('city')}")

        description = "\\n".join(description_parts) # \n for VEVENT newlines

        location = f"{venue.get('name', '')}, {venue.get('city', '')}".strip(', ')


        vevent_data = VEVENT_TEMPLATE.format(
            uid=uid,
            dtstamp=dtstamp,
            dtstart=dt_start_caldav,
            dtend=dt_end_caldav,
            summary=summary,
            description=description,
            location=location
        )

        # Validate the VEVENT data (optional, basic check)
        if "BEGIN:VCALENDAR" not in vevent_data or "END:VEVENT" not in vevent_data:
            logger.error(f"Generated VEVENT data appears malformed for fixture {fixture_id}.")
            return False

        logger.debug(f"Attempting to add event to calendar '{str(target_calendar.url)}':\n{vevent_data}")

        # Using calendar.save_event or add_event
        # add_event is simpler if you have the string
        event_resource = target_calendar.add_event(ical=vevent_data)
        # event_resource.save() # add_event typically saves it. If using `calendar.new_event()`, then save() is needed.
        # The caldav library's add_event method directly creates and uploads the event.

        logger.info(f"Successfully added event for fixture ID {fixture_id} ({home_team} vs {away_team}) to calendar.")
        return True

    except ProppatchError as pe: # Often related to permissions or server issues with properties
        logger.error(f"ProppatchError while adding event for fixture {fixture_id}: {pe}. This might be a permissions issue or server misconfiguration.")
        return False
    except DAVError as e:
        logger.error(f"DAVError adding event for fixture {fixture_id} ({game_info.get('fixture',{}).get('id')}): {e}")
        if hasattr(e, 'reason') and e.reason: logger.error(f"Reason: {e.reason}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error adding event for fixture {fixture_id}: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    # This is for basic testing of the module.
    # Ensure your .env file is populated with CALDAV_* variables.
    from football_suggester.config import load_dotenv, PROJECT_ROOT, logger as cfg_logger
    import os

    dotenv_path_for_test = os.path.join(PROJECT_ROOT, '.env')
    if os.path.exists(dotenv_path_for_test):
        load_dotenv(dotenv_path_for_test)
        # Re-evaluate CALDAV vars
        CALDAV_URL = os.getenv('CALDAV_URL')
        CALDAV_USERNAME = os.getenv('CALDAV_USERNAME')
        CALDAV_PASSWORD = os.getenv('CALDAV_PASSWORD')
        CALDAV_CALENDAR_NAME = os.getenv('CALDAV_CALENDAR_NAME')
        cfg_logger.info("Reloaded .env for calendar_manager test.")

    if not CALDAV_URL:
        cfg_logger.warning("CALDAV_URL not set. Skipping live CalDAV test.")
    else:
        cfg_logger.info("Attempting to connect to CalDAV server and add a test event...")

        # Sample game_info (as if from api_client)
        sample_game = {
            "fixture": {
                "id": 999901, # Unique ID for testing
                "date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), # Tomorrow
                "venue": {"name": "Test Stadium", "city": "Testville"}
            },
            "league": {
                "name": "Test League", "country": "Testland", "round": "Test Round 1"
            },
            "teams": {
                "home": {"name": "Test Home FC"}, "away": {"name": "Test Away United"}
            }
        }

        client = get_caldav_client()
        if client:
            calendar_to_use = get_calendar(client) # Use configured name or find default
            if calendar_to_use:
                cfg_logger.info(f"Using calendar: {str(calendar_to_use.url)}")
                success = add_match_to_calendar(sample_game, calendar=calendar_to_use)
                if success:
                    cfg_logger.info(f"Test event for fixture ID {sample_game['fixture']['id']} should be added (or was skipped if existing).")
                    cfg_logger.info("Please check your calendar. You may want to manually delete this test event.")

                    # Test idempotency: try adding the same event again
                    cfg_logger.info("Trying to add the same event again to test idempotency...")
                    success_again = add_match_to_calendar(sample_game, calendar=calendar_to_use)
                    if success_again:
                         cfg_logger.info(f"Second attempt to add fixture ID {sample_game['fixture']['id']} also reported success (expected if skipped).")
                    else:
                         cfg_logger.error(f"Second attempt to add fixture ID {sample_game['fixture']['id']} failed unexpectedly.")

                else:
                    cfg_logger.error(f"Failed to add test event for fixture ID {sample_game['fixture']['id']}.")
            else:
                cfg_logger.error("Could not retrieve a calendar to add the event to.")
        else:
            cfg_logger.error("Failed to connect to CalDAV server.")

    cfg_logger.info("Calendar manager test finished.")
