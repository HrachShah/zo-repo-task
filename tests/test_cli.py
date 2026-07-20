import unittest
from unittest.mock import Mock

from zo_repo_task.cli import format_repo_text, format_repos_table, list_repos, search_repos


class RepositoryFormattingTests(unittest.TestCase):
    def test_text_format_handles_missing_push_timestamp(self):
        result = format_repo_text({"full_name": "owner/repo", "pushed_at": None})

        self.assertIn("pushed=?", result)

    def test_api_list_rejects_non_positive_limit(self):
        with self.assertRaisesRegex(ValueError, "limit must be at least 1"):
            list_repos("owner", Mock(), limit=0)

    def test_api_search_rejects_non_positive_limit(self):
        with self.assertRaisesRegex(ValueError, "limit must be at least 1"):
            search_repos("query", Mock(), limit=-1)

    def test_api_list_ignores_non_object_entries(self):
        response = Mock()
        response.json.return_value = [{"full_name": "owner/repo"}, "invalid", None]
        session = Mock()
        session.get.return_value = response

        self.assertEqual(list_repos("owner", session), [{"full_name": "owner/repo"}])

    def test_api_search_ignores_scalar_payload(self):
        response = Mock()
        response.json.return_value = []
        session = Mock()
        session.get.return_value = response

        self.assertEqual(search_repos("query", session), [])

    def test_api_search_ignores_non_list_items(self):
        response = Mock()
        response.json.return_value = {"items": {"full_name": "owner/repo"}}
        session = Mock()

        session.get.return_value = response

        self.assertEqual(search_repos("query", session), [])

    def test_table_handles_empty_descriptions_and_missing_push_timestamp(self):
        result = format_repos_table(
            [{"full_name": "owner/repo", "description": None, "pushed_at": None}]
        )

        self.assertIn("owner/repo", result)
        self.assertIn("?", result)

    def test_table_handles_missing_repository_name(self):
        result = format_repos_table([{"description": "No name supplied"}])

        self.assertIn("?", result)


if __name__ == "__main__":
    unittest.main()
