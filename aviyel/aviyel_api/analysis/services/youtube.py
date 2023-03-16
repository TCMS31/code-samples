"""YouTube Data API collection layer.

Everything that talks to Google lives here. The client is built lazily on first
use rather than at import time: building it at import made the whole Django
project unimportable (``manage.py check``, ``test`` and ``runserver`` all raised
``DefaultCredentialsError``) whenever ``GOOGLE_API_KEY`` was unset.
"""

import logging

import isodate
from django.conf import settings
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# The Data API accepts up to 50 ids per videos.list / videoCategories.list call.
API_BATCH_SIZE = 50
SEARCH_PAGE_SIZE = 50


class YouTubeUnavailable(RuntimeError):
    """Raised when no API key is configured."""


class YouTubeClient:
    """Thin wrapper over the YouTube Data API v3."""

    def __init__(self, api_key=None):
        self._api_key = api_key if api_key is not None else settings.GOOGLE_API_KEY
        self._service = None

    @property
    def service(self):
        if not self._api_key:
            raise YouTubeUnavailable(
                "GOOGLE_API_KEY is not set. Add it to .env to collect new data; "
                "existing input files under input_files/ can still be analysed."
            )
        if self._service is None:
            # static_discovery avoids a network round-trip for the discovery doc.
            self._service = build(
                "youtube",
                "v3",
                developerKey=self._api_key,
                cache_discovery=False,
                static_discovery=True,
            )
        return self._service

    def search_video_ids(self, keyword, max_pages=6):
        """Return video ids matching ``keyword``.

        The original implementation searched ``keyword`` for page 1 and then a
        hardcoded unrelated string for every subsequent page, so roughly 6/7 of
        the collected data had nothing to do with the requested keyword.
        """
        video_ids = []
        page_token = None

        for _ in range(max_pages):
            request = self.service.search().list(
                q=keyword,
                part="snippet",
                type="video",
                maxResults=SEARCH_PAGE_SIZE,
                pageToken=page_token,
            )
            result = request.execute()
            video_ids.extend(
                item["id"]["videoId"]
                for item in result.get("items", [])
                if item.get("id", {}).get("videoId")
            )
            page_token = result.get("nextPageToken")
            if not page_token:
                break

        return video_ids

    def _chunks(self, items):
        for start in range(0, len(items), API_BATCH_SIZE):
            yield items[start : start + API_BATCH_SIZE]

    def fetch_video_details(self, video_ids):
        """Return ``[{video_id, category_id, duration, tags}, ...]``.

        Ids are requested 50 at a time. The original code issued one
        ``videos.list`` *and* one ``videoCategories.list`` per video, i.e. about
        700 sequential HTTP calls for a 350-video keyword.
        """
        details = []
        for chunk in self._chunks(video_ids):
            request = self.service.videos().list(
                id=",".join(chunk), part="snippet,contentDetails"
            )
            for item in request.execute().get("items", []):
                details.append(
                    {
                        "video_id": item["id"],
                        "category_id": item["snippet"]["categoryId"],
                        "duration": isodate.parse_duration(
                            item["contentDetails"]["duration"]
                        ).total_seconds(),
                        "tags": item["snippet"].get("tags"),
                    }
                )
        return details

    def fetch_category_names(self, category_ids):
        """Return ``{category_id: title}`` for the given ids, batched."""
        names = {}
        unique_ids = sorted(set(category_ids))
        for chunk in self._chunks(unique_ids):
            request = self.service.videoCategories().list(
                id=",".join(chunk), part="snippet"
            )
            for item in request.execute().get("items", []):
                names[item["id"]] = item["snippet"]["title"]
        return names

    def collect(self, keyword, max_pages=6):
        """Collect ``[{video_id, category, duration, tags}, ...]`` for a keyword."""
        video_ids = self.search_video_ids(keyword, max_pages=max_pages)
        if not video_ids:
            return []

        details = self.fetch_video_details(video_ids)
        category_names = self.fetch_category_names([d["category_id"] for d in details])

        return [
            {
                "video_id": d["video_id"],
                "category": category_names.get(d["category_id"], "Unknown"),
                "duration": d["duration"],
                "tags": d["tags"],
            }
            for d in details
        ]
