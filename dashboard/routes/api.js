const express = require('express');
const router = express.Router();
const requireAuth = require('../middleware/auth');
const GuildSettings = require('../../models/GuildSettings');
const User = require('../../models/User');

router.use(requireAuth);

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
    { announcementChannelId: announcementChannelId || null, xpPerMessage: parseInt(xpPerMessage), xpPerMinuteVC: parseInt(xpPerMinuteVC) },
    { upsert: true, new: true }
  );
  res.json({ success: true, settings });
});

router.post('/levelroles', async (req, res) => {
  const { level, roleId, roleName } = req.body;
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

router.get('/leaderboard', async (req, res) => {
  const users = await User.find({ guildId: process.env.GUILD_ID })
    .sort({ level: -1, xp: -1 })
    .limit(10);
  res.json(users);
});

module.exports = router;
