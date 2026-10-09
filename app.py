#!/usr/bin/env python3
"""
Local web dashboard showing GitLab activity (pushes/merges) per team.

Usage:
    Put your GitLab private token (nothing else) in the token file, e.g.:
        echo -n glpat-xxxxxxxxxxxxxxxxxxxx > token
    python3 app.py

Then open http://127.0.0.1:5050 in your browser. This only ever talks to
your own machine and to the configured GitLab host - nothing is published
or sent anywhere else.
"""

import os
from datetime import datetime, timezone

import requests
from flask import Flask, render_template, request

from git_activity import (
    ACTIONS,
    DEFAULT_ACTION,
    DEFAULT_HOST,
    DEFAULT_PREFIX,
    DEFAULT_TEAMS,
    DEFAULT_TOKEN_FILE,
    DEMOS,
    derive_email,
    fetch_and_bucket,
    last_week_window,
    load_token,
    resolve_project,
)

app = Flask(__name__)

TEAMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "teams.txt")


def default_teams():
    if os.path.exists(TEAMS_FILE):
        teams = [line.strip() for line in open(TEAMS_FILE) if line.strip() and not line.startswith("#")]
        if teams:
            return teams
    return DEFAULT_TEAMS


def windows_for_period(period, start_date=None, end_date=None):
    if period == "custom":
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return [("Custom range", start, end)]
    if period == "last_week":
        return last_week_window()
    if period == "all":
        return DEMOS
    for i, (name, start, end) in enumerate(DEMOS, start=1):
        if period == str(i):
            return [(name, start, end)]
    return DEMOS


@app.route("/", methods=["GET", "POST"])
def dashboard():
    # Use POST so a pasted token never ends up in the URL, browser history, or server logs.
    source = request.form if request.method == "POST" else request.args

    teams_param = source.get("teams", "")
    teams = [t.strip() for t in teams_param.replace(",", "\n").splitlines() if t.strip()]
    if not teams:
        teams = default_teams()

    host = source.get("host", DEFAULT_HOST)
    prefix = source.get("prefix", DEFAULT_PREFIX)
    period = source.get("period", "all")
    start_date = source.get("start_date", "")
    end_date = source.get("end_date", "")
    action = source.get("action", DEFAULT_ACTION)
    if action not in ACTIONS:
        action = DEFAULT_ACTION
    token_input = request.form.get("token", "").strip() if request.method == "POST" else ""

    context = {
        "teams_text": ",".join(teams),
        "host": host,
        "prefix": prefix,
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "action": action,
        "actions": {value: label for value, (label, _) in ACTIONS.items()},
        "action_word": ACTIONS[action][0].lower(),
        "has_token_input": bool(token_input),
        "demos": DEMOS,
        "error": None,
        "team_results": [],
    }

    if not teams:
        context["error"] = (
            "No teams given. Enter one or more repo names, or add them (one per line) "
            f"to {TEAMS_FILE}."
        )
        return render_template("dashboard.html", **context)

    token = load_token(token_input or None, DEFAULT_TOKEN_FILE)
    if not token:
        context["error"] = (
            f"No GitLab token found. Paste one in the Token field, or put it in {DEFAULT_TOKEN_FILE}."
        )
        return render_template("dashboard.html", **context)

    if period == "custom" and (not start_date or not end_date):
        context["error"] = "Pick both a start and end date for a custom range."
        return render_template("dashboard.html", **context)

    try:
        windows = windows_for_period(period, start_date, end_date)
    except ValueError:
        context["error"] = "Invalid custom date range."
        return render_template("dashboard.html", **context)

    team_results = []
    for team in teams:
        project = resolve_project(team, prefix)
        try:
            events, results = fetch_and_bucket(host, project, token, windows, detail=True, action=action)

            for _, _, _, authors in results:
                for a in authors:
                    a["email"] = derive_email(a["username"])

            team_results.append({
                "team": team,
                "project": project,
                "total": len(events),
                "windows": [
                    {
                        "name": name,
                        "start": start.date().isoformat(),
                        "end": end.date().isoformat(),
                        "authors": authors,
                        "total": sum(a["count"] for a in authors),
                    }
                    for name, start, end, authors in results
                ],
                "error": None,
            })
        except requests.HTTPError as e:
            team_results.append({
                "team": team,
                "project": project,
                "error": f"{e.response.status_code} {e.response.reason}",
            })
        except requests.RequestException as e:
            team_results.append({"team": team, "project": project, "error": str(e)})

    context["team_results"] = team_results
    return render_template("dashboard.html", **context)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
