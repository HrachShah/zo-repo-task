import unittest

from zo_repo_task.cli import format_repo_text, format_repos_table


class RepositoryFormattingTests(unittest.TestCase):
    def test_text_format_handles_missing_push_timestamp(self):
        result = format_repo_text({"full_name": "owner/repo", "pushed_at": None})

        self.assertIn("pushed=?", result)

    def test_table_handles_empty_descriptions_and_missing_push_timestamp(self):
        result = format_repos_table(
            [{"full_name": "owner/repo", "description": None, "pushed_at": None}]
        )

        self.assertIn("owner/repo", result)
        self.assertIn("?", result)


if __name__ == "__main__":
    unittest.main()
