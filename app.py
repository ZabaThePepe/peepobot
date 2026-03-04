"""
app.py — Discord Bot + Dashboard webowy z listą ról
"""

import threading
import subprocess
import sys
import json
import os
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

DB_FILE = "levels.json"
CONFIG_FILE = "config.json"
ADMIN_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "admin123")
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
GUILD_ID = "1478527413146091651"


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


def xp_to_level(xp):
    level = 0
    while (level + 1) ** 2 * 100 <= xp:
        level += 1
    return level


def xp_for_level(level):
    return level ** 2 * 100


def fetch_discord_roles():
    """Pobiera listę ról z serwera Discord przez API"""
    try:
        print(f"DEBUG: Token zaczyna się od: {DISCORD_TOKEN[:20] if DISCORD_TOKEN else 'BRAK TOKENU'}")
        print(f"DEBUG: Guild ID: {GUILD_ID}")
        url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/roles"
        req = urllib.request.Request(url, headers={"Authorization": f"Bot {DISCORD_TOKEN}"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            roles = json.loads(resp.read().decode())
            roles = [r for r in roles if r["name"] != "@everyone" and not r.get("managed", False)]
            roles.sort(key=lambda r: r["position"], reverse=True)
            print(f"DEBUG: Pobrano {len(roles)} ról!")
            return roles
    except Exception as e:
        print(f"Błąd pobierania ról: {e}")
        return []


def get_dashboard_html(db, config, message=""):
    users = db.get("users", {})
    stats = db.get("stats", {})
    sorted_users = sorted(users.items(), key=lambda x: x[1].get("xp", 0), reverse=True)

    # Pobierz role z Discorda
    discord_roles = fetch_discord_roles()

    # Leaderboard
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

    # Tabela skonfigurowanych ról
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
                    <input type="hidden" name="password" id="del-pass-{r['level']}" value="">
                    <input type="hidden" name="level" value="{r['level']}">
                    <button type="submit" class="btn btn-danger"
                        onclick="document.getElementById('del-pass-{r['level']}').value=document.getElementById('admin-pass').value">Usuń</button>
                </form>
            </td>
        </tr>"""

    if not roles_rows:
        roles_rows = '<tr><td colspan="4" style="text-align:center;color:#888;padding:20px">Brak ról. Dodaj pierwszą poniżej!</td></tr>'

    # Opcje select dla ról Discord
    role_options = '<option value="">-- Wybierz rolę --</option>'
    if discord_roles:
        for r in discord_roles:
            role_options += f'<option value="{r["id"]}" data-name="{r["name"]}">{r["name"]}</option>'
        role_select = f"""
        <div class="form-group">
            <label>Rola Discord</label>
            <select name="role_id" id="role-select" required onchange="updateRoleName(this)">
                {role_options}
            </select>
        </div>
        <input type="hidden" name="role_name" id="role-name-hidden">
        """
    else:
        role_select = """
        <div class="form-group">
            <label>Rola Discord (nie udało się pobrać — wpisz ID ręcznie)</label>
            <input type="text" name="role_id" placeholder="np. 123456789012345678" required>
        </div>
        <div class="form-group">
            <label>Nazwa roli</label>
            <input type="text" name="role_name" placeholder="np. Weteran" required>
        </div>
        """

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
  header{{padding:32px 0 24px;border-bottom:1px solid var(--border);margin-bottom:32px;display:flex;align-items:center;gap:16px}}
  .logo{{font-size:2.4rem}}
  header h1{{font-family:'Syne',sans-serif;font-weight:800;font-size:1.8rem;letter-spacing:-.5px}}
  header p{{color:var(--muted);font-size:.8rem;margin-top:4px}}
  .status-dot{{width:10px;height:10px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green);animation:pulse 2s infinite;display:inline-block;margin-left:8px}}
  @keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.7;transform:scale(.85)}}}}
  .stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:32px}}
  .stat-card{{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:20px;position:relative;overflow:hidden;transition:transform .2s,border-color .2s}}
  .stat-card:hover{{transform:translateY(-2px);border-color:var(--accent)}}
  .stat-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--accent),var(--accent2))}}
  .stat-icon{{font-size:1.8rem;margin-bottom:8px}}
  .stat-val{{font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:var(--accent)}}
  .stat-label{{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:1px;margin-top:4px}}
  .section{{background:var(--surface);border:1px solid var(--border);border-radius:20px;margin-bottom:24px;overflow:hidden}}
  .section-header{{padding:20px 24px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--surface2)}}
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
  .level-badge{{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;padding:3px 10px;border-radius:20px;font-size:.75rem;font-weight:700;white-space:nowrap}}
  .role-tag{{background:rgba(88,101,242,.2);border:1px solid rgba(88,101,242,.4);color:var(--accent2);padding:3px 10px;border-radius:20px;font-size:.75rem}}
  .progress-wrap{{background:var(--border);border-radius:4px;height:6px;margin-bottom:3px;overflow:hidden}}
  .progress-bar{{height:100%;border-radius:4px}}
  .form-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;align-items:end}}
  .form-group{{display:flex;flex-direction:column;gap:6px}}
  label{{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:1px}}
  input[type="text"],input[type="number"],input[type="password"],select{{
    background:var(--bg);border:1px solid var(--border);
    color:var(--text);padding:10px 14px;border-radius:10px;
    font-family:'Space Mono',monospace;font-size:.85rem;transition:border-color .2s;
    width:100%;
  }}
  select option{{background:var(--surface2);color:var(--text)}}
  input:focus,select:focus{{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(88,101,242,.15)}}
  .btn{{padding:10px 20px;border-radius:10px;border:none;cursor:pointer;font-family:'Space Mono',monospace;font-size:.82rem;font-weight:700;transition:all .2s;text-transform:uppercase;letter-spacing:.5px}}
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
  .pass-bar{{position:sticky;top:0;z-index:100;background:rgba(13,14,26,.95);backdrop-filter:blur(10px);border-bottom:1px solid var(--border);padding:10px 0;margin-bottom:24px}}
  .pass-inner{{max-width:1200px;margin:0 auto;padding:0 20px;display:flex;align-items:center;gap:12px}}
  .pass-label{{color:var(--muted);font-size:.75rem;white-space:nowrap}}
  @media(max-width:768px){{.form-grid{{grid-template-columns:1fr}}table{{font-size:.75rem}}th:nth-child(n+5),td:nth-child(n+5){{display:none}}}}
</style>
</head>
<body>

<div class="pass-bar">
  <div class="pass-inner">
    <span class="pass-label">🔑 Hasło admina:</span>
    <input type="password" id="admin-pass" placeholder="Wpisz hasło..." style="width:200px;margin:0">
    <span style="font-size:.72rem;color:var(--muted)">Wymagane do zmian</span>
  </div>
</div>

<div class="container">
  <header>
    <div class="logo">🤖</div>
    <div>
      <h1>Discord Level Bot <span class="status-dot"></span></h1>
      <p>Dashboard administracyjny · {total_users} użytkowników</p>
    </div>
  </header>

  {msg_html}

  <div class="stats-grid">
    <div class="stat-card"><div class="stat-icon">👥</div><div class="stat-val">{total_users}</div><div class="stat-label">Użytkownicy</div></div>
    <div class="stat-card"><div class="stat-icon">💬</div><div class="stat-val">{total_msgs:,}</div><div class="stat-label">Wiadomości</div></div>
    <div class="stat-card"><div class="stat-icon">🎙️</div><div class="stat-val">{total_voice}</div><div class="stat-label">Minut voice</div></div>
    <div class="stat-card"><div class="stat-icon">🏅</div><div class="stat-val">{len(roles)}</div><div class="stat-label">Skonfig. rang</div></div>
  </div>

  <!-- Role za poziomy -->
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
            <label>Hasło admina</label>
            <input type="password" name="password" id="add-pass" placeholder="••••••••" required>
          </div>
          <div class="form-group">
            <label>&nbsp;</label>
            <button type="submit" class="btn btn-primary"
              onclick="syncPassword(); updateRoleNameBeforeSubmit()">Dodaj Rolę</button>
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

  <!-- Ranking -->
  <div class="section">
    <div class="section-header">
      <span class="section-title">🏆 Ranking Użytkowników</span>
      <span style="color:var(--muted);font-size:.75rem">Top 20</span>
    </div>
    <div class="section-body" style="padding:0">
      <table>
        <thead><tr><th>#</th><th>Użytkownik</th><th>Poziom</th><th>XP</th><th>Postęp</th><th>Wiad.</th><th>Voice (min)</th></tr></thead>
        <tbody>{''.join(rows) if rows else '<tr><td colspan="7" style="text-align:center;color:#888;padding:30px">Brak danych — napisz coś na serwerze!</td></tr>'}</tbody>
      </table>
    </div>
  </div>

  <!-- Ustawienia -->
  <div class="section">
    <div class="section-header"><span class="section-title">⚙️ Ustawienia XP</span></div>
    <div class="section-body">
      <form method="POST" action="/save_settings">
        <div class="form-grid">
          <div class="form-group"><label>XP za wiadomość</label><input type="number" name="xp_per_message" value="{config.get('xp_per_message', 15)}" min="1" max="1000"></div>
          <div class="form-group"><label>XP za minutę voice</label><input type="number" name="xp_per_voice_minute" value="{config.get('xp_per_voice_minute', 5)}" min="1" max="100"></div>
          <div class="form-group"><label>Cooldown (sekundy)</label><input type="number" name="xp_cooldown" value="{config.get('xp_cooldown', 60)}" min="0" max="3600"></div>
          <div class="form-group"><label>Hasło admina</label><input type="password" name="password" id="cfg-pass" placeholder="••••••••" required></div>
          <div class="form-group"><label>&nbsp;</label>
            <button type="submit" class="btn btn-primary" onclick="document.getElementById('cfg-pass').value=document.getElementById('admin-pass').value">Zapisz</button>
          </div>
        </div>
      </form>
    </div>
  </div>
</div>

<script>
  function syncPassword() {{
    const p = document.getElementById('admin-pass').value;
    document.getElementById('add-pass').value = p;
  }}

  function updateRoleNameBeforeSubmit() {{
    const sel = document.getElementById('role-select');
    const hidden = document.getElementById('role-name-hidden');
    if (sel && hidden) {{
      const opt = sel.options[sel.selectedIndex];
      hidden.value = opt.getAttribute('data-name') || opt.text;
    }}
  }}

  document.querySelectorAll('form').forEach(form => {{
    form.addEventListener('submit', () => {{
      const p = document.getElementById('admin-pass').value;
      form.querySelectorAll('input[type="password"]').forEach(inp => {{ if (!inp.value) inp.value = p; }});
      updateRoleNameBeforeSubmit();
    }});
  }});
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        db = load_db()
        config = load_config()
        html = get_dashboard_html(db, config)
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        params = dict(urllib.parse.parse_qsl(body))
        path = urlparse(self.path).path
        message = ""

        if params.get("password") != ADMIN_PASSWORD:
            message = "❌ Błędne hasło admina!"
        elif path == "/add_role":
            try:
                level = int(params["level"])
                role_name = params.get("role_name", "").strip()
                role_id = params.get("role_id", "").strip()
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
        html = get_dashboard_html(db, config, message)
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

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
