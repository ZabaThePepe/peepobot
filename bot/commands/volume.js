const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const { useMainPlayer } = require('discord-player');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('volume')
    .setDescription('Reguluje głośność bota')
    .addIntegerOption(option =>
      option
        .setName('level')
        .setDescription('Poziom głośności (0-200)')
        .setMinValue(0)
        .setMaxValue(200)
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

      const volume = interaction.options.getInteger('level');
      queue.node.setVolume(volume);

      interaction.reply({
        embeds: [new EmbedBuilder()
          .setColor('Yellow')
          .setDescription(`🔊 Głośność ustawiona na ${volume}%`)
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
