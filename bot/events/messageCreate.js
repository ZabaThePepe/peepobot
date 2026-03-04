const User = require('../../models/User');
const GuildSettings = require('../../models/GuildSettings');

module.exports = {
  name: 'messageCreate',
  async execute(message, client) {
    if (message.author.bot || !message.guild) return;
    if (message.guildId !== process.env.GUILD_ID) return;

    const settings = await GuildSettings.findOneAndUpdate(
      { guildId: message.guildId },
      {},
      { upsert: true, new: true, setDefaultsOnInsert: true }
    );

    const user = await User.findOneAndUpdate(
      { userId: message.author.id, guildId: message.guildId },
      {},
      { upsert: true, new: true, setDefaultsOnInsert: true }
    );

    const now = new Date();
    const cooldown = settings.messageCooldownSeconds * 1000;
    if (user.lastMessage && (now - user.lastMessage) < cooldown) return;

    user.lastMessage = now;
    user.xp += settings.xpPerMessage;
    const leveledUp = user.checkLevelUp();
    await user.save();

    if (leveledUp && settings.announcementChannelId) {
      const channel = message.guild.channels.cache.get(settings.announcementChannelId);
      if (channel) {
        channel.send(`🎉 ${message.author} osiągnął **Level ${user.level}**! Gratulacje!`);
      }

      // Nadaj rolę za level
      const reward = settings.levelRoles.find(r => r.level === user.level);
      if (reward) {
        const member = await message.guild.members.fetch(message.author.id).catch(() => null);
        if (member) {
          const role = message.guild.roles.cache.get(reward.roleId);
          if (role) member.roles.add(role).catch(console.error);
        }
      }
    }
  },
};
