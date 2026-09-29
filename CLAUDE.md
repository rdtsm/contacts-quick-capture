# CLAUDE.md

How to work in this repo. What the app does and how to set it up: [README.md](README.md).
Why it is built this way, and the detailed backlog: [project.md](project.md).

## Commands

- Test: `./.venv/bin/python -m pytest -q` (pytest is dev-only, not in `requirements.txt`).
- Restart after a code change: `launchctl kickstart -k gui/$(id -u)/com.rdtsm.contacts-quick-capture`.
  Killing the process just respawns the old code (see project.md → Gotchas).
- Log: `app.log`.

## Constraints

- Keep it one file: `app.py` holds the server, the prompt, and the embedded page.
- Before committing, run the tests, restart the server, and let the owner check the change in a real browser.
- A new form field needs both a `SIMPLE` entry and a matching DOM `id`; `test_app.py` guards this.
- Public repo: the pre-commit hook blocks staged images. Show the owner what it flagged and get explicit confirmation before `--no-verify`.
- Never commit `credentials.json` or `token.json`, and never read them into a prompt.
