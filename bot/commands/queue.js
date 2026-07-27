const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { useMainPlayer } = require('discord-player');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('queue')
    .setDescription('Wyświetla kolejkę piosenek'),
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

      const tracks = queue.tracks.slice(0, 10);
      const current = queue.currentTrack;

      const description = [
        `**▶️ Aktualnie:** ${current.title}`,
        `**Czas:** ${current.duration}ms`,
        '',
        '**📋 Następne:**',
        ...tracks.map((track, i) => `${i + 1}. ${track.title}`)
      ].join('\n');

      const embed = new EmbedBuilder()
        .setColor('Blue')
        .setTitle('🎵 Kolejka piosenek')
        .setDescription(description)
        .setFooter({ text: `Razem: ${queue.tracks.length + 1} piosenek` });

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
