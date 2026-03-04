require('dotenv').config();
const mongoose = require('mongoose');

async function main() {
  // Połącz z MongoDB
  await mongoose.connect(process.env.MONGODB_URI);
  console.log('✅ Połączono z MongoDB');

  // Uruchom bota
  const bot = require('./bot/index');

  // Uruchom dashboard
  const dashboard = require('./dashboard/index');
  const PORT = process.env.PORT || 3000;
  dashboard.listen(PORT, () => {
    console.log(`✅ Dashboard działa na porcie ${PORT}`);
  });
}

main().catch(err => {
  console.error('❌ Błąd uruchamiania:', err);
  process.exit(1);
});
