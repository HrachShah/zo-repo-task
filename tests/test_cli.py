import unittest
from argparse import Namespace
from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import patch

from zo_repo_task.cli import cmd_info


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
