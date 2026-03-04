const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const User = require('../../models/User');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('rank')
    .setDescription('Sprawdź swój level i XP')
    .addUserOption(opt => opt.setName('user').setDescription('Użytkownik').setRequired(false)),
  async execute(interaction) {
    if (interaction.guildId !== process.env.GUILD_ID) return;
    const target = interaction.options.getUser('user') || interaction.user;
    const userData = await User.findOne({ userId: target.id, guildId: interaction.guildId });

    if (!userData) {
      return interaction.reply({ content: `${target.username} nie ma jeszcze żadnego XP!`, ephemeral: true });
    }

    const xpNeeded = userData.xpForNextLevel();
    const progress = Math.floor((userData.xp / xpNeeded) * 20);
    const bar = '█'.repeat(progress) + '░'.repeat(20 - progress);

    const rank = await User.countDocuments({
      guildId: interaction.guildId,
      $or: [{ level: { $gt: userData.level } }, { level: userData.level, xp: { $gt: userData.xp } }]
    }) + 1;

    const embed = new EmbedBuilder()
      .setColor('#5865F2')
      .setTitle(`Rank — ${target.username}`)
      .setThumbnail(target.displayAvatarURL())
      .addFields(
        { name: 'Level', value: `**${userData.level}**`, inline: true },
        { name: 'XP', value: `**${userData.xp}** / ${xpNeeded}`, inline: true },
        { name: 'Ranking', value: `**#${rank}**`, inline: true },
        { name: 'Postęp', value: `\`${bar}\`` }
      )
      .setFooter({ text: `ID: ${target.id}` });

    return interaction.reply({ embeds: [embed] });
  },
};
