const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { useMainPlayer } = require('discord-player');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('leave')
    .setDescription('Bot opuszcza kanał głosowy'),
  async execute(interaction) {
    if (!interaction.member.voice.channel) {
      return interaction.reply({
        embeds: [new EmbedBuilder()
          .setColor('Red')
          .setDescription('❌ Musisz być na kanale głosowym!')
        ],
        ephemeral: true
      });
    }

    try {
      const player = useMainPlayer();
      const queue = player.queues.get(interaction.guildId);

      if (queue) {
        queue.delete();
      }

      interaction.reply({
        embeds: [new EmbedBuilder()
          .setColor('Purple')
          .setDescription('👋 Do widzenia!')
        ]
      });
    } catch (error) {
      console.error(error);
      interaction.reply({
        embeds: [new EmbedBuilder()
          .setColor('Red')
          .setDescription('❌ Błąd!')
        ],
        ephemeral: true
      });
    }
  }
};
