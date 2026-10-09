#!/usr/bin/env python3
"""
Count GitLab activity events (pushes or merges) per user for a project.

Usage:
    Put your GitLab private token (nothing else) in the token file, e.g.:
        echo -n glpat-xxxxxxxxxxxxxxxxxxxx > token
    python3 git_activity_cli.py 1_yn_1

    # multiple repos under the same namespace prefix
    python3 git_activity_cli.py 1_yn_1 2_yn_2 3_yn_3

    # merge requests instead of pushes
    python3 git_activity_cli.py 1_yn_1 --action merged

    # different semester/prefix, or a fully-qualified path
    python3 git_activity_cli.py 1_yn_1 --prefix cs309/2025spring
    python3 git_activity_cli.py cs309/2026fall/1_yn_1 --token-file /path/to/token \
        --host https://git.las.iastate.edu
"""

import argparse
import os
import sys

from git_activity import (
    ACTIONS,
    DEFAULT_ACTION,
    DEFAULT_HOST,
    DEFAULT_PREFIX,
    DEFAULT_TOKEN_FILE,
    DEMOS,
    fetch_and_bucket,
    last_week_window,
    load_token,
    resolve_project,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Count GitLab activity events per user for a project.")
    parser.add_argument(
        "projects",
        nargs="+",
        help="One or more repo names, e.g. '1_yn_1', or full paths with namespace "
             "(full paths override --prefix)",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help="GitLab host (default: %(default)s)",
    )
    parser.add_argument(
        "--prefix",
        default=DEFAULT_PREFIX,
        help="Namespace prefix prepended to each project that doesn't already "
             "contain a '/' (default: %(default)s)",
    )
    parser.add_argument(
        "--action",
        choices=list(ACTIONS),
        default=DEFAULT_ACTION,
        help="Which GitLab event type to count (default: %(default)s)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="GitLab private token. Overrides --token-file and GITLAB_TOKEN if set.",
    )
    parser.add_argument(
        "--token-file",
        default=DEFAULT_TOKEN_FILE,
        help="Path to a file containing just the GitLab private token (default: %(default)s)",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=100,
        help="Results per page (max 100, default: %(default)s)",
    )
    parser.add_argument(
        "--demo",
        choices=["all"] + [str(i) for i in range(1, len(DEMOS) + 1)],
        default="all",
        help="Restrict the report to a single demo window instead of all of them, "
             "e.g. '1' for Demo 1 (default: %(default)s)",
    )
    parser.add_argument(
        "--last-week",
        action="store_true",
        help="Restrict the report to the last 7 days instead of the demo windows "
             "(overrides --demo)",
    )
    return parser.parse_args()


def windows_to_report(args):
    if args.last_week:
        return last_week_window()
    if args.demo == "all":
        return DEMOS
    return [DEMOS[int(args.demo) - 1]]


def main():
    args = parse_args()

    token = load_token(args.token or os.environ.get("GITLAB_TOKEN"), args.token_file)
    if not token:
        print(
            f"Error: no GitLab token found. Put it in {args.token_file}, "
            "set GITLAB_TOKEN, or pass --token.",
            file=sys.stderr,
        )
        sys.exit(1)

    windows = windows_to_report(args)
    label = ACTIONS[args.action][0]

    for project in args.projects:
        project = resolve_project(project, args.prefix)
        events, results = fetch_and_bucket(
            args.host, project, token, windows, args.per_page, action=args.action
        )

        print(f"=== {project} ===")
        print(f"Total {label.lower()} fetched (in range): {len(events)}\n")

        for name, start, end, counts in results:
            print(f"--- {name} ({start.date()} to {end.date()}) ---")
            print(f"{'Student':<25}{label:>10}")
            print("-" * 35)
            if not counts:
                print(f"(no {label.lower()})")
            for username, count in counts.most_common():
                print(f"{username:<25}{count:>10}")
            print()


if __name__ == "__main__":
    main()
