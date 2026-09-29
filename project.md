# project.md — Contacts quick capture

Long-term memory for future sessions. User-facing setup, usage and the high-level
backlog live in [README.md](README.md) — this file records *why*, not *how to run*.

## Requirements, and how the alternatives score

What this tool has to do, in the order that matters. R1 to R4 are why it exists at all;
a product that misses one of them cannot be adopted, however good the rest is.

| | Requirement | Why |
|---|---|---|
| **R1** | **Any input, not just cards.** Photo, live camera, pasted text, email signature, screenshot, URL | The card is the rarest of the five in practice. A signature block or a screenshot is the everyday case |
| **R2** | **Correct Google labels on write.** Mobile / Work / Work fax, name prefix, Home page, Profile, ISO country code | A contact that lands as one unlabelled blob still has to be edited by hand, which is the work being removed |
| **R3** | **No vendor account, no second contact database.** Nothing accumulates off the machine | The address book already exists. A tool that owns a copy of it is a dependency with an exit cost |
| **R4** | **Untrusted input is contained.** A card or a fetched page cannot make the parser reach anything else on disk | The input is a photograph handed over by a stranger, and the same machine holds the Google credentials |
| **R5** | **Zero marginal cost per contact** | A few contacts a week does not carry a per-seat subscription |
| **R6** | **The model flags what it could not read**, and a human confirms before the write | Attention goes to the one uncertain field instead of all twelve |

R6 is not gradeable below: no vendor documents whether or how uncertainty is surfaced.
Prices are per seat, checked 2026-09-05.

### Freemium and paid

| Product | Model | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|---|
| [CamCard](https://www.camcard.com/) | Free + team tiers ([no published price](https://zapier.com/blog/best-business-card-scanner-software/)) | ✗ | ✓ | ✗ | ✗ | ~ |
| [Covve Scan](https://covve.com/pricing/) | $12/mo, $119/yr | ✗ | ~ | ✗ | ✗ | ✗ |
| [ABBYY FineReader](https://zapier.com/blog/best-business-card-scanner-software/) | ~$99/yr | ~ | ✗ | ~ | ✗ | ✗ |
| Blinq, Popl, HiHello, [Haystack](https://spreadly.app/en/blog/top-7-best-business-card-scanner-apps-2026) | Freemium, per seat | ✗ | ~ | ✗ | ✗ | ~ |
| HubSpot, Salesflare | Bundled with the CRM | ✗ | ✗ | ✗ | ✗ | ✗ |
| [iOS Live Text](https://www.idownloadblog.com/2023/06/07/how-to-scan-business-card-details-iphone-contacts/), [Google Lens](https://phototranslator.net/blog/google-lens-honest-review-2026) | Free, built in | ~ | ✗ | ✓ | ✓ | ✓ |
| [Parsio](https://parsio.io/email-signature-parser/), [SigParser](https://www.sigparser.com/), ContactsFlow | Freemium to enterprise SaaS | ✗ | ~ | ✗ | ✗ | ✗ |

**CamCard is the closest**, and it does sync to Google Contacts — but the card goes to its
cloud and the contact lives in its account first, because the product is team lead capture
and a personal address book is the side effect. **The real incumbent is iOS Live Text**: free,
offline, already on the phone, and it passes R3 to R5 outright. It fails R2 completely, and
that failure is behavioural rather than technical. It hands over one field at a time —
long-press the number, add to contacts, repeat for name, email, company — which is slow
enough that the contact often never gets filed at all. Everything paid in this table fails
R3 by construction: the subscription exists because the vendor holds the database. Cloud OCR
is the category norm, and [reselling scanned contacts has been documented in
it](https://www.folocard.com/2019/08/07/business-card-scanner-privacy-gdpr-ccpa/).

### Open source

Searched GitHub 2026-09-05. Nothing packaged does this job; the field splits three ways,
and each way misses a different requirement.

| Project | What it is | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|---|
| [Card OCR demos](https://github.com/topics/business-card-recognition) — [dhruv2601](https://github.com/dhruv2601/Business-Card-Scanner), [stpabhi](https://github.com/stpabhi/business-card-scanner), [ierolsen](https://github.com/ierolsen/Business-Card-Reader-App), [Bob-GGB](https://github.com/Bob-GGB/BusinessCardScannerVer3) | Tesseract or Vision plus regex; one spaCy NER model | ✗ | ✗ | ✓ | ✓ | ✓ |
| [Monica](https://github.com/monicahq/monica) (25.2k), [Twenty](https://github.com/twentyhq/twenty) (56.3k), [harperreed/crm](https://github.com/harperreed/crm) | Self-hosted personal CRM; harperreed's syncs Google contacts and ships an MCP server | ✗ | ✗ | ✗ | ✓ | ✓ |
| [n8n](https://github.com/n8n-io/n8n) (203k) | Fair-code automation platform: wire a vision node to the Google Contacts node | ✓ | ~ | ~ | ✗ | ✗ |

**The card OCR projects are demos.** Double-digit stars at best, and the three most complete
were last touched in 2017, 2022 and 2022; only [Bob-GGB](https://github.com/Bob-GGB/BusinessCardScannerVer3)
(Swift, 3 stars) is still moving. They return name, phone and email as text: no label mapping
and no write path, so the contact is still assembled by hand. One of the better-looking ones,
[krayc425](https://github.com/krayc425/BusinessCardScanner), is a client for the ABBYY and
CamCard commercial APIs — open source wrapping the paid service, not replacing it. What the
cluster does get free is R4: regex has no model to inject into. That is the trade in one line,
because regex also cannot read a card the way a model can.

**The personal CRMs fail R3 on purpose.** Monica and Twenty are excellent and enormous, and a
second contact database is their entire product — the thing this tool refuses to become. None
ingests a card photo. [harperreed/crm](https://github.com/harperreed/crm) is the nearest
neighbour in spirit (Go, Google sync, MCP server, active) and still starts from contacts that
already exist.

**n8n is the only real open-source path to the same outcome**, and it is a fair comparison:
self-hosted, a vision node into the Google Contacts node, done. What it costs is the platform
to run and a workflow to maintain, a metered API key instead of a subscription CLI, no review
screen unless you build one, and no containment — an n8n workflow runs with whatever
credentials the node holds, which is the R4 failure this app was designed around.

A fourth group is large and irrelevant: dozens of "digital business card" and vCard-generator
repos solve the inverse problem, sharing your own card rather than filing someone else's.

### Where this app lands

R1 to R6, by construction. The two that nothing else in the table holds together are **R1 with
R2** — an arbitrary scrap in, a correctly-labelled contact out — and **R4**: the parse runs in a
throwaway temp directory holding only the image, the prompt goes in over stdin, and POSTs are
same-origin only. Image-based prompt injection is a [documented 2026 attack
class](https://labs.cloudsecurityalliance.org/research/csa-research-note-image-prompt-injection-multimodal-llm-2026/)
and [OWASP's answer is sandboxing, not filtering](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).
Nothing above states a threat model at all.

**Where they win, and it is not close.** Conference batch capture, CRM push and team sharing
are what CamCard and Covve are for; CJK OCR is theirs. Here there is no mobile app (backlog 1),
no duplicate detection (backlog 2), and setup is a 15-minute OAuth registration against their
install-and-go. One person, a few contacts a week, is the only frame in which this comparison
flatters the app.

Legend: ✓ meets it · ~ partly · ✗ does not.

## Architecture and why

Single file, `app.py`: Flask server, embedded HTML/CSS/JS, all routes.
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

**Mirror the camera preview** (2026-08-18). `#cam` gets `transform:scaleX(-1)`. The Mac's
camera faces the user, so the raw feed moved the card left when you moved it right, and
reversed tilt; vertical was never affected. *Cost:* card text reads backwards while aiming.
*Not done:* mirroring the captured frame — that would reverse the text and break parsing.
`drawImage` reads decoded video frames, so the CSS transform never touches the saved JPEG.
*Deferred:* mirroring only a user-facing camera (`getSettings().facingMode`) — needed when
backlog item 1 puts a phone's rear camera in the loop.

**Two-layer error messages** (2026-09-22, `dfe1689`). An Anthropic outage reached the
page as "claude CLI failed": the CLI prints API errors on stdout and exits 1 with an
empty stderr, and the app relayed only stderr. Parse and Google failures now return a
plain message with one fixed next step (try again, check status.claude.com; or delete
`token.json` and authorise again) plus a `detail` field holding the raw service text,
shown under a closed "Technical details" element labelled as unedited and possibly
cryptic. Guidance is fixed per endpoint, never derived from the raw text. *Rejected:*
inspecting vendor error strings to choose advice — the logic grows without bound and is
wrong on the first message it has not seen.

**Multi-page cards: one call, the model merges** (2026-09-29). Up to `MAX_PAGES = 4`
photos go to Claude in a single parse; the prompt treats them as sides of one card and
routes details that fit no field (second address, other-script name, extra sites,
branches) into Notes. The camera still takes one shot per press; each thumbnail has its
own remove button. Upload cap raised from 20 to 40 MB total. CLI page files carry the real
image extension, because the Read tool keys on it. *Rejected:* one parse per page merged
in JS — hand-written conflict rules and several confidence scores; stitching the photos
into one canvas — lower resolution per page for no saving on the server.

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
6. **Block private addresses in URL fetch** *(deferred 2026-09-29; do with item 1)*.
   `fetch_url_text` fetches any URL, including loopback, LAN and link-local hosts. Harmless
   while only this Mac reaches the page; once Tailscale lets other devices in, resolve the host
   with `ipaddress` and reject private ranges on every redirect hop (the naive check misses a
   public URL that redirects inward).
7. **Tests for the in-page JS** *(deferred 2026-09-29)*. vCard builder, label maps and the
   confidence pill are untested; the JS lives inside a Python string, so testing needs Node or
   Playwright plus extraction. Cheapest route if it ever matters: move `buildVcard` server-side
   — at the cost of the zero-setup, no-round-trip vCard path.
