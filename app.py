#!/usr/bin/env python3
"""Contact Dropper — drop text / image / URL, parse with Claude, create a Google Contact.

Run:  python app.py   then open http://localhost:8321
Parses via the Claude Code CLI (your Claude subscription) by default — no API key needed.
Set ANTHROPIC_API_KEY to use the metered API instead. Requires credentials.json
(Google OAuth client) in this folder.
"""

import base64
import json
import os
import re

import requests
from flask import Flask, jsonify, request

# ---------------------------------------------------------------- config
CLAUDE_MODEL = "claude-haiku-4-5-20251001"  # API path: cheap + good enough for parsing
CLI_MODEL = "sonnet"                         # CLI path: fast, strong, free on your subscription
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SCOPES = ["https://www.googleapis.com/auth/contacts"]
PORT = 8321
HERE = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # bound uploaded image size

# ---------------------------------------------------------------- google auth
def google_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    token_path = os.path.join(HERE, "token.json")
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(HERE, "credentials.json"), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
        os.chmod(token_path, 0o600)  # token is a real credential — owner-only
    return build("people", "v1", credentials=creds)

# ---------------------------------------------------------------- claude parsing
PROMPT = """Extract contact information from the input. Respond with ONLY a JSON object,
no markdown fences, using exactly these keys (use "" or [] when unknown):
{"honorificPrefix":"","givenName":"","familyName":"","company":"","jobTitle":"",
"phones":[{"value":"","type":"mobile"}],"emails":[{"value":"","type":"work"}],
"street":"","city":"","region":"","postalCode":"","country":"","countryCode":"",
"website":"","socials":[{"value":"","type":"profile"}],"notes":"",
"confidence":100,"parseComment":""}

Rules:
- phones: one object per number. "type" MUST be one of: mobile, work, home, main,
  workMobile, workFax, homeFax, pager, other. Classify from the card's own cues —
  "Mobile / Cell / M / HP / Hand phone", or a mobile-format number => mobile;
  "Tel / Office / Direct / Landline / T / Phone" => work; "Fax / F" => workFax.
  A single unlabeled number in mobile format => mobile, else => work. Keep numbers in
  international format when the country is inferable.
- emails: one object per address. "type" MUST be one of: work, home, other. Default to
  "work"; use "home" only for an obviously personal address (personal gmail/hotmail/
  yahoo domain with no company context).
- socials: LinkedIn / X (Twitter) / Instagram / Facebook / GitHub etc. Output the full
  profile URL — build it from an @handle when the platform is clear (linkedin.com/in/...,
  x.com/handle, github.com/handle). "type" is always "profile".
- country / countryCode: keep them in sync. "country" is the full name (e.g. China),
  "countryCode" its ISO 3166-1 alpha-2 code (e.g. CN, DE, US). Infer both from the
  address, phone country code, or language when only one is present. If you set one,
  set the other; leave both "" only when there is no country signal at all.
- website: the company or personal homepage, NOT a social profile.
- honorificPrefix: a name title such as Dr., Prof., Mr., Ms., Datuk. Put it ONLY here,
  never in givenName or notes.
- confidence: integer 0-100 scoring THIS parse. 90-100: clean input, every
  visible field extracted unambiguously. 70-89: minor uncertainty (one guessed
  label, partial address, low-res but readable). 40-69: notable gaps or guesses.
  Below 40: badly degraded input (blurry, truncated, conflicting).
- parseComment: one short sentence on anything the user should check. ALWAYS
  name the specific field and the cause when an item could not be fully
  identified, e.g. "familyName incomplete - a finger covers part of the card",
  "postalCode unreadable - left empty", "second phone labelled work by guess -
  card gives no cue". Empty string when everything parsed cleanly.
- notes: only information from the input itself. NEVER put parsing-quality
  remarks in notes - they belong in parseComment."""


def _strip_json(text):
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


def _parse_via_api(content_blocks):
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY,
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": CLAUDE_MODEL, "max_tokens": 1024,
              "messages": [{"role": "user", "content": content_blocks}]},
        timeout=60)
    r.raise_for_status()
    return _strip_json(r.json()["content"][0]["text"])


def _parse_via_cli(content_blocks):
    """Reuse the logged-in Claude Code CLI → bills your subscription, no API key.
    Runs in a throwaway temp dir holding only the card image: headless claude can
    Read files inside its cwd but nothing outside it, so a prompt injected via a
    malicious card/webpage can't reach credentials.json, token.json, or any other
    file on disk."""
    import shutil
    import subprocess
    import tempfile

    prompt = "\n\n".join(b["text"] for b in content_blocks if b["type"] == "text")
    workdir = tempfile.mkdtemp(prefix="contact-capture-")
    try:
        for b in content_blocks:
            if b["type"] == "image":
                img = os.path.join(workdir, "card.png")
                with open(img, "wb") as f:
                    f.write(base64.b64decode(b["source"]["data"]))
                prompt += f"\n\nAn image is saved at {img} — read it and extract from it too."
        # Prompt via stdin so variadic flags can't swallow it.
        r = subprocess.run(["claude", "-p", "--model", CLI_MODEL], input=prompt,
                           capture_output=True, text=True, timeout=180, cwd=workdir)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or "claude CLI failed")
        return _strip_json(r.stdout)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def claude_parse(content_blocks):
    return _parse_via_api(content_blocks) if ANTHROPIC_API_KEY else _parse_via_cli(content_blocks)


def fetch_url_text(url):
    resp = requests.get(url, timeout=20, stream=True, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
    raw = resp.raw.read(500_000, decode_content=True)  # cap download; text is cut to 15k below
    html = raw.decode(resp.encoding or "utf-8", "replace")
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text)[:15000]

# ---------------------------------------------------------------- routes
@app.before_request
def _same_origin_only():
    # Reject cross-site POSTs (localhost-CSRF guard): a request from another
    # page carries its own Origin; requests from this app's page match ours.
    if request.method == "POST":
        origin = request.headers.get("Origin", "")
        ours = (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}")
        if origin and origin not in ours:
            return jsonify(error="Cross-origin request blocked."), 403


@app.post("/parse")
def parse():
    blocks = [{"type": "text", "text": PROMPT}]
    img = request.files.get("image")
    text = (request.form.get("text") or "").strip()
    if img:
        blocks.append({"type": "image", "source": {
            "type": "base64",
            "media_type": img.mimetype or "image/png",
            "data": base64.b64encode(img.read()).decode()}})
    if text:
        if re.match(r"^https?://\S+$", text):
            try:
                text = f"Content of {text} :\n" + fetch_url_text(text)
            except Exception as e:
                return jsonify(error=f"Could not fetch URL: {e}"), 400
        blocks.append({"type": "text", "text": text})
    if len(blocks) == 1:
        return jsonify(error="Nothing to parse — paste text, a URL, or drop an image."), 400
    try:
        data = claude_parse(blocks)
        conf = data.get("confidence")
        data["confidence"] = (max(0, min(100, int(conf)))
                              if isinstance(conf, (int, float)) else None)
        data["parseComment"] = str(data.get("parseComment") or "")
        return jsonify(data)
    except Exception as e:
        return jsonify(error=f"Parsing failed: {e}"), 500


@app.post("/create")
def create():
    c = request.get_json(force=True)
    body = {}
    if c.get("givenName") or c.get("familyName") or c.get("honorificPrefix"):
        body["names"] = [{"honorificPrefix": c.get("honorificPrefix", ""),
                          "givenName": c.get("givenName", ""),
                          "familyName": c.get("familyName", "")}]
    if c.get("company") or c.get("jobTitle"):
        body["organizations"] = [{"name": c.get("company", ""),
                                  "title": c.get("jobTitle", "")}]
    phones = [{"value": p["value"], "type": p.get("type") or "mobile"}
              for p in c.get("phones", []) if p.get("value")]
    if phones:
        body["phoneNumbers"] = phones
    emails = [{"value": e["value"], "type": e.get("type") or "work"}
              for e in c.get("emails", []) if e.get("value")]
    if emails:
        body["emailAddresses"] = emails
    if any(c.get(k) for k in ("street", "city", "region", "postalCode", "country")):
        body["addresses"] = [{"streetAddress": c.get("street", ""),
                              "city": c.get("city", ""),
                              "region": c.get("region", ""),
                              "postalCode": c.get("postalCode", ""),
                              "country": c.get("country", ""),
                              "countryCode": c.get("countryCode", "")}]
    urls = []
    if c.get("website"):
        urls.append({"value": c["website"], "type": "homePage"})
    urls += [{"value": s["value"], "type": "profile"}
             for s in c.get("socials", []) if s.get("value")]
    if urls:
        body["urls"] = urls
    if c.get("notes"):
        body["biographies"] = [{"value": c["notes"]}]
    if not body:
        return jsonify(error="All fields empty — nothing to create."), 400
    try:
        person = google_service().people().createContact(body=body).execute()
        rid = person["resourceName"].split("/")[-1]
        return jsonify(ok=True, link=f"https://contacts.google.com/person/{rid}")
    except Exception as e:
        return jsonify(error=f"Google Contacts error: {e}"), 500


@app.get("/")
def index():
    if os.path.exists(os.path.join(HERE, "token.json")):
        state = "ready"           # authorized — Google button shows normal
    elif os.path.exists(os.path.join(HERE, "credentials.json")):
        state = "needs-auth"      # first create will open the Google sign-in
    else:
        state = "needs-setup"     # no OAuth client — Google path unavailable
    return HTML.replace("__GOOGLE_STATE__", state)

# ---------------------------------------------------------------- UI
HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📇</text></svg>">
<title>Contacts quick capture to Google</title>
<style>
 :root{--accent:#2563eb;--accent-h:#1d4ed8;--bg:#f4f5f7;--card:#fff;--text:#1f2937;
   --muted:#6b7280;--border:#e5e7eb;--field:#d1d5db;--danger:#b91c1c}
 *{box-sizing:border-box}
 body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);
   color:var(--text);margin:0;min-height:100vh;display:flex;justify-content:center;
   align-items:flex-start;padding:1.5rem 1rem;line-height:1.4}
 .card{background:var(--card);width:min(1140px,100%);border:1px solid var(--border);border-radius:16px;
   box-shadow:0 1px 3px rgba(0,0,0,.06),0 10px 30px rgba(0,0,0,.05);padding:1.4rem 1.6rem}
 .cols{display:grid;grid-template-columns:1fr 1fr .6fr;gap:1.4rem;margin-top:1rem;align-items:start}
 @media(max-width:900px){.cols{grid-template-columns:1fr}}
 .actions2{display:grid;grid-template-columns:1fr 1fr;gap:.55rem;margin-top:.9rem}
 .lbl{font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);font-weight:600;margin-bottom:.4rem}
 .ph{color:var(--muted);font-size:.85rem;border:1px dashed var(--border);border-radius:12px;padding:1.1rem;text-align:center}
 .okbox{border:1px solid #cbe5cf;background:#f2fbf4;border-radius:12px;padding:1rem;font-size:.9rem}
 .okbox .ok{color:#137333;font-weight:700;margin-bottom:.35rem}
 .okbox a{color:var(--accent);font-weight:600;word-break:break-word}
 h1{font-size:1.35rem;margin:0 0 .2rem;letter-spacing:-.01em}
 .sub{margin:0 0 1.1rem;color:var(--muted);font-size:.9rem}
 #drop{border:2px dashed #cbd5e1;border-radius:12px;padding:1.1rem;min-height:190px;outline:none;
   white-space:pre-wrap;overflow:auto;max-height:280px;background:#fcfcfd;transition:border-color .15s,box-shadow .15s}
 #drop:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(37,99,235,.13)}
 #drop.empty:before{content:"Paste or drop anything — text, screenshot, image, or a URL";color:#9ca3af}
 img.thumb{width:100%;max-height:190px;object-fit:contain;display:block;margin-top:.6rem;border-radius:8px}
 #cam{width:100%;max-height:300px;border-radius:12px;background:#000;margin-top:.6rem}
 .btnrow{display:flex;gap:.55rem;flex-wrap:wrap;margin-top:.9rem}
 .btn{font:inherit;font-weight:600;font-size:.92rem;padding:.55rem 1.1rem;border-radius:10px;
   border:1px solid transparent;cursor:pointer;transition:background .15s,border-color .15s,color .15s}
 .btn-primary{background:var(--accent);color:#fff} .btn-primary:hover{background:var(--accent-h)}
 .btn-ghost{background:#fff;color:var(--text);border-color:var(--field)} .btn-ghost:hover{background:#f9fafb}
 .btn-ghost.danger{color:var(--danger);border-color:#f0cccc} .btn-ghost.danger:hover{background:#fef2f2}
 .btn:disabled{opacity:.5;cursor:default}
 .btn-sm{padding:.3rem .75rem;font-size:.8rem;font-weight:500;margin-top:.45rem}
 label{display:block;font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;
   color:var(--muted);font-weight:600;margin:.55rem 0 .22rem}
 #form>.row:first-child label{margin-top:0}
 input,textarea,select{width:100%;padding:.48rem .6rem;border:1px solid var(--field);border-radius:10px;
   font-size:.95rem;background:#fff;font-family:inherit;transition:border-color .15s,box-shadow .15s}
 input:focus,textarea:focus,select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(37,99,235,.13)}
 .row{display:flex;gap:.6rem} .row>div{flex:1} .narrow{flex:.55!important}
 .pv{display:flex;gap:.6rem;margin-top:.4rem} .pv input{flex:3} .pv select{flex:2;min-width:0}
 .create{width:100%;margin-top:.7rem;padding:.72rem;font-size:.98rem}
 .hint{font-size:.72rem;color:var(--muted);margin-top:.3rem;text-align:center;min-height:.9rem}
 .conf{display:none;margin-top:.8rem}
 .confpill{display:inline-block;font-weight:700;font-size:.8rem;padding:.25rem .7rem;
   border-radius:999px;color:#fff}
 .conf .note{margin-top:.35rem;color:var(--muted);font-size:.8rem}
 .okbox .how{margin-top:.45rem;font-size:.8rem;color:var(--muted)}
 #msg{margin-top:1rem;font-size:.92rem;color:var(--muted)} #msg a{color:var(--accent);font-weight:600}
 .err{color:var(--danger)}
</style></head><body>
<div class="card">
<h1>Contacts quick capture to Google</h1>
<p class="sub">Take picture, drop screenshot, image, text, URL and parse. Save as Google Contact or vCard after review.</p>
<div class="cols">
<div class="col">
<div id="drop" class="empty" contenteditable="true"></div>
<div id="camwrap" style="display:none">
 <video id="cam" autoplay playsinline muted></video>
 <div class="btnrow"><button id="snap" class="btn btn-primary">Capture</button>
   <button id="camcancel" class="btn btn-ghost">Cancel</button></div>
</div>
<div class="actions2">
 <button id="camera" class="btn btn-ghost">📷 Camera</button>
 <button id="clear" class="btn btn-ghost danger">Clear</button>
</div>
<button id="parse" class="btn btn-primary create">Parse contact information</button>
<canvas id="canvas" style="display:none"></canvas>
<div id="conf" class="conf"><span id="confpill" class="confpill"></span>
 <div id="confnote" class="note"></div></div>
<div id="msg"></div>
</div>
<div class="col">
<div id="form">
 <div class="row"><div class="narrow"><label>Prefix</label><input id="honorificPrefix"></div>
   <div><label>First name</label><input id="givenName"></div>
   <div><label>Last name</label><input id="familyName"></div></div>
 <div class="row"><div><label>Company</label><input id="company"></div>
   <div><label>Title</label><input id="jobTitle"></div></div>
 <label>Phones</label><div id="phones"></div>
 <label>Emails</label><div id="emails"></div>
 <label>Street</label><input id="street">
 <div class="row"><div><label>City</label><input id="city"></div>
   <div><label>Region/State</label><input id="region"></div>
   <div><label>Postcode</label><input id="postalCode"></div></div>
 <label>Country</label><input id="country">
 <div class="row"><div><label>Website</label><input id="website"></div>
   <div><label>Social profiles</label><input id="socials"></div></div>
 <label>Notes</label><textarea id="notes" rows="2"></textarea>
 <div class="actions2">
  <div><button id="create" class="btn btn-primary create" disabled>Create Google Contact</button>
   <div id="gstate" class="hint"></div></div>
  <div><button id="vcard" class="btn btn-primary create" disabled>Download vCard</button></div>
 </div>
</div>
</div>
<div class="col success-col">
<div class="lbl">Last saved contact</div>
<div id="success"><div class="ph">Your saved contact appears here after you create it in Google or download a vCard.</div></div>
</div>
</div>
</div>
<script>
const drop=document.getElementById('drop'),msg=document.getElementById('msg');
let imageBlob=null;
function showErr(t){msg.textContent='';const s=document.createElement('span');
  s.className='err';s.textContent=t;msg.appendChild(s);}
// parse-confidence widget: pill green>=80 / amber>=50 / red below, plus comment
const confEl=document.getElementById('conf'),confPill=document.getElementById('confpill'),
  confNote=document.getElementById('confnote');
function hideConf(){confEl.style.display='none';}
function showConf(score,comment){
  if(typeof score!=='number'){hideConf();return;}
  confPill.style.background=score>=80?'#137333':score>=50?'#b45309':'#b91c1c';
  confPill.textContent='Parse confidence: '+score+'%';
  let note=comment||'';
  if(score<50)note+=(note?' — ':'')+'Consider a sharper capture.';
  confNote.textContent=note;confNote.style.display=note?'block':'none';
  confEl.style.display='block';
}
// server-injected Google auth state: ready | needs-auth | needs-setup
const GOOGLE_STATE='__GOOGLE_STATE__',gstate=document.getElementById('gstate');
if(GOOGLE_STATE==='needs-auth')gstate.textContent='requires Google auth';
if(GOOGLE_STATE==='needs-setup')gstate.textContent='requires Google setup — see README';
const SIMPLE=['honorificPrefix','givenName','familyName','company','jobTitle','street','city',
  'region','postalCode','country','website','notes'];
const PHONE_TYPES=[['mobile','Mobile'],['work','Work'],['home','Home'],['main','Main'],
  ['workMobile','Work mobile'],['workFax','Work fax'],['homeFax','Home fax'],
  ['pager','Pager'],['other','Other']];
const EMAIL_TYPES=[['work','Work'],['home','Home'],['other','Other']];
function addRow(kind,value,type){
  const opts=kind==='phones'?PHONE_TYPES:EMAIL_TYPES, def=kind==='phones'?'mobile':'work';
  const div=document.createElement('div');div.className='row pv';
  const inp=document.createElement('input');inp.value=value||'';
  const sel=document.createElement('select');let matched=false;
  for(const[v,l]of opts){const o=new Option(l,v);if(v===(type||def)){o.selected=true;matched=true;}
    sel.add(o);}
  if(type&&!matched)sel.add(new Option(type,type,true,true)); // keep a custom label Claude returned
  div.append(inp,sel);document.getElementById(kind).appendChild(div);
}
function fillRows(kind,arr){const c=document.getElementById(kind);c.innerHTML='';
  const def=kind==='phones'?'mobile':'work';
  (arr&&arr.length?arr:[{value:'',type:def}]).forEach(x=>addRow(kind,x.value,x.type));}
function collectRows(kind){return [...document.getElementById(kind).querySelectorAll('.row')]
  .map(r=>({value:r.querySelector('input').value.trim(),type:r.querySelector('select').value}))
  .filter(x=>x.value);}
drop.addEventListener('input',()=>drop.classList.toggle('empty',!drop.textContent.trim()&&!imageBlob));
function addImage(blob){imageBlob=blob;   // one image per capture — a new one replaces it
  const old=drop.querySelector('img.thumb');if(old){URL.revokeObjectURL(old.src);old.remove();}
  const i=document.createElement('img');i.className='thumb';
  i.src=URL.createObjectURL(blob);drop.appendChild(i);drop.classList.remove('empty');}
drop.addEventListener('paste',e=>{for(const it of e.clipboardData.items)
  if(it.type.startsWith('image/')){e.preventDefault();addImage(it.getAsFile());}});
drop.addEventListener('drop',e=>{e.preventDefault();
  for(const f of e.dataTransfer.files) if(f.type.startsWith('image/')) addImage(f);
  const t=e.dataTransfer.getData('text'); if(t) drop.append(t); drop.classList.remove('empty');});
drop.addEventListener('dragover',e=>e.preventDefault());

// camera: live preview → capture a frame → same image pipeline as a pasted screenshot
const camera=document.getElementById('camera'),camwrap=document.getElementById('camwrap'),
  cam=document.getElementById('cam'),canvas=document.getElementById('canvas');
let stream=null;
function stopCam(){if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}
  camwrap.style.display='none';camera.disabled=false;}
camera.onclick=async()=>{
  try{stream=await navigator.mediaDevices.getUserMedia(
    {video:{facingMode:'environment',width:{ideal:1920},height:{ideal:1080}}});}
  catch(e){showErr('Camera unavailable: '+e.message);return;}
  cam.srcObject=stream;camwrap.style.display='block';camera.disabled=true;msg.textContent='';};
document.getElementById('camcancel').onclick=stopCam;
document.getElementById('snap').onclick=()=>{
  canvas.width=cam.videoWidth;canvas.height=cam.videoHeight;
  canvas.getContext('2d').drawImage(cam,0,0);
  canvas.toBlob(b=>{addImage(b);stopCam();},'image/jpeg',0.92);};

document.getElementById('parse').onclick=async()=>{
  const btn=document.getElementById('parse');
  btn.disabled=true; msg.textContent='Parsing…'; hideConf();
  const fd=new FormData();
  fd.append('text',drop.textContent.trim());
  if(imageBlob) fd.append('image',imageBlob,'image.png');
  let d;
  try{const r=await fetch('/parse',{method:'POST',body:fd}); d=await r.json();}
  catch(e){showErr('Request failed: '+e.message);return;}
  finally{btn.disabled=false;}
  if(d.error){showErr(d.error);return;}
  for(const f of SIMPLE)document.getElementById(f).value=d[f]||'';
  fillRows('phones',d.phones); fillRows('emails',d.emails);
  document.getElementById('socials').value=(d.socials||[]).map(s=>s.value||s).join(', ');
  // always log capture month+year as the first notes line
  const my=new Date().toLocaleDateString('en-US',{month:'short',year:'numeric'});
  const nEl=document.getElementById('notes'); nEl.value=my+(nEl.value?'\\n'+nEl.value:'');
  parsed=true; refreshCreate();
  showConf(d.confidence,d.parseComment);
  if(hasAnyData())msg.textContent='Review, edit if needed, then save.';
  else showErr('No contact info found — edit fields or try again.');
};
function collectContact(){
  const c={}; for(const f of SIMPLE)c[f]=document.getElementById(f).value.trim();
  c.phones=collectRows('phones'); c.emails=collectRows('emails');
  c.socials=document.getElementById('socials').value.split(',').map(s=>s.trim())
    .filter(Boolean).map(v=>({value:v,type:'profile'}));
  return c;
}
function successBox(title,...nodes){
  const box=document.createElement('div');box.className='okbox';
  const ok=document.createElement('div');ok.className='ok';ok.textContent=title;
  box.append(ok,...nodes);
  const s=document.getElementById('success');s.innerHTML='';s.appendChild(box);
}
document.getElementById('create').onclick=async()=>{
  document.getElementById('create').disabled=true;   // no double-create
  msg.textContent='Creating… (first run opens a Google login window in your browser)';
  let d;
  try{const r=await fetch('/create',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(collectContact())}); d=await r.json();}
  catch(e){showErr('Request failed: '+e.message);refreshCreate();return;}
  if(d.error){showErr(d.error);refreshCreate();return;}
  const a=document.createElement('a');a.href=d.link;a.target='_blank';
  a.textContent='Open in Google Contacts →';
  successBox('✓ Contact created',a);
  gstate.textContent='';   // a create succeeded, so auth is done
  resetForm(); msg.textContent='';
};

// vCard export — the zero-setup path: built client-side, imports anywhere
const BS=String.fromCharCode(92);  // backslash, kept out of literals in this embedded JS
function vesc(s){return String(s).split(BS).join(BS+BS).split(';').join(BS+';')
  .split(',').join(BS+',').split('\\n').join(BS+'n');}
const TELMAP={mobile:'CELL',work:'WORK',home:'HOME',workFax:'WORK,FAX',homeFax:'HOME,FAX',
  pager:'PAGER',workMobile:'WORK,CELL',main:'VOICE',other:'VOICE'};
function buildVcard(c){
  const L=['BEGIN:VCARD','VERSION:3.0'];
  L.push('N:'+[c.familyName,c.givenName,'',c.honorificPrefix,''].map(vesc).join(';'));
  L.push('FN:'+vesc([c.honorificPrefix,c.givenName,c.familyName].filter(Boolean).join(' ')
    ||c.company||'Contact'));
  if(c.company)L.push('ORG:'+vesc(c.company));
  if(c.jobTitle)L.push('TITLE:'+vesc(c.jobTitle));
  for(const p of c.phones)L.push('TEL;TYPE='+(TELMAP[p.type]||'VOICE')+':'+vesc(p.value));
  for(const e of c.emails)L.push('EMAIL'+(e.type==='other'?'':';TYPE='+e.type.toUpperCase())
    +':'+vesc(e.value));
  if(c.street||c.city||c.region||c.postalCode||c.country)
    L.push('ADR:;;'+[c.street,c.city,c.region,c.postalCode,c.country].map(vesc).join(';'));
  if(c.website)L.push('URL:'+vesc(c.website));
  for(const s of c.socials)L.push('URL:'+vesc(s.value));
  if(c.notes)L.push('NOTE:'+vesc(c.notes));
  L.push('END:VCARD');
  return L.join('\\r\\n')+'\\r\\n';
}
let vcardUrl=null;
document.getElementById('vcard').onclick=()=>{
  const c=collectContact();
  const name=[c.givenName,c.familyName].filter(Boolean).join(' ');
  const file=((name||'contact').toLowerCase().split(' ').join('-'))+'.vcf';
  if(vcardUrl)URL.revokeObjectURL(vcardUrl);
  vcardUrl=URL.createObjectURL(new Blob([buildVcard(c)],{type:'text/vcard'}));
  const a=document.createElement('a');a.href=vcardUrl;a.download=file;a.click();
  const info=document.createElement('div');info.textContent=(name?name+' — ':'')+file;
  const again=document.createElement('a');again.href=vcardUrl;again.download=file;
  again.textContent='Download again';
  const againWrap=document.createElement('div');againWrap.appendChild(again);
  const how=document.createElement('div');how.className='how';
  how.append('Import: double-click (Apple Contacts), or ');
  const g=document.createElement('a');g.href='https://contacts.google.com';g.target='_blank';
  g.textContent='contacts.google.com';how.append(g,' → Import.');
  successBox('✓ vCard downloaded',info,againWrap,how);
  resetForm(); msg.textContent='';
};
function resetForm(){
  for(const f of SIMPLE)document.getElementById(f).value='';
  document.getElementById('socials').value='';
  fillRows('phones',[]); fillRows('emails',[]);
  drop.textContent='';imageBlob=null;drop.classList.add('empty');stopCam();
  parsed=false; refreshCreate(); hideConf();
}
document.getElementById('clear').onclick=()=>{resetForm();msg.textContent='';};

// Create activates only after Parse ran AND at least one real field has content
// (the auto month+year note alone doesn't count).
let parsed=false;
function hasAnyData(){
  for(const f of SIMPLE){if(f==='notes')continue;
    if(document.getElementById(f).value.trim())return true;}
  if(document.getElementById('socials').value.trim())return true;
  for(const k of ['phones','emails'])
    for(const inp of document.getElementById(k).querySelectorAll('input'))
      if(inp.value.trim())return true;
  return false;
}
function refreshCreate(){const ok=parsed&&hasAnyData();
  document.getElementById('create').disabled=!ok||GOOGLE_STATE==='needs-setup';
  document.getElementById('vcard').disabled=!ok;}
const formEl=document.getElementById('form');
formEl.addEventListener('input',refreshCreate); formEl.addEventListener('change',refreshCreate);
// initial state: empty labelled rows visible, Create disabled
fillRows('phones',[]); fillRows('emails',[]); refreshCreate();
</script></body></html>"""

if __name__ == "__main__":
    mode = ("metered API (ANTHROPIC_API_KEY)" if ANTHROPIC_API_KEY
            else f"Claude Code CLI / subscription — model {CLI_MODEL}")
    print(f"Parsing via: {mode}")
    print(f"Contact Dropper → http://localhost:{PORT}")
    app.run(port=PORT, debug=False)
