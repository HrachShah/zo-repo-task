import unittest
from argparse import Namespace
from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import patch

from zo_repo_task.cli import cmd_info, list_repos, search_repos


class InfoCommandTests(unittest.TestCase):
    def test_rejects_repository_without_owner_or_name(self):
        error = StringIO()
        with redirect_stderr(error), patch("zo_repo_task.cli.make_session") as make_session:
            cmd_info(Namespace(repo="owner", format="text"))

        self.assertEqual(error.getvalue().strip(), "Error: repository must use owner/name format")
        make_session.assert_not_called()

    def test_rejects_repository_with_extra_path_segments(self):
        error = StringIO()
        with redirect_stderr(error), patch("zo_repo_task.cli.make_session") as make_session:
            cmd_info(Namespace(repo="owner/repo/issues", format="text"))

        self.assertEqual(error.getvalue().strip(), "Error: repository must use owner/name format")
        make_session.assert_not_called()


if __name__ == "__main__":
    unittest.main()


class LimitValidationTests(unittest.TestCase):
    def test_list_rejects_non_positive_limit_before_request(self):
        session = object()
        with self.assertRaisesRegex(ValueError, "limit must be at least 1"):
            list_repos("owner", session, limit=0)

    def test_search_rejects_non_positive_limit_before_request(self):
        session = object()
        with self.assertRaisesRegex(ValueError, "limit must be at least 1"):
            search_repos("query", session, limit=-1)
