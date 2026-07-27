const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { useMainPlayer } = require('discord-player');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('nowplaying')
    .setDescription('Wyświetla aktualnie graną piosenkę'),
  async execute(interaction) {
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

      const track = queue.currentTrack;
      const progress = queue.node.getTimestamp();

      const embed = new EmbedBuilder()
        .setColor('Green')
        .setTitle('🎵 Aktualnie graczy')
        .setDescription(track.title)
        .setURL(track.url)
        .setThumbnail(track.thumbnail)
        .addFields({
          name: 'Artysta',
          value: track.author || 'Nieznany',
          inline: true
        }, {
          name: 'Czas trwania',
          value: track.duration ? `${track.duration}ms` : 'Nieznany',
          inline: true
        }, {
          name: 'Postęp',
          value: `${progress.current}ms / ${progress.total}ms`,
          inline: false
        })
        .setFooter({ text: `Widoki: ${track.views || 0}` });

      interaction.reply({ embeds: [embed] });
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
