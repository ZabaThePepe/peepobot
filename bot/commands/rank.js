const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const User = require('../../models/User');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('rank')
    .setDescription('Sprawdź swój level i XP')
    .addUserOption(opt =>
      opt.setName('user').setDescription('Użytkownik').setRequired(false)
    ),

  async execute(interaction) {
    if (interaction.guildId !== process.env.GUILD_ID) return;

    const target = interaction.options.getUser('user') || interaction.user;
    const userData = await User.findOne({ userId: target.id, guildId: interaction.guildId });

    if (!userData) {
      return interaction.reply({
        embeds: [
          new EmbedBuilder()
            .setColor('#ED4245')
            .setDescription(`> ❌ **${target.username}** nie ma jeszcze żadnego XP!`)
        ],
        ephemeral: true,
      });
    }

    const xpNeeded = userData.xpForNextLevel();
    const percent = Math.min(userData.xp / xpNeeded, 1);
    const filled = Math.round(percent * 15);
    const empty = 15 - filled;
    const bar = '▰'.repeat(filled) + '▱'.repeat(empty);
    const percentDisplay = Math.floor(percent * 100);

    const rank = await User.countDocuments({
      guildId: interaction.guildId,
      $or: [
        { level: { $gt: userData.level } },
        { level: userData.level, xp: { $gt: userData.xp } },
      ],
    }) + 1;

    // Color shifts from blue → purple → gold based on level
    let color = '#5865F2';
    if (userData.level >= 10) color = '#9B59B6';
    if (userData.level >= 25) color = '#FFD700';

    const embed = new EmbedBuilder()
      .setColor(color)
      .setAuthor({
        name: target.username,
        iconURL: target.displayAvatarURL({ dynamic: true }),
      })
      .setThumbnail(target.displayAvatarURL({ dynamic: true, size: 256 }))
      .setTitle(`✨ Karta Gracza`)
      .addFields(
        {
          name: '🎯 Poziom',
          value: `\`\`\`${userData.level}\`\`\``,
          inline: true,
        },
        {
          name: '⚡ XP',
          value: `\`\`\`${userData.xp} / ${xpNeeded}\`\`\``,
          inline: true,
        },
        {
          name: '🏅 Ranking',
          value: `\`\`\`#${rank}\`\`\``,
          inline: true,
        },
        {
          name: `📊 Postęp do następnego poziomu — ${percentDisplay}%`,
          value: `${bar}`,
        }
      )
      .setFooter({ text: `ID: ${target.id}` })
      .setTimestamp();

    return interaction.reply({ embeds: [embed] });
  },
};
