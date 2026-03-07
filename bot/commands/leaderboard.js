const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const User = require('../../models/User');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('leaderboard')
    .setDescription('Top 10 użytkowników na serwerze'),
  async execute(interaction) {
    if (interaction.guildId !== process.env.GUILD_ID) return;
    await interaction.deferReply();

    // Pobieramy więcej niż 10, bo będziemy odfiltrowywać boty i byłych członków
    const top = await User.find({ guildId: interaction.guildId })
      .sort({ level: -1, xp: -1 })
      .limit(50);

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
    const lines = [];

    for (const u of top) {
      if (lines.length >= 10) break;
      let member;
      try {
        member = await interaction.guild.members.fetch(u.userId);
      } catch {
        continue; // opuścił serwer — pomijamy
      }
      if (member.user.bot) continue; // pomijamy boty

      const i = lines.length;
      const prefix = medals[i] ?? `\`#${i + 1}\``;
      lines.push(`${prefix} **${member.displayName}**\n　└ Poziom **${u.level}** • \`${u.xp} XP\``);
    }

    if (!lines.length) {
      return interaction.editReply({
        embeds: [
          new EmbedBuilder()
            .setColor('#2B2D31')
            .setDescription('> 📭 Nikt jeszcze nie zdobył XP na tym serwerze.')
        ]
      });
    }

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
