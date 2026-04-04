const express = require('express');
const axios = require('axios');
const router = express.Router();

const REDIRECT_URI = `${process.env.DASHBOARD_URL}/auth/callback`;

// Przekierowanie do Discorda w celu logowania
router.get('/login', (req, res) => {
  const params = new URLSearchParams({
    client_id: process.env.DISCORD_CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: 'code',
    scope: 'identify guilds',
  });
  res.redirect(`https://discord.com/api/oauth2/authorize?${params}`);
});

// Callback po zalogowaniu w Discordzie
router.get('/auth/callback', async (req, res) => {
  const { code } = req.query;
  if (!code) return res.redirect('/');

  try {
    // Wymiana kodu na token
    const tokenRes = await axios.post('https://discord.com/api/oauth2/token',
      new URLSearchParams({
        client_id: process.env.DISCORD_CLIENT_ID,
        client_secret: process.env.DISCORD_CLIENT_SECRET,
        grant_type: 'authorization_code',
        code,
        redirect_uri: REDIRECT_URI,
      }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );

    const { access_token } = tokenRes.data;
    const headers = { Authorization: `Bearer ${access_token}` };

    // Pobranie danych użytkownika i guilds
    const [userRes, guildsRes] = await Promise.all([
      axios.get('https://discord.com/api/users/@me', { headers }),
      axios.get('https://discord.com/api/users/@me/guilds', { headers }),
    ]);

    const guild = guildsRes.data.find(g => g.id === process.env.GUILD_ID);
    const isAdmin = guild && (guild.permissions & 0x8) === 0x8;

    // Zapis sesji
    req.session.user = {
      id: userRes.data.id,
      username: userRes.data.username,
      avatar: userRes.data.avatar,
      isAdmin: !!isAdmin,
    };

    // Przekierowanie na dashboard jeśli admin, inaczej error
    res.redirect(isAdmin ? '/dashboard' : '/?error=noadmin');
  } catch (err) {
    console.error('OAuth error:', err.response?.data || err.message);
    res.redirect('/?error=oauth');
  }
});

// Wylogowanie
router.get('/logout', (req, res) => {
  req.session.destroy();
  res.redirect('/');
});

module.exports = router;
