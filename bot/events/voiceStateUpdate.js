const User = require('../../models/User');
const GuildSettings = require('../../models/GuildSettings');

const vcTimers = new Map();

module.exports = {
  name: 'voiceStateUpdate',
  async execute(oldState, newState, client) {
    const guild = newState.guild || oldState.guild;
    if (guild?.id !== process.env.GUILD_ID) return;

    const userId = newState.member?.id || oldState.member?.id;
    console.log(`[VC] userId=${userId} old=${oldState.channelId} new=${newState.channelId}`);
    if (!userId) return;

    const guildId = guild.id;

    if (!oldState.channelId && newState.channelId) {
      console.log(`[VC] ${userId} dołączył do kanału ${newState.channelId}`);
      startVCTracking(userId, guildId, newState);
    }

    if (oldState.channelId && !newState.channelId) {
      console.log(`[VC] ${userId} opuścił kanał`);
      stopVCTracking(userId);
    }

    if (oldState.channelId && newState.channelId && oldState.channelId !== newState.channelId) {
      console.log(`[VC] ${userId} zmienił kanał`);
      stopVCTracking(userId);
      startVCTracking(userId, guildId, newState);
    }
  },
};

function startVCTracking(userId, guildId, state) {
  console.log(`[VC] Startuje timer dla ${userId}`);
  const timer = setInterval(async () => {
    try {
      console.log(`[VC] Timer tick dla ${userId}`);
      const guild = state.guild;
      const channel = guild.channels.cache.get(state.channelId);
      if (!channel) {
        console.log(`[VC] Kanal nie znaleziony, zatrzymuje timer`);
        return stopVCTracking(userId);
      }

      const humanMembers = channel.members.filter(m => !m.user.bot);
      console.log(`[VC] Ludzi na kanale: ${humanMembers.size}`);
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
      console.log(`[VC] Dodaje ${xpGained} XP dla ${userId} (mnoznik: ${multiplier})`);
      user.xp += xpGained;
      const leveledUp = user.checkLevelUp();
      await user.save();

      if (leveledUp) {
        if (settings.announcementChannelId) {
          const announceCh = guild.channels.cache.get(settings.announcementChannelId);
          if (announceCh) {
            announceCh.send(`🎉 <@${userId}> osiągnął **Level ${user.level}** podczas rozmowy głosowej!`);
          }
        }
        const reward = settings.levelRoles.find(r => r.level === user.level);
        if (reward && member) {
          const role = guild.roles.cache.get(reward.roleId);
          if (role) member.roles.add(role).catch(console.error);
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
    console.log(`[VC] Timer zatrzymany dla ${userId}`);
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
