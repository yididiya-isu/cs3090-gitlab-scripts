"""Shared logic for querying GitLab activity events, used by git_activity_cli.py (CLI) and app.py (dashboard)."""

import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests

DEFAULT_TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token")
DEFAULT_HOST = "https://git.las.iastate.edu"
DEFAULT_PREFIX = "cs309/2026fall"
DEFAULT_TEAMS = ["1_yn_1", "4_yn_1", "4_yn_2", "4_yn_4", "4_yn_5", "4_yn_6"]
EMAIL_DOMAIN = "iastate.edu"

# GitLab event "action" types we support switching between: value -> (switch label, singular noun).
ACTIONS = {
    "pushed": ("Pushes", "push"),
    "merged": ("Merges", "merge"),
}
DEFAULT_ACTION = "pushed"

# (name, start date, end date) - end date is inclusive.
DEMOS = [
    ("Demo 1", datetime(2026, 8, 26, tzinfo=timezone.utc), datetime(2026, 9, 11, tzinfo=timezone.utc)),
    ("Demo 2", datetime(2026, 9, 12, tzinfo=timezone.utc), datetime(2026, 10, 9, tzinfo=timezone.utc)),
]


def load_token(token=None, token_file=DEFAULT_TOKEN_FILE):
    if token:
        return token.strip()

    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            token = f.read().strip()
        if token:
            return token

    return None


def resolve_project(project, prefix=DEFAULT_PREFIX):
    if "/" not in project:
        return f"{prefix.strip('/')}/{project}"
    return project


def fetch_events(host, project_path, token, per_page=100, after=None, before=None, action=DEFAULT_ACTION):
    encoded_project = quote(project_path, safe="")
    url = f"{host.rstrip('/')}/api/v4/projects/{encoded_project}/events"
    headers = {"PRIVATE-TOKEN": token}
    params = {
        "action": action,
        "per_page": per_page,
        "page": 1,
    }
    if after:
        params["after"] = after.strftime("%Y-%m-%d")
    if before:
        params["before"] = before.strftime("%Y-%m-%d")

    events = []
    while True:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        page_events = resp.json()
        if not page_events:
            break

        events.extend(page_events)

        next_page = resp.headers.get("X-Next-Page")
        if not next_page:
            break
        params["page"] = int(next_page)

    return events


def event_author(event):
    return event.get("author_username") or (event.get("author") or {}).get("username", "unknown")


def event_author_info(event, host=DEFAULT_HOST):
    author = event.get("author") or {}
    username = event_author(event)
    name = author.get("name") or username
    web_url = author.get("web_url") or f"{host.rstrip('/')}/{username}"
    return {"id": author.get("id"), "username": username, "name": name, "web_url": web_url}


def derive_email(username, domain=EMAIL_DOMAIN):
    """ISU GitLab usernames are ISU IDs, so the email is just <username>@<domain>.
    Bot accounts (e.g. project access tokens) don't correspond to a real person."""
    if not username or "_bot_" in username or username.startswith("project_"):
        return None
    return f"{username}@{domain}"


def event_commit_count(event):
    return (event.get("push_data") or {}).get("commit_count", 0)


def event_created_at(event):
    # e.g. "2026-09-05T14:23:01.123Z"
    return datetime.strptime(event["created_at"], "%Y-%m-%dT%H:%M:%S.%f%z")


def last_week_window():
    now = datetime.now(timezone.utc)
    return [("Last 7 days", now - timedelta(days=7), now)]


def demo_by_index(i):
    return DEMOS[i - 1]


def counts_for_window(events, start, end):
    # end date is inclusive, so the upper bound is the end of that calendar day.
    end_inclusive = end.replace(hour=23, minute=59, second=59, microsecond=999999)
    counts = Counter()
    for event in events:
        created_at = event_created_at(event)
        if start <= created_at <= end_inclusive:
            counts[event_author(event)] += 1
    return counts


def details_for_window(events, start, end, host=DEFAULT_HOST):
    """Like counts_for_window, but returns author name/profile-url info, unique active days,
    and total commit count (for push events) alongside counts."""
    end_inclusive = end.replace(hour=23, minute=59, second=59, microsecond=999999)
    counts = Counter()
    commits = Counter()
    days = {}
    authors = {}
    for event in events:
        created_at = event_created_at(event)
        if start <= created_at <= end_inclusive:
            username = event_author(event)
            counts[username] += 1
            commits[username] += event_commit_count(event)
            days.setdefault(username, set()).add(created_at.date())
            if username not in authors:
                authors[username] = event_author_info(event, host)

    rows = [
        {**authors[username], "count": count, "days": len(days[username]), "commits": commits[username]}
        for username, count in counts.items()
    ]
    rows.sort(key=lambda a: a["name"].lower())
    return rows


def fetch_and_bucket(host, project, token, windows, per_page=100, detail=False, action=DEFAULT_ACTION):
    """Fetch events for a project once, covering all windows, then bucket per window."""
    range_after = min(start for _, start, _ in windows)
    # add a day of slack since the API's "before" filter is date-granularity only.
    range_before = max(end for _, _, end in windows) + timedelta(days=1)

    events = fetch_events(
        host, project, token, per_page, after=range_after, before=range_before, action=action
    )

    bucket_fn = (
        (lambda evts, s, e: details_for_window(evts, s, e, host))
        if detail
        else counts_for_window
    )

    results = []
    for name, start, end in windows:
        results.append((name, start, end, bucket_fn(events, start, end)))

    return events, results
