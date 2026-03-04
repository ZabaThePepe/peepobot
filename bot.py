import discord
from discord.ext import commands, tasks
import json
import os
import time

# ========================
# KONFIGURACJA
# ========================
TOKEN = os.environ.get("DISCORD_TOKEN", "")
PREFIX = os.environ.get("BOT_PREFIX", "!")

XP_PER_MESSAGE = int(os.environ.get("XP_PER_MESSAGE", "15"))
XP_PER_VOICE_MINUTE = int(os.environ.get("XP_PER_VOICE_MINUTE", "5"))
XP_COOLDOWN = int(os.environ.get("XP_COOLDOWN", "60"))
LEVEL_UP_CHANNEL_ID = os.environ.get("LEVEL_UP_CHANNEL_ID", None)
if LEVEL_UP_CHANNEL_ID:
    LEVEL_UP_CHANNEL_ID = int(LEVEL_UP_CHANNEL_ID)

DB_FILE = "levels.json"
CONFIG_FILE = "config.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ========================
# DATABASE
# ========================

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "stats": {"total_messages": 0, "total_voice_minutes": 0}}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_config():
    default = {
        "roles": [],
        "level_up_channel": None,
        "xp_per_message": XP_PER_MESSAGE,
        "xp_per_voice_minute": XP_PER_VOICE_MINUTE,
        "xp_cooldown": XP_COOLDOWN
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
            default.update(cfg)
    return default

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def get_user(db, user_id):
    uid = str(user_id)
    if "users" not in db:
        db["users"] = {}
    if uid not in db["users"]:
        db["users"][uid] = {"xp": 0, "level": 0, "messages": 0, "voice_minutes": 0, "last_message": 0, "username": "Unknown"}
    return db["users"][uid]

def xp_to_level(xp):
    level = 0
    while (level + 1) ** 2 * 100 <= xp:
        level += 1
    return level

def xp_for_level(level):
    return level ** 2 * 100

def get_role_for_level(config, level):
    best_role = None
    best_level = -1
    for entry in config.get("roles", []):
        if entry["level"] <= level and entry["level"] > best_level:
            best_level = entry["level"]
            best_role = entry
    return best_role

voice_tracker = {}

@bot.event
async def on_ready():
    print(f"✅ Bot uruchomiony jako {bot.user}")
    voice_xp_task.start()
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, name=f"{PREFIX}poziom | XP System"
    ))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    db = load_db()
    config = load_config()
    user = get_user(db, message.author.id)
    user["username"] = str(message.author)
    now = time.time()
    cooldown = config.get("xp_cooldown", XP_COOLDOWN)
    xp_msg = config.get("xp_per_message", XP_PER_MESSAGE)

    if now - user["last_message"] >= cooldown:
        old_level = xp_to_level(user["xp"])
        user["xp"] += xp_msg
        user["messages"] += 1
        user["last_message"] = now
        if "stats" not in db:
            db["stats"] = {"total_messages": 0, "total_voice_minutes": 0}
        db["stats"]["total_messages"] = db["stats"].get("total_messages", 0) + 1
        new_level = xp_to_level(user["xp"])
        if new_level > old_level:
            user["level"] = new_level
            await handle_level_up(message.guild, message.author, user, new_level, config, message.channel)
        save_db(db)
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    uid = member.id
    if after.channel and not before.channel:
        voice_tracker[uid] = time.time()
    elif not after.channel and before.channel:
        if uid in voice_tracker:
            minutes = (time.time() - voice_tracker[uid]) / 60
            config = load_config()
            xp_voice = config.get("xp_per_voice_minute", XP_PER_VOICE_MINUTE)
            xp_earned = int(minutes * xp_voice)
            if xp_earned > 0:
                db = load_db()
                user = get_user(db, uid)
                old_level = xp_to_level(user["xp"])
                user["xp"] += xp_earned
                user["voice_minutes"] += int(minutes)
                if "stats" not in db:
                    db["stats"] = {"total_messages": 0, "total_voice_minutes": 0}
                db["stats"]["total_voice_minutes"] = db["stats"].get("total_voice_minutes", 0) + int(minutes)
                new_level = xp_to_level(user["xp"])
                if new_level > old_level:
                    user["level"] = new_level
                    guild = before.channel.guild
                    mem = guild.get_member(uid)
                    if mem:
                        await handle_level_up(guild, mem, user, new_level, config, None)
                save_db(db)
            del voice_tracker[uid]

@tasks.loop(minutes=5)
async def voice_xp_task():
    now = time.time()
    db = load_db()
    config = load_config()
    xp_voice = config.get("xp_per_voice_minute", XP_PER_VOICE_MINUTE)
    changed = False
    for uid, join_time in list(voice_tracker.items()):
        if (now - join_time) / 60 >= 5:
            user = get_user(db, uid)
            user["xp"] += 5 * xp_voice
            user["voice_minutes"] += 5
            voice_tracker[uid] = now
            changed = True
    if changed:
        save_db(db)

async def handle_level_up(guild, member, user_data, new_level, config, channel):
    role_entry = get_role_for_level(config, new_level)
    embed = discord.Embed(
        title="⬆️ LEVEL UP!",
        description=f"{member.mention} osiągnął **Poziom {new_level}**!",
        color=discord.Color.gold()
    )
    embed.add_field(name="✨ XP", value=f"`{user_data['xp']}`")
    embed.set_thumbnail(url=member.display_avatar.url)

    if role_entry:
        role = guild.get_role(int(role_entry["role_id"]))
        if role:
            for entry in config.get("roles", []):
                old_role = guild.get_role(int(entry["role_id"]))
                if old_role and old_role in member.roles and old_role != role:
                    try:
                        await member.remove_roles(old_role)
                    except:
                        pass
            try:
                await member.add_roles(role)
                embed.add_field(name="🏅 Nowa rola", value=f"`{role.name}`", inline=False)
            except discord.Forbidden:
                embed.add_field(name="⚠️", value="Brak uprawnień do nadania roli!", inline=False)

    target = None
    lvl_channel_id = config.get("level_up_channel") or LEVEL_UP_CHANNEL_ID
    if lvl_channel_id:
        target = guild.get_channel(int(lvl_channel_id))
    elif channel:
        target = channel
    if target:
        try:
            await target.send(embed=embed)
        except:
            pass

# ========================
# KOMENDY
# ========================

@bot.command(name="poziom", aliases=["level", "xp", "rank"])
async def poziom(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    db = load_db()
    user = get_user(db, member.id)
    level = xp_to_level(user["xp"])
    next_xp = xp_for_level(level + 1)
    prev_xp = xp_for_level(level)
    progress = user["xp"] - prev_xp
    total = next_xp - prev_xp
    pct = int((progress / total) * 20) if total > 0 else 20
    bar = "█" * pct + "░" * (20 - pct)
    config = load_config()
    role_entry = get_role_for_level(config, level)
    role_text = f"`{role_entry['role_name']}`" if role_entry else "Brak"
    embed = discord.Embed(title=f"📊 {member.display_name}", color=discord.Color.blue())
    embed.add_field(name="🎯 Poziom", value=f"`{level}`", inline=True)
    embed.add_field(name="✨ XP", value=f"`{user['xp']}`", inline=True)
    embed.add_field(name="🏅 Rola", value=role_text, inline=True)
    embed.add_field(name="💬 Wiadomości", value=f"`{user['messages']}`", inline=True)
    embed.add_field(name="🎙️ Voice (min)", value=f"`{user['voice_minutes']}`", inline=True)
    embed.add_field(name=f"📈 Do lvl {level+1}", value=f"`[{bar}]` {user['xp']}/{next_xp} XP", inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="ranking", aliases=["top"])
async def ranking(ctx):
    db = load_db()
    users = db.get("users", {})
    sorted_users = sorted(users.items(), key=lambda x: x[1].get("xp", 0), reverse=True)[:10]
    embed = discord.Embed(title="🏆 Ranking Serwera", color=discord.Color.gold())
    medals = ["🥇", "🥈", "🥉"]
    desc = ""
    for i, (uid, data) in enumerate(sorted_users):
        m = ctx.guild.get_member(int(uid))
        name = m.display_name if m else data.get("username", f"#{uid}")
        medal = medals[i] if i < 3 else f"`#{i+1}`"
        lvl = xp_to_level(data.get("xp", 0))
        desc += f"{medal} **{name}** — `{data.get('xp', 0)} XP` | Lvl {lvl}\n"
    embed.description = desc or "Brak danych!"
    await ctx.send(embed=embed)

@bot.command(name="setrole")
@commands.has_permissions(administrator=True)
async def setrole(ctx, level: int, role: discord.Role):
    """Ustaw rolę za poziom. Użycie: !setrole 5 @Rola"""
    config = load_config()
    roles = [r for r in config.get("roles", []) if r["level"] != level]
    roles.append({"level": level, "role_id": str(role.id), "role_name": role.name})
    roles.sort(key=lambda x: x["level"])
    config["roles"] = roles
    save_config(config)
    await ctx.send(f"✅ Rola `{role.name}` zostanie nadana automatycznie na **Poziomie {level}**!\n💡 XP potrzebne: `{xp_for_level(level)} XP`")

@bot.command(name="removerole")
@commands.has_permissions(administrator=True)
async def removerole_cmd(ctx, level: int):
    """Usuń rolę z poziomu: !removerole 5"""
    config = load_config()
    config["roles"] = [r for r in config.get("roles", []) if r["level"] != level]
    save_config(config)
    await ctx.send(f"✅ Usunięto rolę z poziomu **{level}**.")

@bot.command(name="rangi", aliases=["roles"])
async def rangi_cmd(ctx):
    config = load_config()
    roles = config.get("roles", [])
    embed = discord.Embed(title="🏅 Role za poziomy", color=discord.Color.purple())
    if roles:
        desc = ""
        for r in sorted(roles, key=lambda x: x["level"]):
            xp_needed = xp_for_level(r["level"])
            desc += f"**Poziom {r['level']}** (`{xp_needed} XP`) → `{r['role_name']}`\n"
        embed.description = desc
    else:
        embed.description = f"Brak skonfigurowanych ról!\nAdmin może użyć: `{PREFIX}setrole <poziom> @rola`"
    embed.set_footer(text="XP do poziomu N = N² × 100 | Lvl 5=2500 XP | Lvl 10=10000 XP")
    await ctx.send(embed=embed)

@bot.command(name="addxp")
@commands.has_permissions(administrator=True)
async def addxp(ctx, member: discord.Member, amount: int):
    db = load_db()
    config = load_config()
    user = get_user(db, member.id)
    old_level = xp_to_level(user["xp"])
    user["xp"] += amount
    new_level = xp_to_level(user["xp"])
    if new_level > old_level:
        user["level"] = new_level
        await handle_level_up(ctx.guild, member, user, new_level, config, ctx.channel)
    save_db(db)
    await ctx.send(f"✅ Dodano `{amount} XP` dla {member.mention}! Teraz: `{user['xp']} XP` (Lvl {new_level})")

@bot.command(name="resetxp")
@commands.has_permissions(administrator=True)
async def resetxp(ctx, member: discord.Member):
    db = load_db()
    db["users"][str(member.id)] = {"xp": 0, "level": 0, "messages": 0, "voice_minutes": 0, "last_message": 0, "username": str(member)}
    save_db(db)
    await ctx.send(f"✅ Zresetowano XP dla {member.mention}.")

@bot.command(name="pomoc")
async def pomoc(ctx):
    embed = discord.Embed(title="📚 Komendy", color=discord.Color.blue())
    embed.add_field(name=f"`{PREFIX}poziom [@user]`", value="Twój poziom i XP", inline=False)
    embed.add_field(name=f"`{PREFIX}ranking`", value="Top 10 serwera", inline=False)
    embed.add_field(name=f"`{PREFIX}rangi`", value="Role za poziomy", inline=False)
    embed.add_field(name=f"`{PREFIX}setrole <lvl> @rola`", value="[Admin] Rola za poziom", inline=False)
    embed.add_field(name=f"`{PREFIX}removerole <lvl>`", value="[Admin] Usuń rolę z poziomu", inline=False)
    embed.add_field(name=f"`{PREFIX}addxp @user <ilość>`", value="[Admin] Dodaj XP", inline=False)
    embed.add_field(name=f"`{PREFIX}resetxp @user`", value="[Admin] Resetuj XP", inline=False)
    await ctx.send(embed=embed)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Brak DISCORD_TOKEN!")
    else:
        bot.run(TOKEN)
