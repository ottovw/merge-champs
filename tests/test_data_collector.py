import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from src.data_collector import DataCollector, GitLabDataCollector
from src.config import config


class DataCollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_config = {
            "gitlab_token": config.gitlab_token,
            "project_id": config.project_id,
            "group_id": config.group_id,
            "team_members": list(config.team_members),
            "mr_weight_rules": list(config.mr_weight_rules),
        }

    def tearDown(self) -> None:
        config.gitlab_token = self._original_config["gitlab_token"]
        config.project_id = self._original_config["project_id"]
        config.group_id = self._original_config["group_id"]
        config.team_members = self._original_config["team_members"]
        config.mr_weight_rules = list(self._original_config["mr_weight_rules"])

    @patch("src.data_collector.requests.get")
    def test_collects_project_requests_filtered_by_team(self, mock_get) -> None:
        config.gitlab_token = "test-token"
        config.project_id = "123"
        config.group_id = ""
        config.team_members = ["alice", "bob", "carol"]
        config.mr_weight_rules = []

        mock_response = SimpleNamespace(
            json=lambda: [
                {"author": {"username": "alice"}, "title": "MR 1"},
                {"author": {"username": "dave"}, "title": "MR 2"},
                {"author": {"username": "bob"}, "title": "MR 3"},
            ],
            raise_for_status=lambda: None,
        )
        mock_get.return_value = mock_response

        collector = DataCollector()
        aggregate = collector.get_weekly_data(reference=datetime(2025, 9, 26))

        self.assertAlmostEqual(aggregate.raw["alice"], 1.0)
        self.assertAlmostEqual(aggregate.raw["bob"], 1.0)
        self.assertAlmostEqual(aggregate.raw["carol"], 0.0)
        self.assertAlmostEqual(aggregate.weighted["alice"], 1.0)
        self.assertAlmostEqual(aggregate.weighted["bob"], 1.0)
        self.assertAlmostEqual(aggregate.weighted["carol"], 0.0)
        mock_get.assert_called_once()

    @patch("src.data_collector.requests.get")
    def test_collects_group_requests_across_pages(self, mock_get) -> None:
        config.gitlab_token = "test-token"
        config.project_id = ""
        config.group_id = "456"
        config.team_members = ["alice", "bob"]
        config.mr_weight_rules = []

        page_one_payload = [
            {"author": {"username": f"user{i}"}, "title": f"MR {i}", "project": {"name": "A"}}
            for i in range(99)
        ] + [
            {"author": {"username": "alice"}, "title": "MR 100", "project": {"name": "A"}},
        ]
        page_one = SimpleNamespace(
            json=lambda: page_one_payload,
            raise_for_status=lambda: None,
        )
        page_two_payload = [
            {"author": {"username": "bob"}, "title": "MR 101", "project": {"name": "B"}},
        ]
        page_two = SimpleNamespace(
            json=lambda: page_two_payload,
            raise_for_status=lambda: None,
        )
        pages_seen: list[int] = []

        def fake_get(url, *, headers=None, params=None):  # type: ignore[override]
            page_number = params.get("page", 1) if params else 1
            pages_seen.append(page_number)
            if page_number == 1:
                return page_one
            if page_number == 2:
                return page_two
            return SimpleNamespace(json=lambda: [], raise_for_status=lambda: None)

        mock_get.side_effect = fake_get

        collector = DataCollector()
        aggregate = collector.get_monthly_data(reference=datetime(2025, 9, 1))

        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(pages_seen, [1, 2])
        self.assertAlmostEqual(aggregate.raw["alice"], 1.0)
        self.assertAlmostEqual(aggregate.raw["bob"], 1.0)
        self.assertAlmostEqual(aggregate.weighted["alice"], 1.0)
        self.assertAlmostEqual(aggregate.weighted["bob"], 1.0)

    @patch("src.data_collector.GitLabDataCollector.get_merge_request_changes_count")
    @patch("src.data_collector.requests.get")
    def test_weighted_counts_fetch_lines_when_missing(self, mock_get, mock_changes_count) -> None:
        config.gitlab_token = "test-token"
        config.project_id = ""
        config.group_id = "456"
        config.team_members = ["alice"]
        config.mr_weight_rules = [(20, 0.3), (80, 0.6), (200, 1.0)]

        mr_payload = [
            {
                "author": {"username": "alice"},
                "title": "MR 1",
                "iid": 101,
                "project_id": 999,
                # No statistics or changes_count included
            }
        ]

        mock_get.return_value = SimpleNamespace(
            json=lambda: mr_payload,
            raise_for_status=lambda: None,
        )
        mock_changes_count.return_value = 10

        collector = DataCollector()
        aggregate = collector.get_weekly_data(reference=datetime(2025, 9, 26))

        mock_changes_count.assert_called_once_with("999", 101)
        self.assertAlmostEqual(aggregate.raw["alice"], 1.0)
        # With 10 lines changed, the 0.3 weight applies
        self.assertAlmostEqual(aggregate.weighted["alice"], 0.3)

    @patch("src.data_collector.requests.get")
    def test_gitlab_collector_falls_back_to_changes_endpoint(self, mock_get) -> None:
        collector = GitLabDataCollector("token", gitlab_url="https://gitlab.example.com")

        detail_payload: dict[str, object] = {}

        changes_payload = {
            "changes": [
                {"diff": "@@ -1,2 +1,3 @@\n-foo\n+foo\n+bar"},
                {"diff": "@@ -3 +2 @@\n-baz"},
            ]
        }

        detail_response = SimpleNamespace(
            json=lambda: detail_payload,
            raise_for_status=lambda: None,
        )
        changes_response = SimpleNamespace(
            json=lambda: changes_payload,
            raise_for_status=lambda: None,
        )

        mock_get.side_effect = [detail_response, changes_response]

        total = collector.get_merge_request_changes_count("123", 456)

        # Diff parsing yields 2 additions (foo, bar) and 2 deletions (foo, baz) -> 4 lines changed
        self.assertEqual(total, 4)
        self.assertEqual(mock_get.call_count, 2)
        requested_urls = [call_args[0][0] for call_args in mock_get.call_args_list]
        self.assertIn("/projects/123/merge_requests/456", requested_urls[0])
        self.assertTrue(requested_urls[1].endswith("/projects/123/merge_requests/456/changes"))

    def test_configuration_validation(self) -> None:
        config.gitlab_token = "token"
        config.project_id = ""
        config.group_id = ""

        collector = DataCollector()
        self.assertFalse(collector.has_valid_configuration())

        config.group_id = "456"
        collector = DataCollector()
        self.assertTrue(collector.has_valid_configuration())


if __name__ == "__main__":
    unittest.main()
