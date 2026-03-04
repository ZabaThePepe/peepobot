module.exports = {
  name: 'ready',
  once: true,
  execute(client) {
    console.log(`✅ Bot zalogowany jako ${client.user.tag}`);
    client.user.setActivity('📊 Zbiera XP', { type: 3 });
  },
};
