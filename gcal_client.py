# gcal_client.py

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from httpx_oauth.oauth2 import OAuth2Token
import datetime

def build_credentials(token: OAuth2Token) -> Credentials:
    return Credentials(
        token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=None,
        client_secret=None,
        scopes=token.get("scope").split()
    )

def build_service(creds: Credentials,
                  api_name: str = "calendar",
                  api_version: str = "v3"):
    return build(api_name, api_version, credentials=creds)

def list_events(service,
                calendar_id: str = "primary",
                time_min: datetime.datetime = None,
                time_max: datetime.datetime = None,
                max_results: int = 250) -> list[dict]:
    """Lista eventos en un rango, gestionando paginación."""
    if time_min is None:
        time_min = datetime.datetime.utcnow()
    if time_max is None:
        time_max = time_min + datetime.timedelta(days=7)

    iso_min = time_min.isoformat() + "Z"
    iso_max = time_max.isoformat() + "Z"

    events = []
    page_token = None

    while True:
        resp = service.events().list(
            calendarId=calendar_id,
            timeMin=iso_min,
            timeMax=iso_max,
            singleEvents=True,
            orderBy="startTime",
            maxResults=max_results,
            pageToken=page_token
        ).execute()
        events.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return events

def upsert_event(service,
                 event_body: dict,
                 calendar_id: str = "primary",
                 event_id: str | None = None) -> dict:
    """Inserta o actualiza un evento según event_id."""
    if event_id:
        return service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_body
        ).execute()
    else:
        return service.events().insert(
            calendarId=calendar_id,
            body=event_body
        ).execute()
