# zo-repo-task

A minimal CLI tool to list and explore GitHub repositories from the command line.

## Installation

```bash
pip install -e .
```

## Usage

```bash
# List your repos
zo-task list --user HrachShah

# Show repo details
zo-task info HrachShah/FreeRelay

# Search repos by name
zo-task search "log analyzer"
```

## Features

- List repositories for any GitHub user
- Show repository metadata (stars, forks, description, language)
- Search repositories by keyword
- Filter by stars, language, or push date
- Output as text, JSON, or table format
