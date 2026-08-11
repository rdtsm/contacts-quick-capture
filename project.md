# project.md — Contacts quick capture

Long-term memory for future sessions. User-facing setup, usage and the high-level
backlog live in [README.md](README.md) — this file records *why*, not *how to run*.

## Architecture and why

Single file, `app.py` (~580 lines): Flask server, embedded HTML/CSS/JS, all routes.
Nothing is split out because nothing is reused — one file is readable end to end and
has no import graph to keep in your head.

- **Local only.** Flask dev server binds 127.0.0.1:8321 (`app.run(port=PORT)`), so the
  app is unreachable from the network. This is the load-bearing privacy property:
  contact data never leaves the machine except to Anthropic (parsing) and Google
  (the one contact you create).
- **Three routes.** `/parse` (input → Claude → JSON), `/create` (form → People API),
  `/` (the page). vCard export is pure client-side JS — no server round-trip, and it
  works with zero Google setup, which is why it is the on-ramp the README leads with.
- **Two parsing paths, one interface.** `claude_parse()` dispatches to the Claude Code
  CLI (default, billed to the subscription) or the metered API when `ANTHROPIC_API_KEY`
  is set. Models: `CLI_MODEL = "sonnet"`, `CLAUDE_MODEL = "claude-haiku-4-5-20251001"`.
- **Google writes go through raw REST**, not a client library: an `AuthorizedSession`
  POSTs to `people.googleapis.com/v1/people:createContact`. The session refreshes the
  hourly access token itself.
- **The form is data-driven.** A JS `SIMPLE` array drives fill/collect/reset. Every
  entry needs a matching DOM `id` — see the gotcha below.

## Decisions and rationale

**Parse with the Claude Code CLI, not the API** (2026-07-04). The CLI reuses the
existing subscription, so per-contact parsing costs nothing; the API path stays as a
fallback behind an env var. *Rejected:* API-only — correct engineering, but it puts a
metered bill on a personal utility used a few times a week. *Cost of the choice:* the
CLI is slower (subprocess + model start) and needs `claude` on `PATH`.

**Sandbox the CLI in a throwaway temp cwd** (2026-07-04). Headless `claude` can read
files inside its cwd, so `_parse_via_cli` writes only the card image into a fresh temp
dir and runs there. A prompt injected via a malicious card or web page therefore cannot
reach `credentials.json`, `token.json`, or anything else on disk. The prompt goes in via
stdin so variadic flags cannot swallow it.

**Drop `google-api-python-client`** (2026-07-22, commit `fe6140f`). The app calls exactly
one endpoint; the library added a large dependency and a discovery round-trip to save
about five lines. Verified by uninstalling it and running a real create. Dependencies are
now `flask`, `requests`, `google-auth-oauthlib`.

**Leave versions unpinned** (2026-07-22). A deliberate call against the usual advice: a
lockfile is ceremony for a three-dependency local tool, and a stale pin is likelier to
break this app than a fresh upstream release. The README says to pin a single package if
one ever misbehaves.

**Keep `country` and `countryCode` as two visible fields** (2026-07-22, `fd6279c`/`501ffc0`).
Google needs the ISO alpha-2 code to render an address correctly, but a hidden derived
field is a field you cannot fix when the model guesses wrong. The prompt keeps the pair
in sync; the user can override either. *Rejected:* deriving the code server-side from
the country name — needs a country table, and fails silently on the cases that matter.

**Auto-start via LaunchAgent** (2026-07-31, `abe140f`). Asked for a friendlier "server not
running" error; the app cannot render one, because when the server is down there is
nothing to serve the page — Chrome shows its own error. So the fix removes the failure
mode instead of describing it: `RunAtLoad` + `KeepAlive` start the server at login and
respawn it within seconds if it dies. *Rejected:* a bookmarked local `launch.html` that
pings and shows the start command (works, but adds a second HTML surface and changes the
pinned URL); a double-clickable `start.command` (no message where the failure appears).

**Tolerate prose around the model's JSON** (2026-08-11, `800f674`). `_strip_json` had
required the entire CLI output to be one JSON document. Fenced JSON plus a trailing
sentence — which the model adds on hard inputs — failed the whole parse with
`Extra data: line 4 column 1`. It now decodes the first JSON object with
`raw_decode` and ignores what surrounds it, which also deleted the fence regex.
*Rejected:* tightening the prompt — it already forbade fences and prose, and the model
overrode it; parser tolerance is the fix that holds.

**Dropped: "Open vCard" button** (2026-07-22). Browsers cannot hand a downloaded file to a
local app. The only working version runs `open` on the server — macOS-only machinery for
a button that saves one double-click.

## Research findings

- **There is no zero-setup Google login.** Writing contacts is a Google *sensitive scope*;
  the consent screen only appears for a registered OAuth client. Hence `credentials.json`
  and the setup section. Registering the app as **Internal** to a Workspace domain avoids
  verification and test-user expiry, so the refresh token persists indefinitely.
- **Mobile requires the phone to be a client of this Mac.** Parsing depends on the local
  `claude` CLI, so the server cannot move to a phone or to a cloud host without giving up
  the free-parsing and local-only properties. Camera capture on mobile needs HTTPS
  (`getUserMedia`), which `tailscale serve` provides over a private tunnel. *Rejected:*
  cloud hosting (metered API + contact data on a server), a native app (weeks of work),
  Termux on Android (no Claude Code CLI).
- **The screenshot method is deliberate.** `docs/screenshot.png` is regenerated with a
  temporary Playwright install and a fictional card (Dr. Mara Whitfield / Northwind Labs,
  555-01xx numbers); the generating `shot.py` is kept out of this public repo, and the
  browser cache (~540 MB) is uninstalled afterwards. Full method is in Claude's memory
  for this project.

## Gotchas no test can encode

- **Restart with `launchctl kickstart -k gui/$(id -u)/com.rdtsm.contacts-quick-capture`.**
  `KeepAlive` means killing the process just respawns it, and `debug=False` means there is
  no auto-reload — so code changes need this, not a `kill`.
- **launchd does not load your shell profile.** The plist must set `PATH` explicitly or the
  server cannot find `claude` and every parse fails with `[Errno 2] ... 'claude'`.
- **Verify in a real browser before committing.** A `countryCode` fix once passed
  server-side checks and still failed, because the field was not wired into the JS
  `SIMPLE` list. `test_app.py` now guards that specific gap; the habit still applies.
- **CSS specificity in the success box.** `.okbox a{color:var(--accent)}` beats
  `.btn-primary`, which once rendered blue-on-blue button text. `.okbox a.btn{color:#fff}`
  holds it; watch for it when touching that box.
- **`pytest` is dev-only** and deliberately absent from `requirements.txt`; install it into
  `.venv` once.
- **The pre-commit hook blocks any staged image in this public repo.** Expect it when the
  screenshot changes, and get explicit confirmation before `--no-verify`.
- **Stale name:** `app.py`'s module docstring still says "Contact Dropper", the pre-rename
  product name. Cosmetic, untouched to keep diffs surgical.

## Backlog

Ordered by value. README carries the user-facing summary of these.

1. **Mobile capture (Android/iPhone).** Phone as a client of the Mac. Install Tailscale on
   both, `tailscale serve` the app for HTTPS, add a "Choose photo" file input (on Android
   that natively offers camera-or-gallery). Nothing is exposed to the internet. The
   LaunchAgent is the prerequisite and is now in place. A PWA manifest is the natural
   follow-on so it opens like an app.
2. **Duplicate hints** *(undecided)*. Mark parsed fields that already exist in Google
   Contacts, advisory only. Search `people.searchContacts` for last name, each email and
   phone; re-check candidates exactly on the server, comparing phones via Google's
   `canonicalForm` (E.164), so a dot can never be wrong — the only failure mode is an
   unflagged duplicate, since Google matches from the *start* of a stored number.
   *Trade-off, and the reason it is undecided:* the app would start **reading** contacts,
   so the "only ever calls `createContact`" guarantee in the README's Privacy & security
   section would no longer hold. No re-authorization needed — the scope already permits it.
3. **Duplicate merge.** The step beyond hints: update the matched contact instead of
   creating a new one.
4. **Lower-friction capture.** A macOS Share/Quick Action or menu-bar shortcut that sends
   the clipboard or selection straight to parsing, skipping the browser tab.
5. **Accessibility.** Form labels are not wired to inputs for screen readers.
