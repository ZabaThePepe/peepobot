const { ActivityType } = require('discord.js');

module.exports = {
  name: 'ready',
  once: true,
  execute(client) {
    console.log(`✅ Bot zalogowany jako ${client.user.tag}`);
    client.user.setActivity('To co swierzak?', {
      type: ActivityType.Streaming,
      url: 'https://twitch.tv/zabathepepeee',
    });
  },
};
