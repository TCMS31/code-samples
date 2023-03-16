"""Tests for the keyword analysis sample.

The analysis layer is exercised against the real committed dataset
(``input_files/travel.csv``, 350 videos). The collection layer is exercised with
a stubbed YouTube client - no test makes a network call or needs an API key.
"""

import tempfile
from pathlib import Path
from unittest import mock

import pandas as pd
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from analysis.services import statistics
from analysis.services.youtube import YouTubeClient, YouTubeUnavailable

FIXTURE = Path(__file__).resolve().parent.parent / "aviyel_api" / "input_files"


class DatasetLoadingTests(SimpleTestCase):
    def test_loads_the_committed_travel_dataset(self):
        frame = statistics.load_dataset(FIXTURE / "travel.csv")
        self.assertEqual(len(frame), 350)
        for column in statistics.REQUIRED_COLUMNS:
            self.assertIn(column, frame.columns)

    def test_rejects_a_file_missing_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            pd.DataFrame({"video_id": ["a"]}).to_csv(path, index=False)
            with self.assertRaises(ValueError):
                statistics.load_dataset(path)

    def test_rejects_an_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.csv"
            pd.DataFrame(columns=list(statistics.REQUIRED_COLUMNS)).to_csv(
                path, index=False
            )
            with self.assertRaises(statistics.EmptyDataset):
                statistics.load_dataset(path)


class StatisticsTests(SimpleTestCase):
    """Exact arithmetic on a small hand-built frame."""

    def setUp(self):
        self.frame = pd.DataFrame(
            {
                "video_id": ["a", "b", "c", "d"],
                "category": ["Travel", "Travel", "Music", "Music"],
                "duration": [100.0, 200.0, 50.0, 400.0],
                "tags": ["['x']", "['y']", "['x']", None],
            }
        )

    def test_videos_per_category(self):
        self.assertEqual(
            statistics.videos_per_category(self.frame), {"Travel": 2, "Music": 2}
        )

    def test_average_duration_per_category(self):
        self.assertEqual(
            statistics.average_duration_per_category(self.frame),
            {"Music": 225.0, "Travel": 150.0},
        )

    def test_min_max_category_by_duration(self):
        result = statistics.min_max_category_by_duration(self.frame)
        self.assertEqual(result["Category with Max Duration"], "Music")
        self.assertEqual(result["Category with Min Duration"], "Music")

    def test_min_max_category_by_volume(self):
        result = statistics.min_max_category_by_volume({"a": 10, "b": 3, "c": 7})
        self.assertEqual(result["Category with Max Videos"], "a")
        self.assertEqual(result["Category with Min Videos"], "b")

    def test_tags_per_category_drops_nulls_and_dedupes(self):
        result = statistics.tags_per_category(self.frame)
        self.assertEqual(result["Travel"], ["['x']", "['y']"])
        self.assertEqual(result["Music"], ["['x']"])

    def test_empty_volume_comparison_raises(self):
        with self.assertRaises(statistics.EmptyDataset):
            statistics.min_max_category_by_volume({})

    def test_average_duration_on_real_dataset_is_positive(self):
        frame = statistics.load_dataset(FIXTURE / "travel.csv")
        averages = statistics.average_duration_per_category(frame)
        self.assertGreater(len(averages), 0)
        self.assertTrue(all(v > 0 for v in averages.values()))


class WriteResultsTests(SimpleTestCase):
    def test_writes_every_expected_file(self):
        frame = statistics.load_dataset(FIXTURE / "travel.csv")
        results = statistics.analyse(frame)
        with tempfile.TemporaryDirectory() as tmp:
            written = statistics.write_results(Path(tmp), results)
            self.assertEqual(len(written), 5)
            for path in written:
                self.assertTrue(path.exists())
                self.assertGreater(path.stat().st_size, 0)

    def test_creates_the_output_directory_if_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "does" / "not" / "exist"
            statistics.write_results(target, {"x.csv": ({"a": 1}, None)})
            self.assertTrue((target / "x.csv").exists())


class KeywordValidationTests(SimpleTestCase):
    def test_rejects_path_traversal(self):
        from analysis.views import _safe_keyword

        self.assertIsNone(_safe_keyword("../../etc/passwd"))
        self.assertIsNone(_safe_keyword("a/b"))
        self.assertIsNone(_safe_keyword(""))
        self.assertIsNone(_safe_keyword(None))
        self.assertIsNone(_safe_keyword(123))
        self.assertIsNone(_safe_keyword("x" * 65))

    def test_accepts_and_trims_a_normal_keyword(self):
        from analysis.views import _safe_keyword

        self.assertEqual(_safe_keyword("  travel "), "travel")


class AnalysisEndpointTests(APITestCase):
    def test_get_analyses_the_committed_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(INPUT_FILES_DIR=FIXTURE, OUTPUT_FILES_DIR=Path(tmp)):
                response = self.client.get(reverse("analysis"), {"keyword": "travel"})
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["videos_analysed"], 350)
                self.assertEqual(len(response.data["files"]), 5)
                self.assertTrue((Path(tmp) / "number_of_videos.csv").exists())

    def test_get_without_keyword_is_a_400(self):
        response = self.client.get(reverse("analysis"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_for_unknown_keyword_is_a_404_listing_what_exists(self):
        with override_settings(INPUT_FILES_DIR=FIXTURE):
            response = self.client.get(reverse("analysis"), {"keyword": "nosuchthing"})
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertIn("travel", response.data["available_keywords"])

    def test_post_without_keyword_is_a_400(self):
        response = self.client.post(reverse("analysis"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(GOOGLE_API_KEY="")
    def test_post_without_an_api_key_is_a_clear_503(self):
        """Regression: an absent key used to crash the whole project at import."""
        response = self.client.post(
            reverse("analysis"), {"keyword": "travel"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("GOOGLE_API_KEY", response.data["message"])

    def test_post_writes_an_input_file_from_collected_rows(self):
        rows = [
            {
                "video_id": "abc",
                "category": "Travel & Events",
                "duration": 120.0,
                "tags": "['x']",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(INPUT_FILES_DIR=Path(tmp)):
                with mock.patch.object(
                    YouTubeClient, "collect", return_value=rows
                ) as collect:
                    response = self.client.post(
                        reverse("analysis"), {"keyword": "demo"}, format="json"
                    )
                collect.assert_called_once_with("demo")
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(response.data["videos"], 1)
                self.assertTrue((Path(tmp) / "demo.csv").exists())


class YouTubeClientTests(SimpleTestCase):
    """The collection layer, driven by a stubbed API service."""

    def test_raises_a_clear_error_without_a_key(self):
        with self.assertRaises(YouTubeUnavailable):
            YouTubeClient(api_key="").service

    def test_search_uses_the_requested_keyword_on_every_page(self):
        """Regression: page 2+ searched a hardcoded unrelated string."""
        client = YouTubeClient(api_key="k")
        search = mock.Mock()
        search.list.return_value.execute.side_effect = [
            {"items": [{"id": {"videoId": "a"}}], "nextPageToken": "p2"},
            {"items": [{"id": {"videoId": "b"}}]},
        ]
        service = mock.Mock()
        service.search.return_value = search
        client._service = service

        ids = client.search_video_ids("travel", max_pages=3)

        self.assertEqual(ids, ["a", "b"])
        used_queries = [c.kwargs["q"] for c in search.list.call_args_list]
        self.assertEqual(used_queries, ["travel", "travel"])

    def test_search_stops_when_there_is_no_next_page(self):
        client = YouTubeClient(api_key="k")
        search = mock.Mock()
        search.list.return_value.execute.return_value = {
            "items": [{"id": {"videoId": "a"}}]
        }
        service = mock.Mock()
        service.search.return_value = search
        client._service = service

        client.search_video_ids("travel", max_pages=6)
        self.assertEqual(search.list.call_count, 1)

    def test_video_details_are_requested_in_batches_of_fifty(self):
        """Regression: this used to be one HTTP call per video."""
        client = YouTubeClient(api_key="k")
        videos = mock.Mock()
        videos.list.return_value.execute.return_value = {"items": []}
        service = mock.Mock()
        service.videos.return_value = videos
        client._service = service

        client.fetch_video_details([f"id{i}" for i in range(120)])

        self.assertEqual(videos.list.call_count, 3)
        first_batch = videos.list.call_args_list[0].kwargs["id"].split(",")
        self.assertEqual(len(first_batch), 50)

    def test_category_names_are_deduplicated_before_fetching(self):
        client = YouTubeClient(api_key="k")
        categories = mock.Mock()
        categories.list.return_value.execute.return_value = {
            "items": [{"id": "1", "snippet": {"title": "Film"}}]
        }
        service = mock.Mock()
        service.videoCategories.return_value = categories
        client._service = service

        names = client.fetch_category_names(["1"] * 200)

        self.assertEqual(categories.list.call_count, 1)
        self.assertEqual(names, {"1": "Film"})

    def test_collect_joins_details_to_category_names(self):
        client = YouTubeClient(api_key="k")
        with mock.patch.object(
            client, "search_video_ids", return_value=["v1"]
        ), mock.patch.object(
            client,
            "fetch_video_details",
            return_value=[
                {
                    "video_id": "v1",
                    "category_id": "19",
                    "duration": 90.0,
                    "tags": ["a"],
                }
            ],
        ), mock.patch.object(
            client, "fetch_category_names", return_value={"19": "Travel & Events"}
        ):
            rows = client.collect("travel")

        self.assertEqual(
            rows,
            [
                {
                    "video_id": "v1",
                    "category": "Travel & Events",
                    "duration": 90.0,
                    "tags": ["a"],
                }
            ],
        )

    def test_collect_returns_empty_when_search_finds_nothing(self):
        client = YouTubeClient(api_key="k")
        with mock.patch.object(client, "search_video_ids", return_value=[]):
            self.assertEqual(client.collect("nothing"), [])
