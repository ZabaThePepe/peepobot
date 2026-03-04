const express = require('express');
const router = express.Router();
const axios = require('axios');
const requireAuth = require('../middleware/auth');
const GuildSettings = require('../../models/GuildSettings');
const User = require('../../models/User');

router.use(requireAuth);

// Pobierz role serwera z Discord API
async function getGuildRoles() {
  try {
    const res = await axios.get(`https://discord.com/api/v10/guilds/${process.env.GUILD_ID}/roles`, {
      headers: { Authorization: `Bot ${process.env.DISCORD_TOKEN}` },
    });
    return res.data.filter(r => r.name !== '@everyone').sort((a, b) => b.position - a.position);
  } catch (err) {
    console.error('Błąd pobierania ról:', err.message);
    return [];
  }
}

// Pobierz członków serwera (do leaderboard)
async function getMemberName(userId) {
  try {
    const res = await axios.get(`https://discord.com/api/v10/guilds/${process.env.GUILD_ID}/members/${userId}`, {
      headers: { Authorization: `Bot ${process.env.DISCORD_TOKEN}` },
    });
    return res.data.nick || res.data.user.username;
  } catch {
    return null;
  }
}

router.get('/settings', async (req, res) => {
  const settings = await GuildSettings.findOneAndUpdate(
    { guildId: process.env.GUILD_ID },
    {},
    { upsert: true, new: true, setDefaultsOnInsert: true }
  );
  res.json(settings);
});

router.post('/settings', async (req, res) => {
  const { announcementChannelId, xpPerMessage, xpPerMinuteVC } = req.body;
  const settings = await GuildSettings.findOneAndUpdate(
    { guildId: process.env.GUILD_ID },
    {
      announcementChannelId: announcementChannelId || null,
      xpPerMessage: parseInt(xpPerMessage),
      xpPerMinuteVC: parseInt(xpPerMinuteVC),
    },
    { upsert: true, new: true }
  );
  res.json({ success: true, settings });
});

// Pobierz role serwera dla dropdownów
router.get('/roles', async (req, res) => {
  const roles = await getGuildRoles();
  res.json(roles);
});

// Level roles
router.post('/levelroles', async (req, res) => {
  const { level, roleId } = req.body;
  const roles = await getGuildRoles();
  const role = roles.find(r => r.id === roleId);
  const roleName = role ? role.name : roleId;

  const settings = await GuildSettings.findOneAndUpdate(
    { guildId: process.env.GUILD_ID },
    { $push: { levelRoles: { level: parseInt(level), roleId, roleName } } },
    { upsert: true, new: true }
  );
  res.json({ success: true, levelRoles: settings.levelRoles });
});

router.delete('/levelroles/:roleId', async (req, res) => {
  const settings = await GuildSettings.findOneAndUpdate(
    { guildId: process.env.GUILD_ID },
    { $pull: { levelRoles: { roleId: req.params.roleId } } },
    { new: true }
  );
  res.json({ success: true, levelRoles: settings.levelRoles });
});

// XP Boostery
router.post('/boosters', async (req, res) => {
  const { roleId, multiplier } = req.body;
  const roles = await getGuildRoles();
  const role = roles.find(r => r.id === roleId);
  const roleName = role ? role.name : roleId;

  const settings = await GuildSettings.findOneAndUpdate(
    { guildId: process.env.GUILD_ID },
    { $push: { xpBoosters: { roleId, roleName, multiplier: parseFloat(multiplier) } } },
    { upsert: true, new: true }
  );
  res.json({ success: true, xpBoosters: settings.xpBoosters });
});

router.delete('/boosters/:roleId', async (req, res) => {
  const settings = await GuildSettings.findOneAndUpdate(
    { guildId: process.env.GUILD_ID },
    { $pull: { xpBoosters: { roleId: req.params.roleId } } },
    { new: true }
  );
  res.json({ success: true, xpBoosters: settings.xpBoosters });
});

// Globalny event booster
router.get('/event', async (req, res) => {
  const settings = await GuildSettings.findOneAndUpdate(
    { guildId: process.env.GUILD_ID },
    {},
    { upsert: true, new: true, setDefaultsOnInsert: true }
  );
  const ev = settings.globalEvent || {};
  // Jeśli timer wygasł — automatycznie wyłącz
  if (ev.active && ev.endsAt && new Date() > ev.endsAt) {
    settings.globalEvent.active = false;
    await settings.save();
  }
  res.json(settings.globalEvent);
});

router.post('/event', async (req, res) => {
  const { active, multiplier, name, durationHours } = req.body;
  const update = {
    'globalEvent.active': active,
    'globalEvent.multiplier': parseFloat(multiplier) || 2,
    'globalEvent.name': name || 'Event XP',
    'globalEvent.startedAt': active ? new Date() : null,
    'globalEvent.endsAt': active && durationHours
      ? new Date(Date.now() + parseFloat(durationHours) * 60 * 60 * 1000)
      : null,
  };
  const settings = await GuildSettings.findOneAndUpdate(
    { guildId: process.env.GUILD_ID },
    { $set: update },
    { upsert: true, new: true }
  );
  res.json({ success: true, globalEvent: settings.globalEvent });
});

// Leaderboard z nazwami
router.get('/leaderboard', async (req, res) => {
  const users = await User.find({ guildId: process.env.GUILD_ID })
    .sort({ level: -1, xp: -1 })
    .limit(10);

  const result = await Promise.all(users.map(async (u) => {
    const name = await getMemberName(u.userId);
    return {
      userId: u.userId,
      displayName: name || `Użytkownik`,
      level: u.level,
      xp: u.xp,
    };
  }));

  res.json(result);
});

module.exports = router;
