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

    if (!top.length) return interaction.editReply('Brak danych!');

    const medals = ['🥇', '🥈', '🥉'];
    const lines = await Promise.all(top.map(async (u, i) => {
      let name;
      try {
        const member = await interaction.guild.members.fetch(u.userId);
        name = member.displayName;
      } catch { name = `Użytkownik (${u.userId.slice(0, 6)})`; }
      const medal = medals[i] || `**${i + 1}.**`;
      return `${medal} ${name} — Level **${u.level}** (${u.xp} XP)`;
    }));

    const embed = new EmbedBuilder()
      .setColor('#FFD700')
      .setTitle('🏆 Leaderboard — Top 10')
      .setDescription(lines.join('\n'))
      .setTimestamp();

    return interaction.editReply({ embeds: [embed] });
  },
};
