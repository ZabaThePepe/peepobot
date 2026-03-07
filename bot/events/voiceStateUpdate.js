const { EmbedBuilder } = require('discord.js');
const User = require('../../models/User');
const GuildSettings = require('../../models/GuildSettings');

const vcTimers = new Map();

module.exports = {
  name: 'voiceStateUpdate',
  async execute(oldState, newState, client) {
    const guild = newState.guild || oldState.guild;
    if (guild?.id !== process.env.GUILD_ID) return;

    const userId = newState.member?.id || oldState.member?.id;
    if (!userId) return;

    const guildId = guild.id;

    if (!oldState.channelId && newState.channelId) {
      startVCTracking(userId, guildId, newState);
    }
    if (oldState.channelId && !newState.channelId) {
      stopVCTracking(userId);
    }
    if (oldState.channelId && newState.channelId && oldState.channelId !== newState.channelId) {
      stopVCTracking(userId);
      startVCTracking(userId, guildId, newState);
    }
  },
};

function startVCTracking(userId, guildId, state) {
  const member = state.guild.members.cache.get(userId);
  if (member?.user.bot) return; // boty nie dostają timera

  const timer = setInterval(async () => {
    try {
      const guild = state.guild;
      const channel = guild.channels.cache.get(state.channelId);
      if (!channel) return stopVCTracking(userId);

      if (guild.afkChannelId && state.channelId === guild.afkChannelId) return;

      const humanMembers = channel.members.filter(m => !m.user.bot);
      if (humanMembers.size < 2) return;

      const settings = await GuildSettings.findOneAndUpdate(
        { guildId },
        {},
        { upsert: true, new: true, setDefaultsOnInsert: true }
      );

      const member = await guild.members.fetch(userId).catch(() => null);
      const multiplier = getMultiplier(settings, member);

      const user = await User.findOneAndUpdate(
        { userId, guildId },
        {},
        { upsert: true, new: true, setDefaultsOnInsert: true }
      );

      const xpGained = Math.floor(settings.xpPerMinuteVC * multiplier);
      user.xp += xpGained;
      const leveledUp = user.checkLevelUp();
      await user.save();

      if (leveledUp) {
        const reward = settings.levelRoles.find(r => r.level === user.level);
        if (reward && member) {
          const role = guild.roles.cache.get(reward.roleId);
          if (role) member.roles.add(role).catch(console.error);
        }

        if (settings.announcementChannelId) {
          const announceCh = guild.channels.cache.get(settings.announcementChannelId);
          if (announceCh && member) {
            let color = '#5865F2';
            if (user.level >= 10) color = '#9B59B6';
            if (user.level >= 25) color = '#E67E22';
            if (user.level >= 50) color = '#FFD700';

            const xpNeeded = user.xpForNextLevel();
            const embed = new EmbedBuilder()
              .setColor(color)
              .setAuthor({
                name: member.displayName || member.user.username,
                iconURL: member.user.displayAvatarURL({ dynamic: true }),
              })
              .setTitle('⬆️ Level Up!')
              .setDescription(`Gratulacje, <@${userId}>!\nOsiągnąłeś **Level ${user.level}**! 🎉`)
              .addFields(
                { name: '🎯 Nowy poziom', value: `\`\`\`${user.level}\`\`\``, inline: true },
                { name: '⚡ XP do następnego', value: `\`\`\`${xpNeeded}\`\`\``, inline: true },
                { name: '🎙️ Źródło', value: `\`\`\`Rozmowa głosowa\`\`\``, inline: true },
                ...(reward ? [{ name: '🏅 Nowa rola', value: `<@&${reward.roleId}>`, inline: true }] : []),
              )
              .setFooter({ text: `${guild.name} • System poziomów` })
              .setTimestamp();

            announceCh.send({ embeds: [embed] });
          }
        }
      }
    } catch (err) {
      console.error('[VC] Blad timera:', err);
    }
  }, 60_000);

  vcTimers.set(userId, timer);
}

function stopVCTracking(userId) {
  if (vcTimers.has(userId)) {
    clearInterval(vcTimers.get(userId));
    vcTimers.delete(userId);
  }
}

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
