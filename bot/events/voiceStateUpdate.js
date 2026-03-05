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

    // Dołączył do kanału
    if (!oldState.channelId && newState.channelId) {
      startVCTracking(userId, guildId, newState);
    }

    // Opuścił kanał
    if (oldState.channelId && !newState.channelId) {
      stopVCTracking(userId);
    }

    // Zmienił kanał
    if (oldState.channelId && newState.channelId && oldState.channelId !== newState.channelId) {
      stopVCTracking(userId);
      startVCTracking(userId, guildId, newState);
    }
  },
};

function startVCTracking(userId, guildId, state) {
  const timer = setInterval(async () => {
    try {
      const guild = state.guild;
      const channel = guild.channels.cache.get(state.channelId);
      if (!channel) return stopVCTracking(userId);

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

      user.xp += Math.floor(settings.xpPerMinuteVC * multiplier);
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
      console.error('VC tracking error:', err);
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

  // Globalny event
  const ev = settings.globalEvent;
  if (ev && ev.active) {
    const expired = ev.endsAt && new Date() > new Date(ev.endsAt);
    if (!expired) multiplier *= ev.multiplier;
  }

  // Boostery rólowe
  if (member && settings.xpBoosters?.length) {
    for (const booster of settings.xpBoosters) {
      if (member.roles.cache.has(booster.roleId)) {
        multiplier *= booster.multiplier;
        break; // tylko jeden booster — usuń break jeśli chcesz stackować wszystkie
      }
    }
  }

  return multiplier;
}
