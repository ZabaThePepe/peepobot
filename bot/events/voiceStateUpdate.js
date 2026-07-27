const { EmbedBuilder } = require('discord.js');
const { useMainPlayer } = require('discord-player');

module.exports = {
  name: 'voiceStateUpdate',
  async execute(oldState, newState) {
    const player = useMainPlayer();

    // Bot opuścił kanał - zatrzymaj muzykę
    if (oldState.channelId && !newState.channelId && newState.member.id === newState.client.user.id) {
      const queue = player.queues.get(newState.guild.id);
      if (queue) {
        queue.delete();
      }
      return;
    }

    // Użytkownik dołączył do kanału
    if (!oldState.channelId && newState.channelId && !newState.member.user.bot) {
      try {
        const botVoiceState = newState.guild.members.me?.voice;
        if (botVoiceState && botVoiceState.channel) {
          // Bot już jest na kanale
          return;
        }

        // Sprawdź czy kanał nie jest AFK
        if (newState.channel.flags.has('JOIN_FOR_ACTIVITY')) {
          return;
        }

        const logChannel = newState.guild.channels.cache.find(
          ch => ch.name === 'logs' && ch.isTextBased()
        );

        if (logChannel) {
          const embed = new EmbedBuilder()
            .setColor('Green')
            .setDescription(`👤 ${newState.member.user.username} dołączył do kanału ${newState.channel.name}`);
          logChannel.send({ embeds: [embed] });
        }
      } catch (error) {
        console.error('Błąd w voiceStateUpdate:', error);
      }
    }

    // Użytkownik opuścił kanał
    if (oldState.channelId && !newState.channelId && !oldState.member.user.bot) {
      try {
        const logChannel = newState.guild.channels.cache.find(
          ch => ch.name === 'logs' && ch.isTextBased()
        );

        if (logChannel) {
          const embed = new EmbedBuilder()
            .setColor('Red')
            .setDescription(`👤 ${oldState.member.user.username} opuścił kanał`);
          logChannel.send({ embeds: [embed] });
        }

        // Jeśli bot jest sam na kanale, opuść go
        const botVoiceState = oldState.guild.members.me?.voice;
        if (botVoiceState && botVoiceState.channel && botVoiceState.channelId === oldState.channelId) {
          const voiceMembers = botVoiceState.channel.members.filter(m => !m.user.bot);
          if (voiceMembers.size === 0) {
            const queue = player.queues.get(oldState.guild.id);
            if (queue) {
              queue.delete();
            }
          }
        }
      } catch (error) {
        console.error('Błąd w voiceStateUpdate:', error);
      }
    }
  }
};
