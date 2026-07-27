const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { useMainPlayer } = require('discord-player');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('pause')
    .setDescription('Pauzuje aktualną muzykę'),
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

      if (!queue || !queue.isPlaying()) {
        return interaction.reply({
          embeds: [new EmbedBuilder()
            .setColor('Red')
            .setDescription('❌ Nic nie jest odtwarzane!')
          ],
          ephemeral: true
        });
      }

      const wasPaused = queue.isPaused();
      queue.setPaused(!wasPaused);

      const status = wasPaused ? '▶️ Wznowiono' : '⏸️ Pauzowano';

      interaction.reply({
        embeds: [new EmbedBuilder()
          .setColor('Blue')
          .setDescription(`${status}`)
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
