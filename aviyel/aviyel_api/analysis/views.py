"""HTTP layer for the keyword analysis endpoint.

POST collects a dataset for a keyword from the YouTube Data API.
GET runs the offline analysis over an already-collected dataset.

The view stays thin: collection lives in ``services.youtube`` and the maths in
``services.statistics``.
"""

import logging

import pandas as pd
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from analysis.services import statistics
from analysis.services.youtube import YouTubeClient, YouTubeUnavailable

logger = logging.getLogger(__name__)

# Keywords become filenames, so keep them to something safe.
MAX_KEYWORD_LENGTH = 64


def _safe_keyword(raw):
    """Validate a keyword and return it, or None when unusable."""
    if not raw or not isinstance(raw, str):
        return None
    keyword = raw.strip()
    if not keyword or len(keyword) > MAX_KEYWORD_LENGTH:
        return None
    # Reject anything that could escape the input/output directories.
    if any(ch in keyword for ch in ("/", "\\", "..", "\0")):
        return None
    return keyword


class AnalysisView(APIView):
    """Collect (POST) and analyse (GET) YouTube data for a keyword."""

    client_class = YouTubeClient

    def post(self, request):
        """Collect a dataset for the given keyword and write it to input_files/."""
        keyword = _safe_keyword(request.data.get("keyword"))
        if not keyword:
            return Response(
                {"message": "Please provide a 'keyword' string (1-64 chars)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rows = self.client_class().collect(keyword)
        except YouTubeUnavailable as exc:
            return Response(
                {"message": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        if not rows:
            return Response(
                {"message": f"No videos found for '{keyword}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        settings.INPUT_FILES_DIR.mkdir(parents=True, exist_ok=True)
        target = settings.INPUT_FILES_DIR / f"{keyword}.csv"
        pd.DataFrame(rows, columns=list(statistics.REQUIRED_COLUMNS)).to_csv(target)

        return Response(
            {
                "message": f"Input file generated for '{keyword}'.",
                "videos": len(rows),
                "file": target.name,
            },
            status=status.HTTP_201_CREATED,
        )

    def get(self, request):
        """Analyse the stored dataset for the given keyword."""
        keyword = _safe_keyword(request.GET.get("keyword"))
        if not keyword:
            return Response(
                {"message": "Please provide a 'keyword' query parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        source = settings.INPUT_FILES_DIR / f"{keyword}.csv"
        if not source.exists():
            available = sorted(p.stem for p in settings.INPUT_FILES_DIR.glob("*.csv"))
            return Response(
                {
                    "message": f"No input file for '{keyword}'. POST first to collect it.",
                    "available_keywords": available,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            frame = statistics.load_dataset(source)
            results = statistics.analyse(frame)
        except (ValueError, statistics.EmptyDataset) as exc:
            return Response(
                {"message": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        written = statistics.write_results(settings.OUTPUT_FILES_DIR, results)

        return Response(
            {
                "message": f"Analysis complete for '{keyword}'.",
                "videos_analysed": int(len(frame)),
                "categories": int(frame["category"].nunique()),
                "files": [p.name for p in written],
            },
            status=status.HTTP_200_OK,
        )
