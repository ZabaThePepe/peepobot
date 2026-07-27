const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { useMainPlayer } = require('discord-player');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('play')
    .setDescription('Puszcza muzykę z YouTube')
    .addStringOption(option =>
      option
        .setName('query')
        .setDescription('Link lub nazwa piosenki')
        .setRequired(true)
    ),
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

    await interaction.deferReply();

    try {
      const player = useMainPlayer();
      const query = interaction.options.getString('query');

      const result = await player.search(query, {
        requestedBy: interaction.user
      });

      if (!result || !result.tracks.length) {
        return interaction.editReply({
          embeds: [new EmbedBuilder()
            .setColor('Red')
            .setDescription('❌ Nie znaleźliśmy żadnej piosenki!')
          ]
        });
      }

      const { playlist, tracks } = await player.play(
        interaction.member.voice.channel,
        result,
        {
          nodeOptions: {
            metadata: interaction
          }
        }
      );

      const embed = new EmbedBuilder()
        .setColor('Green')
        .setTitle('🎵 Dodane do kolejki')
        .setDescription(`${tracks.length} piosenka(i) dodana(ne)`)
        .addFields({
          name: 'Aktualna piosenka',
          value: tracks[0].title || 'Nieznana',
          inline: false
        })
        .setThumbnail(tracks[0].thumbnail);

      interaction.editReply({ embeds: [embed] });
    } catch (error) {
      console.error(error);
      interaction.editReply({
        embeds: [new EmbedBuilder()
          .setColor('Red')
          .setDescription('❌ Błąd podczas odtwarzania!')
        ]
      });
    }
  }
};
