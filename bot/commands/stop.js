const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { useMainPlayer } = require('discord-player');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('stop')
    .setDescription('Zatrzymuje muzykę i czyści kolejkę'),
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

      if (!queue) {
        return interaction.reply({
          embeds: [new EmbedBuilder()
            .setColor('Red')
            .setDescription('❌ Nic nie jest odtwarzane!')
          ],
          ephemeral: true
        });
      }

      queue.delete();

      interaction.reply({
        embeds: [new EmbedBuilder()
          .setColor('Red')
          .setDescription('⏹️ Muzyka zatrzymana')
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
