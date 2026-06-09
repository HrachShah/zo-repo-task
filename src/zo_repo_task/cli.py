"""CLI for zo-repo-task."""

import argparse
import json
import os
import sys
import textwrap
from datetime import datetime, timezone
from typing import Any

import requests


DEFAULT_BASE_URL = "https://api.github.com"


def make_session() -> requests.Session:
    """Create a requests session with appropriate headers."""
    session = requests.Session()
    session.headers["Accept"] = "application/vnd.github+json"
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    return session


def list_repos(user: str, session: requests.Session, limit: int = 30) -> list[dict[str, Any]]:
    """List repositories for a GitHub user, sorted by recently pushed."""
    url = f"{DEFAULT_BASE_URL}/users/{user}/repos"
    params = {"sort": "pushed", "per_page": min(limit, 100), "type": "owner"}
    response = session.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def get_repo(owner: str, repo: str, session: requests.Session) -> dict[str, Any]:
    """Get repository details."""
    url = f"{DEFAULT_BASE_URL}/repos/{owner}/{repo}"
    response = session.get(url, timeout=15)
    response.raise_for_status()
    return response.json()


def search_repos(query: str, session: requests.Session, limit: int = 30) -> list[dict[str, Any]]:
    """Search repositories by keyword."""
    url = f"{DEFAULT_BASE_URL}/search/repositories"
    params = {"q": query, "sort": "stars", "per_page": min(limit, 100)}
    response = session.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()
    return data.get("items", [])


def format_repo_text(repo: dict[str, Any], indent: int = 0) -> str:
    """Format a single repository as human-readable text."""
    prefix = "  " * indent
    lines = [
        f"{prefix}{repo['full_name']}",
    ]
    if desc := repo.get("description"):
        lines.append(f"{prefix}  {textwrap.shorten(desc, width=70)}")
    lines.append(
        f"{prefix}  stars={repo.get('stargazers_count', 0)} "
        f"forks={repo.get('forks_count', 0)} "
        f"lang={repo.get('language') or '?'} "
        f"pushed={repo.get('pushed_at', '?')[:10]}"
    )
    return "\n".join(lines)


def format_repos_table(repos: list[dict[str, Any]]) -> str:
    """Format a list of repositories as an ASCII table."""
    if not repos:
        return "(no repositories)"

    name_width = max(len(r["full_name"]) for r in repos)
    desc_width = min(50, max(len(r.get("description", "") or "") for r in repos))

    header = f"{'Name':<{name_width}} {'Stars':>6} {'Forks':>6} {'Language':<12} {'Pushed'}"
    sep = "-" * len(header)
    rows = [header, sep]

    for repo in repos:
        name = repo["full_name"][:name_width]
        stars = str(repo.get("stargazers_count", 0))
        forks = str(repo.get("forks_count", 0))
        lang = str(repo.get("language") or "?")[:12]
        pushed = (repo.get("pushed_at") or "?")[:10]
        desc = textwrap.shorten(repo.get("description") or "", width=desc_width)
        rows.append(f"{name:<{name_width}} {stars:>6} {forks:>6} {lang:<12} {pushed}")

        if desc:
            rows.append(f"{'':>{name_width + 70}}  {desc}")

    return "\n".join(rows)


def cmd_list(args: argparse.Namespace) -> None:
    """Handle the list command."""
    session = make_session()
    try:
        repos = list_repos(args.user, session, limit=args.limit)
    except requests.HTTPError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not repos:
        print(f"No repositories found for user: {args.user}")
        sys.exit(0)

    if args.format == "json":
        print(json.dumps(repos, indent=2))
    else:
        print(format_repos_table(repos))


def cmd_info(args: argparse.Namespace) -> None:
    """Handle the info command."""
    # Validate and split the owner/name argument. The previous code was a
    # single rsplit("/", 1) which crashed with ValueError on a missing
    # slash ("noslash" returns a one-element list) and silently split
    # wrong on extra slashes ("a/b/c" became owner="a", repo="b/c"),
    # which then hit the API as /repos/a/b%2Fc and produced a confusing
    # 404. We now require exactly one '/' and reject anything else up
    # front with a clear usage error.
    parts = args.repo.strip().rstrip("/").split("/")
    if len(parts) != 2 or not all(parts):
        print(
            f"Error: '{args.repo}' is not in owner/name format. "
            f"Expected exactly one '/' separating the owner and repo name.",
            file=sys.stderr,
        )
        sys.exit(2)
    owner, repo = parts

    session = make_session()
    try:
        data = get_repo(owner, repo, session)
    except requests.HTTPError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(format_repo_text(data))
        print()
        topics = data.get("topics", [])
        if topics:
            print(f"  Topics: {', '.join(topics)}")


def cmd_search(args: argparse.Namespace) -> None:
    """Handle the search command."""
    session = make_session()
    try:
        results = search_repos(args.query, session, limit=args.limit)
    except requests.HTTPError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not results:
        print(f"No repositories found matching: {args.query}")
        sys.exit(0)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(format_repos_table(results))


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="zo-task",
        description="GitHub repository explorer CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="List repositories for a user")
    list_p.add_argument("--user", "-u", default=os.environ.get("GITHUB_USER", ""),
                       help="GitHub username (default: GITHUB_USER env var)")
    list_p.add_argument("--limit", "-l", type=int, default=30)
    list_p.add_argument("--format", "-f", choices=["text", "json"], default="text")
    list_p.set_defaults(func=cmd_list)

    info_p = sub.add_parser("info", help="Show repository details")
    info_p.add_argument("repo", help="Repository in owner/name format")
    info_p.add_argument("--format", "-f", choices=["text", "json"], default="text")
    info_p.set_defaults(func=cmd_info)

    search_p = sub.add_parser("search", help="Search repositories")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--limit", "-l", type=int, default=30)
    search_p.add_argument("--format", "-f", choices=["text", "json"], default="text")
    search_p.set_defaults(func=cmd_search)

    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    if args.command in ("list", "search") and not getattr(args, "user", None) and not getattr(args, "query", None):
        print(f"Error: --user required for '{args.command}' command", file=sys.stderr)
        return 1

    try:
        args.func(args)
    except requests.RequestException as e:
        print(f"Network error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
