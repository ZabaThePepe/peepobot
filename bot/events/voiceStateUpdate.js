const User = require('../../models/User');
const GuildSettings = require('../../models/GuildSettings');

const vcTimers = new Map();

module.exports = {
  name: 'voiceStateUpdate',
  async execute(oldState, newState, client) {
    if (newState.guild?.id !== process.env.GUILD_ID) return;

    const userId = newState.id || oldState.id;
    const guildId = (newState.guild || oldState.guild).id;

    // Dołączył do kanału
    if (!oldState.channelId && newState.channelId) {
      startVCTracking(userId, guildId, newState, client);
    }

    // Opuścił kanał
    if (oldState.channelId && !newState.channelId) {
      stopVCTracking(userId);
    }

    // Zmienił kanał
    if (oldState.channelId && newState.channelId && oldState.channelId !== newState.channelId) {
      stopVCTracking(userId);
      startVCTracking(userId, guildId, newState, client);
    }
  },
};

function startVCTracking(userId, guildId, state, client) {
  const timer = setInterval(async () => {
    const channel = state.guild.channels.cache.get(state.channelId);
    if (!channel) return stopVCTracking(userId);

    const humanMembers = channel.members.filter(m => !m.user.bot);
    if (humanMembers.size < 2) return;

    const settings = await GuildSettings.findOneAndUpdate(
      { guildId },
      {},
      { upsert: true, new: true, setDefaultsOnInsert: true }
    );

    const user = await User.findOneAndUpdate(
      { userId, guildId },
      {},
      { upsert: true, new: true, setDefaultsOnInsert: true }
    );

    user.xp += settings.xpPerMinuteVC;
    const leveledUp = user.checkLevelUp();
    await user.save();

    if (leveledUp && settings.announcementChannelId) {
      const announceCh = state.guild.channels.cache.get(settings.announcementChannelId);
      if (announceCh) {
        announceCh.send(`🎉 <@${userId}> osiągnął **Level ${user.level}** podczas rozmowy głosowej!`);
      }

      const reward = settings.levelRoles.find(r => r.level === user.level);
      if (reward) {
        const member = await state.guild.members.fetch(userId).catch(() => null);
        if (member) {
          const role = state.guild.roles.cache.get(reward.roleId);
          if (role) member.roles.add(role).catch(console.error);
        }
      }
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
