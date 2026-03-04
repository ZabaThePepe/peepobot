"""
app.py — Discord Bot + Dashboard z logowaniem przez Discord OAuth2
"""

import threading
import subprocess
import sys
import json
import os
import urllib.request
import urllib.parse
import hashlib
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DB_FILE = "levels.json"
CONFIG_FILE = "config.json"
SESSIONS_FILE = "sessions.json"

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
GUILD_ID = "1478527413146091651"
CLIENT_ID = "1033064888257486859"
CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "DaYer6LsFdopEbT6n8eXMitIZkTLHeyg")
REDIRECT_URI = "https://web-production-6ee1.up.railway.app/callback"
DISCORD_ADMIN_PERMISSION = 0x8  # Administrator flag


def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "stats": {"total_messages": 0, "total_voice_minutes": 0}}


def load_config():
    default = {"roles": [], "level_up_channel": None, "xp_per_message": 15, "xp_per_voice_minute": 5, "xp_cooldown": 60}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
            default.update(cfg)
    return default


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_sessions(sessions):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f)


def xp_to_level(xp):
    level = 0
    while (level + 1) ** 2 * 100 <= xp:
        level += 1
    return level


def xp_for_level(level):
    return level ** 2 * 100


def fetch_discord_roles():
    if os.path.exists("guild_roles.json"):
        with open("guild_roles.json", "r") as f:
            return json.load(f)
    return []


def get_cookie_session(headers):
    cookie = headers.get("Cookie", "")
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("session="):
            return part[8:]
    return None


def exchange_code(code):
    """Wymienia kod OAuth2 na access token"""
    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }).encode()
    req = urllib.request.Request(
        "https://discord.com/api/v10/oauth2/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def get_discord_user(access_token):
    """Pobiera dane użytkownika Discord"""
    req = urllib.request.Request(
        "https://discord.com/api/v10/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def get_guild_member(access_token):
    """Pobiera dane członka serwera"""
    req = urllib.request.Request(
        f"https://discord.com/api/v10/users/@me/guilds/{GUILD_ID}/member",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except:
        return None


def is_admin_on_guild(access_token):
    """Sprawdza czy user ma admina na serwerze"""
    member = get_guild_member(access_token)
    if not member:
        return False
    # Sprawdź przez role czy ma admina
    roles_data = fetch_discord_roles()
    # Pobierz pełne role serwera z pliku
    if os.path.exists("guild_roles_full.json"):
        with open("guild_roles_full.json", "r") as f:
            all_roles = json.load(f)
        role_map = {r["id"]: r for r in all_roles}
        member_role_ids = member.get("roles", [])
        for rid in member_role_ids:
            role = role_map.get(rid, {})
            perms = int(role.get("permissions", 0))
            if perms & DISCORD_ADMIN_PERMISSION:
                return True
    # Fallback: sprawdź czy jest właścicielem
    return member.get("permissions") is not None and (int(member.get("permissions", 0)) & DISCORD_ADMIN_PERMISSION) != 0


def login_page(error=""):
    oauth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&response_type=code"
        f"&scope=identify+guilds.members.read"
    )
    error_html = f'<div class="error">{error}</div>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🤖 Bot Dashboard — Logowanie</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg:#0d0e1a;--surface:#13152a;--border:#2a2d4a;
    --accent:#5865f2;--accent2:#7289da;--green:#57f287;--red:#ed4245;
    --text:#e8eaf6;--muted:#7986cb;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--text);font-family:'Space Mono',monospace;
    min-height:100vh;display:flex;align-items:center;justify-content:center}}
  body::before{{content:'';position:fixed;inset:0;
    background:radial-gradient(ellipse at 30% 30%,rgba(88,101,242,.12) 0%,transparent 60%),
               radial-gradient(ellipse at 70% 70%,rgba(114,137,218,.08) 0%,transparent 60%);
    pointer-events:none}}
  .card{{background:var(--surface);border:1px solid var(--border);border-radius:24px;
    padding:48px 40px;text-align:center;max-width:420px;width:90%;
    box-shadow:0 20px 60px rgba(0,0,0,.4);position:relative}}
  .card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;
    background:linear-gradient(90deg,var(--accent),var(--accent2));border-radius:24px 24px 0 0}}
  .logo{{font-size:4rem;margin-bottom:16px}}
  h1{{font-family:'Syne',sans-serif;font-weight:800;font-size:1.8rem;margin-bottom:8px}}
  p{{color:var(--muted);font-size:.85rem;margin-bottom:32px;line-height:1.6}}
  .btn-discord{{
    display:inline-flex;align-items:center;gap:12px;
    background:#5865f2;color:#fff;padding:14px 28px;border-radius:12px;
    text-decoration:none;font-family:'Space Mono',monospace;font-weight:700;
    font-size:.9rem;transition:all .2s;border:none;cursor:pointer;width:100%;
    justify-content:center;
  }}
  .btn-discord:hover{{background:#4752c4;transform:translateY(-2px);box-shadow:0 8px 24px rgba(88,101,242,.4)}}
  .discord-logo{{width:24px;height:24px;fill:white}}
  .error{{background:rgba(237,66,69,.1);border:1px solid rgba(237,66,69,.3);
    color:var(--red);padding:12px;border-radius:10px;margin-bottom:20px;font-size:.82rem}}
  .badge{{background:rgba(87,242,135,.1);border:1px solid rgba(87,242,135,.3);
    color:var(--green);padding:6px 14px;border-radius:20px;font-size:.72rem;
    display:inline-block;margin-bottom:24px}}
</style>
</head>
<body>
<div class="card">
  <div class="logo">🤖</div>
  <div class="badge">Tylko dla adminów serwera</div>
  <h1>Bot Dashboard</h1>
  <p>Zaloguj się przez Discord żeby zarządzać botem. Musisz mieć uprawnienia <strong>Administratora</strong> na serwerze.</p>
  {error_html}
  <a href="{oauth_url}" class="btn-discord">
    <svg class="discord-logo" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057c.002.022.015.043.033.055a19.879 19.879 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/>
    </svg>
    Zaloguj przez Discord
  </a>
</div>
</body>
</html>"""


def not_admin_page(username):
    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<title>Brak dostępu</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@800&family=Space+Mono&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0d0e1a;color:#e8eaf6;font-family:'Space Mono',monospace;
    min-height:100vh;display:flex;align-items:center;justify-content:center}}
  .card{{background:#13152a;border:1px solid #2a2d4a;border-radius:24px;padding:48px;text-align:center;max-width:420px}}
  h1{{font-family:'Syne',sans-serif;font-weight:800;font-size:1.6rem;margin:16px 0 8px;color:#ed4245}}
  p{{color:#7986cb;font-size:.85rem;margin-bottom:24px}}
  a{{color:#5865f2;text-decoration:none;font-size:.85rem}}
</style>
</head>
<body>
<div class="card">
  <div style="font-size:3rem">🚫</div>
  <h1>Brak uprawnień</h1>
  <p>Hej <strong>{username}</strong>, nie masz uprawnień Administratora na tym serwerze Discord.</p>
  <a href="/logout">← Zaloguj się innym kontem</a>
</div>
</body>
</html>"""


def get_dashboard_html(db, config, user_info, message=""):
    users = db.get("users", {})
    stats = db.get("stats", {})
    sorted_users = sorted(users.items(), key=lambda x: x[1].get("xp", 0), reverse=True)
    discord_roles = fetch_discord_roles()

    rows = ""
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, data) in enumerate(sorted_users[:20]):
        level = xp_to_level(data.get("xp", 0))
        next_xp = xp_for_level(level + 1)
        prev_xp = xp_for_level(level)
        progress = data.get("xp", 0) - prev_xp
        total = next_xp - prev_xp
        pct = int((progress / total) * 100) if total > 0 else 100
        medal = medals[i] if i < 3 else f"#{i+1}"
        name = data.get("username", f"User {uid}")
        bar_color = ["#ffd700", "#c0c0c0", "#cd7f32"][i] if i < 3 else "#5865f2"
        rows += f"""
        <tr>
            <td class="rank">{medal}</td>
            <td class="username">{name}</td>
            <td><span class="level-badge">Lvl {level}</span></td>
            <td class="xp-val">{data.get('xp', 0):,}</td>
            <td>
                <div class="progress-wrap">
                    <div class="progress-bar" style="width:{pct}%;background:{bar_color}"></div>
                </div>
                <small>{data.get('xp',0)}/{next_xp} XP</small>
            </td>
            <td>{data.get('messages', 0):,}</td>
            <td>{data.get('voice_minutes', 0):,}</td>
        </tr>"""

    roles = config.get("roles", [])
    roles_rows = ""
    for r in sorted(roles, key=lambda x: x["level"]):
        xp_needed = xp_for_level(r["level"])
        roles_rows += f"""
        <tr>
            <td><span class="level-badge">Lvl {r['level']}</span></td>
            <td>{xp_needed:,} XP</td>
            <td><span class="role-tag">{r['role_name']}</span></td>
            <td>
                <form method="POST" action="/remove_role" style="display:inline">
                    <input type="hidden" name="level" value="{r['level']}">
                    <button type="submit" class="btn btn-danger">Usuń</button>
                </form>
            </td>
        </tr>"""

    if not roles_rows:
        roles_rows = '<tr><td colspan="4" style="text-align:center;color:#888;padding:20px">Brak ról. Dodaj pierwszą poniżej!</td></tr>'

    if discord_roles:
        role_options = '<option value="">-- Wybierz rolę --</option>'
        for r in discord_roles:
            role_options += f'<option value="{r["id"]}" data-name="{r["name"]}">{r["name"]}</option>'
        role_select = f"""
        <div class="form-group">
            <label>Rola Discord</label>
            <select name="role_id" id="role-select" required>
                {role_options}
            </select>
        </div>
        <input type="hidden" name="role_name" id="role-name-hidden">"""
    else:
        role_select = """
        <div class="form-group">
            <label>ID Roli Discord</label>
            <input type="text" name="role_id" placeholder="np. 123456789" required>
        </div>
        <div class="form-group">
            <label>Nazwa roli</label>
            <input type="text" name="role_name" placeholder="np. Weteran" required>
        </div>"""

    avatar = user_info.get("avatar", "")
    uid = user_info.get("id", "")
    avatar_url = f"https://cdn.discordapp.com/avatars/{uid}/{avatar}.png" if avatar else "https://cdn.discordapp.com/embed/avatars/0.png"
    username = user_info.get("username", "Admin")

    msg_html = f'<div class="alert {"alert-success" if "✅" in message else "alert-error"}">{message}</div>' if message else ""
    total_users = len(users)
    total_msgs = stats.get("total_messages", 0)
    total_voice = stats.get("total_voice_minutes", 0)

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🤖 Bot Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg:#0d0e1a;--surface:#13152a;--surface2:#1a1d35;--border:#2a2d4a;
    --accent:#5865f2;--accent2:#7289da;--green:#57f287;--red:#ed4245;
    --text:#e8eaf6;--muted:#7986cb;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--text);font-family:'Space Mono',monospace;min-height:100vh}}
  body::before{{content:'';position:fixed;inset:0;
    background:radial-gradient(ellipse at 20% 20%,rgba(88,101,242,.08) 0%,transparent 60%),
               radial-gradient(ellipse at 80% 80%,rgba(114,137,218,.06) 0%,transparent 60%);
    pointer-events:none}}
  .container{{max-width:1200px;margin:0 auto;padding:0 20px 60px}}
  header{{padding:24px 0;border-bottom:1px solid var(--border);margin-bottom:32px;
    display:flex;align-items:center;justify-content:space-between}}
  .header-left{{display:flex;align-items:center;gap:16px}}
  .logo{{font-size:2rem}}
  header h1{{font-family:'Syne',sans-serif;font-weight:800;font-size:1.6rem;letter-spacing:-.5px}}
  header p{{color:var(--muted);font-size:.75rem;margin-top:2px}}
  .status-dot{{width:8px;height:8px;border-radius:50%;background:var(--green);
    box-shadow:0 0 8px var(--green);animation:pulse 2s infinite;display:inline-block;margin-left:6px}}
  @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.5}}}}
  .user-bar{{display:flex;align-items:center;gap:10px}}
  .user-avatar{{width:36px;height:36px;border-radius:50%;border:2px solid var(--accent)}}
  .user-name{{font-size:.82rem;color:var(--muted)}}
  .logout-btn{{background:rgba(237,66,69,.15);color:var(--red);border:1px solid rgba(237,66,69,.3);
    padding:6px 12px;border-radius:8px;font-size:.72rem;text-decoration:none;font-family:'Space Mono',monospace}}
  .logout-btn:hover{{background:var(--red);color:#fff}}
  .stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:32px}}
  .stat-card{{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:20px;
    position:relative;overflow:hidden;transition:transform .2s,border-color .2s}}
  .stat-card:hover{{transform:translateY(-2px);border-color:var(--accent)}}
  .stat-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;
    background:linear-gradient(90deg,var(--accent),var(--accent2))}}
  .stat-icon{{font-size:1.8rem;margin-bottom:8px}}
  .stat-val{{font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:var(--accent)}}
  .stat-label{{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:1px;margin-top:4px}}
  .section{{background:var(--surface);border:1px solid var(--border);border-radius:20px;margin-bottom:24px;overflow:hidden}}
  .section-header{{padding:20px 24px;border-bottom:1px solid var(--border);display:flex;align-items:center;
    justify-content:space-between;background:var(--surface2)}}
  .section-title{{font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;letter-spacing:.5px}}
  .section-body{{padding:24px}}
  table{{width:100%;border-collapse:collapse}}
  th{{color:var(--muted);font-size:.7rem;text-transform:uppercase;letter-spacing:1.5px;padding:0 12px 12px;text-align:left}}
  td{{padding:12px;border-bottom:1px solid var(--border);font-size:.82rem}}
  tr:last-child td{{border-bottom:none}}
  tr:hover td{{background:rgba(88,101,242,.05)}}
  .rank{{font-size:1.1rem;width:48px}}
  .username{{font-weight:700;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .xp-val{{color:var(--accent);font-weight:700;font-family:'Syne',sans-serif}}
  .level-badge{{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;
    padding:3px 10px;border-radius:20px;font-size:.75rem;font-weight:700;white-space:nowrap}}
  .role-tag{{background:rgba(88,101,242,.2);border:1px solid rgba(88,101,242,.4);
    color:var(--accent2);padding:3px 10px;border-radius:20px;font-size:.75rem}}
  .progress-wrap{{background:var(--border);border-radius:4px;height:6px;margin-bottom:3px;overflow:hidden}}
  .progress-bar{{height:100%;border-radius:4px}}
  .form-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;align-items:end}}
  .form-group{{display:flex;flex-direction:column;gap:6px}}
  label{{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:1px}}
  input[type="text"],input[type="number"],select{{
    background:var(--bg);border:1px solid var(--border);color:var(--text);
    padding:10px 14px;border-radius:10px;font-family:'Space Mono',monospace;
    font-size:.85rem;transition:border-color .2s;width:100%}}
  select option{{background:var(--surface2)}}
  input:focus,select:focus{{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(88,101,242,.15)}}
  .btn{{padding:10px 20px;border-radius:10px;border:none;cursor:pointer;font-family:'Space Mono',monospace;
    font-size:.82rem;font-weight:700;transition:all .2s;text-transform:uppercase;letter-spacing:.5px}}
  .btn-primary{{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff}}
  .btn-primary:hover{{transform:translateY(-1px);box-shadow:0 4px 16px rgba(88,101,242,.4)}}
  .btn-danger{{background:rgba(237,66,69,.15);color:var(--red);border:1px solid rgba(237,66,69,.3);padding:6px 12px;font-size:.75rem}}
  .btn-danger:hover{{background:var(--red);color:#fff}}
  .alert{{padding:12px 16px;border-radius:10px;margin-bottom:20px;font-size:.85rem}}
  .alert-success{{background:rgba(87,242,135,.1);border:1px solid rgba(87,242,135,.3);color:var(--green)}}
  .alert-error{{background:rgba(237,66,69,.1);border:1px solid rgba(237,66,69,.3);color:var(--red)}}
  .xp-ref{{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}}
  .xp-chip{{background:var(--surface2);border:1px solid var(--border);padding:6px 12px;border-radius:8px;font-size:.75rem;color:var(--muted)}}
  .xp-chip span{{color:var(--accent);font-weight:700}}
  @media(max-width:768px){{.form-grid{{grid-template-columns:1fr}}table{{font-size:.75rem}}th:nth-child(n+5),td:nth-child(n+5){{display:none}}}}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="header-left">
      <div class="logo">🤖</div>
      <div>
        <h1>Discord Level Bot <span class="status-dot"></span></h1>
        <p>Dashboard administracyjny · {total_users} użytkowników</p>
      </div>
    </div>
    <div class="user-bar">
      <img src="{avatar_url}" class="user-avatar" alt="">
      <span class="user-name">{username}</span>
      <a href="/logout" class="logout-btn">Wyloguj</a>
    </div>
  </header>

  {msg_html}

  <div class="stats-grid">
    <div class="stat-card"><div class="stat-icon">👥</div><div class="stat-val">{total_users}</div><div class="stat-label">Użytkownicy</div></div>
    <div class="stat-card"><div class="stat-icon">💬</div><div class="stat-val">{total_msgs:,}</div><div class="stat-label">Wiadomości</div></div>
    <div class="stat-card"><div class="stat-icon">🎙️</div><div class="stat-val">{total_voice}</div><div class="stat-label">Minut voice</div></div>
    <div class="stat-card"><div class="stat-icon">🏅</div><div class="stat-val">{len(roles)}</div><div class="stat-label">Skonfig. rang</div></div>
  </div>

  <div class="section">
    <div class="section-header">
      <span class="section-title">🏅 Role za Poziomy</span>
      <span style="color:var(--muted);font-size:.75rem">Automatyczne przyznawanie ról Discord</span>
    </div>
    <div class="section-body">
      <table>
        <thead><tr><th>Poziom</th><th>XP Wymagane</th><th>Nazwa Roli</th><th>Akcja</th></tr></thead>
        <tbody>{roles_rows}</tbody>
      </table>
      <hr style="border-color:var(--border);margin:24px 0">
      <p style="font-size:.85rem;color:var(--muted);margin-bottom:16px">➕ Dodaj nową rolę za poziom</p>
      <form method="POST" action="/add_role">
        <div class="form-grid">
          <div class="form-group">
            <label>Poziom (np. 5)</label>
            <input type="number" name="level" min="1" max="100" placeholder="5" required>
          </div>
          {role_select}
          <div class="form-group">
            <label>&nbsp;</label>
            <button type="submit" class="btn btn-primary" onclick="updateRoleName()">Dodaj Rolę</button>
          </div>
        </div>
      </form>
      <div class="xp-ref">
        <div class="xp-chip">Lvl 1 = <span>100 XP</span></div>
        <div class="xp-chip">Lvl 3 = <span>900 XP</span></div>
        <div class="xp-chip">Lvl 5 = <span>2,500 XP</span></div>
        <div class="xp-chip">Lvl 7 = <span>4,900 XP</span></div>
        <div class="xp-chip">Lvl 10 = <span>10,000 XP</span></div>
        <div class="xp-chip">Lvl 15 = <span>22,500 XP</span></div>
        <div class="xp-chip">Lvl 20 = <span>40,000 XP</span></div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <span class="section-title">🏆 Ranking Użytkowników</span>
      <span style="color:var(--muted);font-size:.75rem">Top 20</span>
    </div>
    <div class="section-body" style="padding:0">
      <table>
        <thead><tr><th>#</th><th>Użytkownik</th><th>Poziom</th><th>XP</th><th>Postęp</th><th>Wiad.</th><th>Voice (min)</th></tr></thead>
        <tbody>{''.join(rows) if rows else '<tr><td colspan="7" style="text-align:center;color:#888;padding:30px">Brak danych!</td></tr>'}</tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <div class="section-header"><span class="section-title">⚙️ Ustawienia XP</span></div>
    <div class="section-body">
      <form method="POST" action="/save_settings">
        <div class="form-grid">
          <div class="form-group"><label>XP za wiadomość</label><input type="number" name="xp_per_message" value="{config.get('xp_per_message', 15)}" min="1" max="1000"></div>
          <div class="form-group"><label>XP za minutę voice</label><input type="number" name="xp_per_voice_minute" value="{config.get('xp_per_voice_minute', 5)}" min="1" max="100"></div>
          <div class="form-group"><label>Cooldown (sekundy)</label><input type="number" name="xp_cooldown" value="{config.get('xp_cooldown', 60)}" min="0" max="3600"></div>
          <div class="form-group"><label>&nbsp;</label>
            <button type="submit" class="btn btn-primary">Zapisz</button>
          </div>
        </div>
      </form>
    </div>
  </div>
</div>
<script>
  function updateRoleName() {{
    const sel = document.getElementById('role-select');
    const hidden = document.getElementById('role-name-hidden');
    if (sel && hidden) {{
      const opt = sel.options[sel.selectedIndex];
      hidden.value = opt.getAttribute('data-name') || opt.text;
    }}
  }}
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def get_session_user(self):
        token = get_cookie_session(self.headers)
        if not token:
            return None
        sessions = load_sessions()
        return sessions.get(token)

    def redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def send_html(self, html, cookie=None):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(html.encode())

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/callback":
            params = parse_qs(parsed.query)
            code = params.get("code", [None])[0]
            if not code:
                self.send_html(login_page("Błąd logowania — brak kodu."))
                return
            try:
                token_data = exchange_code(code)
                access_token = token_data["access_token"]
                user = get_discord_user(access_token)

                # Sprawdź czy admin
                if not is_admin_on_guild(access_token):
                    self.send_html(not_admin_page(user.get("username", "?")))
                    return

                # Utwórz sesję
                session_token = secrets.token_hex(32)
                sessions = load_sessions()
                sessions[session_token] = {
                    "user": user,
                    "access_token": access_token
                }
                save_sessions(sessions)

                cookie = f"session={session_token}; Path=/; HttpOnly; Max-Age=86400"
                self.send_response(302)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie", cookie)
                self.end_headers()
            except Exception as e:
                print(f"OAuth error: {e}")
                self.send_html(login_page(f"Błąd logowania: {e}"))
            return

        if path == "/logout":
            token = get_cookie_session(self.headers)
            if token:
                sessions = load_sessions()
                sessions.pop(token, None)
                save_sessions(sessions)
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", "session=; Path=/; Max-Age=0")
            self.end_headers()
            return

        user_session = self.get_session_user()
        if not user_session:
            self.send_html(login_page())
            return

        db = load_db()
        config = load_config()
        html = get_dashboard_html(db, config, user_session["user"])
        self.send_html(html)

    def do_POST(self):
        user_session = self.get_session_user()
        if not user_session:
            self.redirect("/")
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        params = dict(urllib.parse.parse_qsl(body))
        path = urlparse(self.path).path
        message = ""

        if path == "/add_role":
            try:
                level = int(params["level"])
                role_name = params.get("role_name", "").strip()
                role_id = params.get("role_id", "").strip()

                # Pobierz nazwę z listy ról jeśli role_name puste
                if not role_name:
                    roles_data = fetch_discord_roles()
                    for r in roles_data:
                        if r["id"] == role_id:
                            role_name = r["name"]
                            break

                config = load_config()
                roles = [r for r in config.get("roles", []) if r["level"] != level]
                roles.append({"level": level, "role_id": role_id, "role_name": role_name})
                roles.sort(key=lambda x: x["level"])
                config["roles"] = roles
                save_config(config)
                message = f"✅ Rola '{role_name}' zostanie nadana na Poziomie {level} ({xp_for_level(level):,} XP)!"
            except Exception as e:
                message = f"❌ Błąd: {e}"

        elif path == "/remove_role":
            try:
                level = int(params["level"])
                config = load_config()
                config["roles"] = [r for r in config.get("roles", []) if r["level"] != level]
                save_config(config)
                message = f"✅ Usunięto rolę z poziomu {level}."
            except Exception as e:
                message = f"❌ Błąd: {e}"

        elif path == "/save_settings":
            try:
                config = load_config()
                config["xp_per_message"] = int(params.get("xp_per_message", 15))
                config["xp_per_voice_minute"] = int(params.get("xp_per_voice_minute", 5))
                config["xp_cooldown"] = int(params.get("xp_cooldown", 60))
                save_config(config)
                message = "✅ Ustawienia zapisane!"
            except Exception as e:
                message = f"❌ Błąd: {e}"

        db = load_db()
        config = load_config()
        html = get_dashboard_html(db, config, user_session["user"], message)
        self.send_html(html)

    def log_message(self, format, *args):
        pass


def run_bot():
    print("🤖 Uruchamianie bota Discord...")
    subprocess.run([sys.executable, "bot.py"])


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("✅ Bot uruchomiony w tle!")
    port = int(os.environ.get("PORT", 7860))
    print(f"🌐 Dashboard na http://0.0.0.0:{port}")
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()
