module.exports = {
  name: 'interactionCreate',
  async execute(interaction) {
    if (!interaction.isChatInputCommand()) return;

    const command = interaction.client.commands.get(interaction.commandName);

    if (!command) {
      console.error(`❌ Komenda ${interaction.commandName} nie znaleziona`);
      return;
    }

    try {
      await command.execute(interaction);
    } catch (error) {
      console.error(error);
      if (interaction.replied || interaction.deferred) {
        await interaction.followUp({
          content: '❌ Błąd podczas wykonywania komendy!',
          ephemeral: true
        });
      } else {
        await interaction.reply({
          content: '❌ Błąd podczas wykonywania komendy!',
          ephemeral: true
        });
      }
    }
  }
};
