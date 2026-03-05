const { EmbedBuilder } = require('discord.js');
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

    const multiplier = getMultiplier(settings, message.member);
    user.xp += Math.floor(settings.xpPerMessage * multiplier);

    const leveledUp = user.checkLevelUp();
    await user.save();

    if (leveledUp) {
      const reward = settings.levelRoles.find(r => r.level === user.level);
      const member = await message.guild.members.fetch(message.author.id).catch(() => null);

      // Nadaj role
      if (reward && member) {
        const role = message.guild.roles.cache.get(reward.roleId);
        if (role) member.roles.add(role).catch(console.error);
      }

      // Embed powiadomienie
      if (settings.announcementChannelId) {
        const channel = message.guild.channels.cache.get(settings.announcementChannelId);
        if (channel) {
          let color = '#5865F2';
          if (user.level >= 10) color = '#9B59B6';
          if (user.level >= 25) color = '#E67E22';
          if (user.level >= 50) color = '#FFD700';

          const xpNeeded = user.xpForNextLevel();
          const embed = new EmbedBuilder()
            .setColor(color)
            .setAuthor({
              name: message.author.username,
              iconURL: message.author.displayAvatarURL({ dynamic: true }),
            })
            .setTitle('⬆️ Level Up!')
            .setDescription(`Gratulacje, ${message.author}!\nOsiągnąłeś **Level ${user.level}**! 🎉`)
            .addFields(
              { name: '🎯 Nowy poziom', value: `\`\`\`${user.level}\`\`\``, inline: true },
              { name: '⚡ XP do następnego', value: `\`\`\`${xpNeeded}\`\`\``, inline: true },
              ...(reward ? [{ name: '🏅 Nowa rola', value: `<@&${reward.roleId}>`, inline: true }] : []),
            )
            .setFooter({ text: `${message.guild.name} • System poziomów` })
            .setTimestamp();

          channel.send({ embeds: [embed] });
        }
      }
    }
  },
};

function getMultiplier(settings, member) {
  let multiplier = 1;

  const ev = settings.globalEvent;
  if (ev && ev.active) {
    const expired = ev.endsAt && new Date() > new Date(ev.endsAt);
    if (!expired) multiplier *= ev.multiplier;
  }

  if (member && settings.xpBoosters?.length) {
    for (const booster of settings.xpBoosters) {
      if (member.roles.cache.has(booster.roleId)) {
        multiplier *= booster.multiplier;
        break;
      }
    }
  }

  return multiplier;
}
