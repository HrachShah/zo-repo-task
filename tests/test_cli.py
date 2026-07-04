"""Tests for the zo-repo-task CLI."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from zo_repo_task.cli import (
    cmd_info,
    cmd_list,
    cmd_search,
    format_repo_text,
    format_repos_table,
    get_repo,
    list_repos,
    main,
    make_session,
    search_repos,
)


def _make_repo(
    full_name: str = "owner/name",
    description: str = "A test repository.",
    stargazers_count: int = 10,
    forks_count: int = 2,
    language: str | None = "Python",
    pushed_at: str = "2026-07-04T12:00:00Z",
) -> dict:
    return {
        "full_name": full_name,
        "description": description,
        "stargazers_count": stargazers_count,
        "forks_count": forks_count,
        "language": language,
        "pushed_at": pushed_at,
    }


class TestFormatHelpers:
    def test_format_repo_text_includes_all_fields(self) -> None:
        repo = _make_repo()
        out = format_repo_text(repo)
        assert "owner/name" in out
        assert "stars=10" in out
        assert "forks=2" in out
        assert "lang=Python" in out
        assert "pushed=2026-07-04" in out

    def test_format_repo_text_handles_missing_description(self) -> None:
        repo = _make_repo(description=None)
        out = format_repo_text(repo)
        assert "owner/name" in out
        assert "?" not in out.splitlines()[1]  # description row may be absent

    def test_format_repo_text_respects_indent(self) -> None:
        repo = _make_repo()
        out = format_repo_text(repo, indent=2)
        assert out.startswith("    owner/name")

    def test_format_repos_table_handles_empty(self) -> None:
        assert format_repos_table([]) == "(no repositories)"

    def test_format_repos_table_includes_header_and_rows(self) -> None:
        repos = [_make_repo("a/b"), _make_repo("c/d", stargazers_count=99)]
        out = format_repos_table(repos)
        assert "Name" in out.splitlines()[0]
        assert "a/b" in out
        assert "c/d" in out
        assert "99" in out


class TestSession:
    def test_make_session_sets_accept_header(self) -> None:
        session = make_session()
        assert session.headers["Accept"] == "application/vnd.github+json"

    def test_make_session_adds_bearer_when_token_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "secret123")
        session = make_session()
        assert session.headers["Authorization"] == "Bearer secret123"

    def test_make_session_skips_auth_header_when_no_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        session = make_session()
        assert "Authorization" not in session.headers


class TestListRepos:
    def test_list_repos_uses_pushed_sort(self) -> None:
        session = MagicMock()
        response = MagicMock()
        response.json.return_value = [_make_repo()]
        response.raise_for_status = MagicMock()
        session.get.return_value = response

        result = list_repos("owner", session, limit=5)

        assert result == [_make_repo()]
        called_url = session.get.call_args[0][0]
        assert called_url == "https://api.github.com/users/owner/repos"
        params = session.get.call_args.kwargs["params"]
        assert params["sort"] == "pushed"
        assert params["per_page"] == 5
        assert params["type"] == "owner"

    def test_list_repos_caps_per_page_at_100(self) -> None:
        session = MagicMock()
        response = MagicMock()
        response.json.return_value = []
        response.raise_for_status = MagicMock()
        session.get.return_value = response

        list_repos("owner", session, limit=10_000)

        params = session.get.call_args.kwargs["params"]
        assert params["per_page"] == 100


class TestGetRepo:
    def test_get_repo_uses_owner_and_name(self) -> None:
        session = MagicMock()
        response = MagicMock()
        response.json.return_value = _make_repo()
        response.raise_for_status = MagicMock()
        session.get.return_value = response

        data = get_repo("owner", "name", session)

        assert data == _make_repo()
        assert session.get.call_args[0][0] == "https://api.github.com/repos/owner/name"


class TestSearchRepos:
    def test_search_repos_returns_items(self) -> None:
        session = MagicMock()
        response = MagicMock()
        response.json.return_value = {"items": [_make_repo("found/repo")]}
        response.raise_for_status = MagicMock()
        session.get.return_value = response

        result = search_repos("log analyzer", session)

        assert result == [_make_repo("found/repo")]
        params = session.get.call_args.kwargs["params"]
        assert params["q"] == "log analyzer"
        assert params["sort"] == "stars"

    def test_search_repos_returns_empty_when_items_missing(self) -> None:
        session = MagicMock()
        response = MagicMock()
        response.json.return_value = {}
        response.raise_for_status = MagicMock()
        session.get.return_value = response

        assert search_repos("nothing", session) == []


class TestCmdInfo:
    def test_cmd_info_runs_when_repo_has_slash(self, capsys: pytest.CaptureFixture) -> None:
        repo = _make_repo("owner/name", description="A test repository.")
        with patch("zo_repo_task.cli.get_repo", return_value=repo):
            args = MagicMock(repo="owner/name", format="text")
            cmd_info(args)

        out = capsys.readouterr().out
        assert "owner/name" in out
        assert "A test repository." in out

    def test_cmd_info_prints_topics(self, capsys: pytest.CaptureFixture) -> None:
        repo = _make_repo()
        repo["topics"] = ["python", "cli"]
        with patch("zo_repo_task.cli.get_repo", return_value=repo):
            args = MagicMock(repo="owner/name", format="text")
            cmd_info(args)

        out = capsys.readouterr().out
        assert "Topics: python, cli" in out

    def test_cmd_info_prints_json(self, capsys: pytest.CaptureFixture) -> None:
        repo = _make_repo()
        with patch("zo_repo_task.cli.get_repo", return_value=repo):
            args = MagicMock(repo="owner/name", format="json")
            cmd_info(args)

        out = capsys.readouterr().out
        # The whole dict should round-trip through json.dumps
        assert json.loads(out) == repo

    def test_cmd_info_strips_trailing_slash(self) -> None:
        with patch("zo_repo_task.cli.get_repo", return_value=_make_repo()) as get_mock:
            args = MagicMock(repo="owner/name/", format="text")
            cmd_info(args)

        # Should have called get_repo with owner="owner", repo="name" — not owner="owner", repo="name/"
        owner, repo = get_mock.call_args[0][:2]
        assert owner == "owner"
        assert repo == "name"

    def test_cmd_info_rejects_bare_repo_name(self, capsys: pytest.CaptureFixture) -> None:
        """A bare repo name without '/' should fail with a clean error, not ValueError."""
        args = MagicMock(repo="justaname", format="text")
        with pytest.raises(SystemExit) as exc_info:
            cmd_info(args)
        assert exc_info.value.code == 1

        err = capsys.readouterr().err
        assert "owner/name" in err
        assert "Traceback" not in err

    def test_cmd_info_rejects_empty_repo(self, capsys: pytest.CaptureFixture) -> None:
        args = MagicMock(repo="", format="text")
        with pytest.raises(SystemExit) as exc_info:
            cmd_info(args)
        assert exc_info.value.code == 1

        err = capsys.readouterr().err
        assert "owner/name" in err
        assert "Traceback" not in err

    def test_cmd_info_rejects_repo_with_too_many_slashes(self, capsys: pytest.CaptureFixture) -> None:
        args = MagicMock(repo="a/b/c", format="text")
        with pytest.raises(SystemExit) as exc_info:
            cmd_info(args)
        assert exc_info.value.code == 1

        err = capsys.readouterr().err
        assert "owner/name" in err
        assert "Traceback" not in err


class TestCmdList:
    def test_cmd_list_prints_table(self, capsys: pytest.CaptureFixture) -> None:
        with patch("zo_repo_task.cli.list_repos", return_value=[_make_repo()]):
            args = MagicMock(user="owner", limit=10, format="text")
            cmd_list(args)

        out = capsys.readouterr().out
        assert "owner/name" in out

    def test_cmd_list_prints_json(self, capsys: pytest.CaptureFixture) -> None:
        repo = _make_repo()
        with patch("zo_repo_task.cli.list_repos", return_value=[repo]):
            args = MagicMock(user="owner", limit=10, format="json")
            cmd_list(args)

        out = capsys.readouterr().out
        assert json.loads(out) == [repo]

    def test_cmd_list_handles_empty(self, capsys: pytest.CaptureFixture) -> None:
        with patch("zo_repo_task.cli.list_repos", return_value=[]):
            args = MagicMock(user="empty", limit=10, format="text")
            with pytest.raises(SystemExit) as exc_info:
                cmd_list(args)
        assert exc_info.value.code == 0

        out = capsys.readouterr().out
        assert "No repositories found" in out
        assert "empty" in out


class TestCmdSearch:
    def test_cmd_search_prints_table(self, capsys: pytest.CaptureFixture) -> None:
        with patch("zo_repo_task.cli.search_repos", return_value=[_make_repo("found/repo")]):
            args = MagicMock(query="log analyzer", limit=10, format="text")
            cmd_search(args)

        out = capsys.readouterr().out
        assert "found/repo" in out

    def test_cmd_search_prints_json(self, capsys: pytest.CaptureFixture) -> None:
        repo = _make_repo("found/repo")
        with patch("zo_repo_task.cli.search_repos", return_value=[repo]):
            args = MagicMock(query="log", limit=10, format="json")
            cmd_search(args)

        out = capsys.readouterr().out
        assert json.loads(out) == [repo]

    def test_cmd_search_handles_empty(self, capsys: pytest.CaptureFixture) -> None:
        with patch("zo_repo_task.cli.search_repos", return_value=[]):
            args = MagicMock(query="nothing", limit=10, format="text")
            with pytest.raises(SystemExit) as exc_info:
                cmd_search(args)
        assert exc_info.value.code == 0

        out = capsys.readouterr().out
        assert "No repositories found" in out
        assert "nothing" in out


class TestMain:
    def test_main_no_args_prints_help(self, capsys: pytest.CaptureFixture) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main([])
        # argparse exits with 2 when a required subcommand is missing
        assert exc_info.value.code == 2

    def test_main_list_with_user(self, capsys: pytest.CaptureFixture) -> None:
        with patch("zo_repo_task.cli.list_repos", return_value=[_make_repo()]):
            rc = main(["list", "--user", "owner"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "owner/name" in out

    def test_main_list_without_user_returns_error(self, capsys: pytest.CaptureFixture) -> None:
        rc = main(["list"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "--user" in err
        assert "list" in err

    def test_main_search_requires_query(self, capsys: pytest.CaptureFixture) -> None:
        """Empty query is not a real query — the validator should reject it cleanly."""
        rc = main(["search", ""])
        assert rc == 1
        err = capsys.readouterr().err
        assert "query" in err.lower()
        # The misleading '--user required' message must NOT appear for search
        assert "--user" not in err

    def test_main_search_with_query(self, capsys: pytest.CaptureFixture) -> None:
        with patch("zo_repo_task.cli.search_repos", return_value=[_make_repo("hit/repo")]):
            rc = main(["search", "log"])
        assert rc == 0

    def test_main_info_with_slash(self, capsys: pytest.CaptureFixture) -> None:
        with patch("zo_repo_task.cli.get_repo", return_value=_make_repo()):
            rc = main(["info", "owner/name"])
        assert rc == 0

    def test_main_info_bare_name_returns_error_cleanly(self, capsys: pytest.CaptureFixture) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["info", "justaname"])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "owner/name" in err
        # Must not leak a Python traceback
        assert "Traceback" not in err

    def test_main_info_too_many_slashes_returns_error_cleanly(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["info", "a/b/c"])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "Traceback" not in err
