const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const User = require('../../models/User');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('leaderboard')
    .setDescription('Top 10 użytkowników na serwerze'),

  async execute(interaction) {
    if (interaction.guildId !== process.env.GUILD_ID) return;
    await interaction.deferReply();

    const top = await User.find({ guildId: interaction.guildId })
      .sort({ level: -1, xp: -1 })
      .limit(10);

    if (!top.length) {
      return interaction.editReply({
        embeds: [
          new EmbedBuilder()
            .setColor('#2B2D31')
            .setDescription('> 📭 Nikt jeszcze nie zdobył XP na tym serwerze.')
        ]
      });
    }

    const medals = ['🥇', '🥈', '🥉'];
    const rankIcons = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩'];

    const lines = await Promise.all(top.map(async (u, i) => {
      let name;
      try {
        const member = await interaction.guild.members.fetch(u.userId);
        name = member.displayName;
      } catch {
        name = `Nieznany użytkownik`;
      }

      const prefix = medals[i] ?? `\`#${i + 1}\``;
      const xpNeeded = u.xpForNextLevel ? u.xpForNextLevel() : '?';
      return `${prefix} **${name}**\n　└ Poziom **${u.level}** • \`${u.xp} XP\``;
    }));

    const embed = new EmbedBuilder()
      .setColor('#FFD700')
      .setAuthor({
        name: interaction.guild.name,
        iconURL: interaction.guild.iconURL({ dynamic: true }) ?? undefined,
      })
      .setTitle('🏆  Ranking Serwera')
      .setDescription(lines.join('\n\n'))
      .setFooter({ text: `Top 10 • Aktualizacja co wiadomość` })
      .setTimestamp();

    return interaction.editReply({ embeds: [embed] });
  },
};
