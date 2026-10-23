# cs3090-gitlab-scripts

## Setup

Requires Python 3. Create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask requests
```

### Getting a GitLab token

1. Sign in to https://git.las.iastate.edu.
2. Click your avatar (top left) → **Edit profile** → **Access tokens** (or go directly to https://git.las.iastate.edu/-/user_settings/personal_access_tokens).
3. Click **Add new token**.
4. Give it a name (e.g. `cs3090-dashboard`) and an expiration date.
5. Under scopes, select **`read_api`** only. That's all the scripts need.
6. Click **Create personal access token** and copy the token (starts with `glpat-`). It's only shown once.

The token can only see projects your account has access to, so you need to be a member of the team repos you query.

Put the token (nothing else) in a file named `token` in the project root:

```bash
echo -n glpat-xxxxxxxxxxxxxxxxxxxx > token
```

Optionally, list the team repo names to query, one per line, in `teams.txt`. Without it, the defaults in `git_activity.py` are used.

## Running the dashboard

```bash
source .venv/bin/activate
python app.py
```

Then open http://127.0.0.1:5050 in your browser. You can also paste a token into the form instead of using the `token` file.

## TODO

- [ ] Add a "Lines changed" stat (additions/deletions per author per demo window).
  - Use `GET /projects/:id/repository/commits?with_stats=true&all=true&since=...&until=...` (paginated) and sum `stats.additions` / `stats.deletions`.
  - Don't use `/repository/contributors`: its `additions`/`deletions` fields are deprecated and always 0.
  - Commits are keyed by git `author_email`, not GitLab username, so a mapping may be needed for students with personal emails in their git config.
  - Skip merge commits (more than one parent) to avoid double counting.
  - Consider excluding generated/vendored files (lockfiles, build output) via `/repository/commits/:sha/diff`.
