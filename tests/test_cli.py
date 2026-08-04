import unittest
from unittest.mock import Mock

from zo_repo_task.cli import format_repo_text, format_repos_table, list_repos, search_repos, validate_limit


class LimitValidationTests(unittest.TestCase):
    def test_rejects_non_positive_limits(self):
        for limit in (0, -1):
            with self.subTest(limit=limit):
                with self.assertRaisesRegex(ValueError, "limit must be at least 1"):
                    validate_limit(limit)

    def test_caps_limits_at_github_page_size(self):
        self.assertEqual(validate_limit(101), 100)

    def test_list_rejects_invalid_limit_before_request(self):
        session = Mock()
        with self.assertRaises(ValueError):
            list_repos("owner", session, limit=0)
        session.get.assert_not_called()

    def test_search_rejects_invalid_limit_before_request(self):
        session = Mock()
        with self.assertRaises(ValueError):
            search_repos("query", session, limit=-1)
        session.get.assert_not_called()


class RepositoryFormattingTests(unittest.TestCase):
    def test_format_repo_text_handles_missing_push_timestamp(self):
        text = format_repo_text({"full_name": "owner/project", "pushed_at": None})
        self.assertIn("pushed=?", text)

    def test_format_repos_table_handles_empty_descriptions(self):
        text = format_repos_table([{"full_name": "owner/project", "description": None}])
        self.assertIn("owner/project", text)
