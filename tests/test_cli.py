import unittest
from unittest.mock import Mock

from zo_repo_task.cli import format_repo_text, format_repos_table, list_repos, search_repos, validate_limit

class ResponseValidationTests(unittest.TestCase):
    def test_list_rejects_non_object_items(self):
        response = Mock()
        response.json.return_value = [{"full_name": "owner/repo"}, "malformed"]
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response

        with self.assertRaisesRegex(ValueError, "invalid repository list"):
            list_repos("owner", session)

    def test_search_rejects_non_object_items(self):
        response = Mock()
        response.json.return_value = {"items": [{"full_name": "owner/repo"}, None]}
        response.raise_for_status.return_value = None
        session = Mock()
        session.get.return_value = response

        with self.assertRaisesRegex(ValueError, "invalid repository search items"):
            search_repos("query", session)



class LimitValidationTests(unittest.TestCase):
    def test_rejects_non_positive_limits(self):
        for limit in (0, -1):
            with self.subTest(limit=limit):
                with self.assertRaisesRegex(ValueError, "limit must be at least 1"):
                    validate_limit(limit)

    def test_rejects_boolean_limits(self):
        with self.assertRaisesRegex(TypeError, "limit must be an integer"):
            validate_limit(True)

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

    def test_format_repo_text_handles_missing_name(self):
        text = format_repo_text({"description": "A project", "pushed_at": None})
        self.assertTrue(text.startswith("?"))

    def test_format_repos_table_handles_empty_descriptions(self):
        text = format_repos_table([{"full_name": "owner/project", "description": None}])
        self.assertIn("owner/project", text)

    def test_formatters_ignore_non_string_text_fields(self):
        repo = {
            "full_name": {"unexpected": "object"},
            "description": ["unexpected", "list"],
            "language": 42,
            "pushed_at": {"unexpected": "object"},
        }

        text = format_repo_text(repo)
        table = format_repos_table([repo])

        self.assertIn("?", text)
        self.assertIn("?", table)
        self.assertNotIn("unexpected", text)
        self.assertNotIn("unexpected", table)
