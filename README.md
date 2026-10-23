# cs3090-gitlab-scripts

## Setup

Requires Python 3. Create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask requests
```

Put your GitLab private token (nothing else) in a file named `token` in the project root:

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
