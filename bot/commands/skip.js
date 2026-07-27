const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { useMainPlayer } = require('discord-player');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('skip')
    .setDescription('Pomija aktualną piosenkę'),
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

      const currentTrack = queue.currentTrack;
      queue.node.skip();

      interaction.reply({
        embeds: [new EmbedBuilder()
          .setColor('Yellow')
          .setDescription(`⏭️ Pominięto: ${currentTrack.title}`)
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
