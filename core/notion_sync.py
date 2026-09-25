"""
Push a mission straight into a Notion database.

Setup (one-time):
1. Go to https://www.notion.so/my-integrations and create a new integration.
   Copy the "Internal Integration Secret" / "Access token" -> this is NOTION_TOKEN.
2. Create a Notion database (a table) with these properties:
     - Name       -> Title
     - Priority   -> Select   (add options: High, Medium, Low)
     - Intent     -> Select   (add options: task, content_creation)
     - Status     -> Checkbox
3. Open the database, click "..." -> "Connections" -> add your integration.
4. Copy the database ID from its URL:
     https://www.notion.so/yourspace/<DATABASE_ID>?v=...
   Use only the 32-character id itself -- no "p/" prefix, no "?v=..." suffix.
5. Put both values in your .env file.

Note on Notion's "data sources" model (rolled out Sept 2025): a database is
now a container that can hold one or more data sources, and creating a page
requires a data_source_id rather than a database_id. This module looks up
the data source id for you the first time it's needed and caches it, so you
only ever need to set NOTION_DATABASE_ID in your .env file.
"""

import os
import re

from notion_client import Client

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
_raw_database_id = os.getenv("NOTION_DATABASE_ID", "")
# Strip anything that isn't part of the actual id (a stray "p/" prefix from
# copy-pasting a page-style URL, a "?v=..." view suffix, surrounding spaces).
NOTION_DATABASE_ID = re.sub(r"[^0-9a-fA-F-]", "", _raw_database_id.split("?")[0].split("/")[-1]) or None

_client = Client(auth=NOTION_TOKEN) if NOTION_TOKEN else None
_data_source_id_cache = None


def notion_configured() -> bool:
    return bool(NOTION_TOKEN and NOTION_DATABASE_ID)


def _get_data_source_id():
    """Resolves and caches the data_source_id for NOTION_DATABASE_ID.
    Falls back to NOTION_DATABASE_ID itself if the account/library is on an
    older Notion API version that has no concept of data sources.
    """
    global _data_source_id_cache
    if _data_source_id_cache:
        return _data_source_id_cache
    try:
        database = _client.databases.retrieve(database_id=NOTION_DATABASE_ID)
        sources = database.get("data_sources") or []
        if sources:
            _data_source_id_cache = sources[0]["id"]
            return _data_source_id_cache
    except Exception as e:
        print(f"Could not resolve Notion data source, falling back to database_id: {e}")
    return NOTION_DATABASE_ID


def push_to_notion(mission: dict):
    """Creates a page in the configured Notion database for a mission.
    Returns the new page id on success, or None on failure.
    """
    if not notion_configured():
        return None

    properties = {
        "Name": {"title": [{"text": {"content": mission.get("title", "Untitled")}}]},
        "Priority": {"select": {"name": mission.get("priority", "medium").capitalize()}},
        "Intent": {"select": {"name": mission.get("intent", "task")}},
        "Status": {"checkbox": mission.get("done", False)},
    }

    data_source_id = _get_data_source_id()
    try:
        page = _client.pages.create(
            parent={"type": "data_source_id", "data_source_id": data_source_id},
            properties=properties,
        )
        return page["id"]
    except Exception as e:
        # Older Notion accounts/API versions don't use data sources at all --
        # retry once with a plain database_id parent before giving up.
        try:
            page = _client.pages.create(
                parent={"type": "database_id", "database_id": NOTION_DATABASE_ID},
                properties=properties,
            )
            return page["id"]
        except Exception as e2:
            print(f"Notion push failed: {e}; retry with database_id also failed: {e2}")
            return None
