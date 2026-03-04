# Discord Bot Dashboard

Bot XP z dashboardem webowym dla jednego serwera Discord.

## Wymagania
- Node.js 18+
- MongoDB Atlas
- Konto Discord Developer

## Instalacja

1. Sklonuj repo i zainstaluj zależności:
```bash
   npm install
```

2. Skopiuj `.env.example` do `.env` i uzupełnij wartości:
```bash
   cp .env.example .env
```

3. W Discord Developer Portal:
   - Stwórz aplikację → Bot
   - Skopiuj TOKEN, CLIENT_ID, CLIENT_SECRET
   - Włącz: `MESSAGE CONTENT INTENT`, `SERVER MEMBERS INTENT`
   - Dodaj Redirect URI: `http://localhost:3000/auth/callback`

4. Uruchom lokalnie:
```bash
   npm run dev
```

## Deploy na Railway

1. Wrzuć kod na GitHub
2. W Railway: New Project → Deploy from GitHub
3. Dodaj zmienne środowiskowe z `.env`
4. Zmień `DASHBOARD_URL` na URL Railway
5. Zaktualizuj Redirect URI w Discord Developer Portal

## Zmienne środowiskowe

| Zmienna | Opis |
|---|---|
| `DISCORD_TOKEN` | Token bota |
| `DISCORD_CLIENT_ID` | ID aplikacji Discord |
| `DISCORD_CLIENT_SECRET` | Secret OAuth2 |
| `GUILD_ID` | ID serwera |
| `DASHBOARD_URL` | URL dashboardu (np. https://app.railway.app) |
| `SESSION_SECRET` | Losowy string min. 32 znaki |
| `MONGODB_URI` | Connection string MongoDB Atlas |

## Funkcje

### Bot
- `/rank` — wyświetla level i XP użytkownika
- `/leaderboard` — top 10 serwera
- XP za wiadomości (cooldown 60s)
- XP za VC (min. 2 osoby, co minutę)

### Dashboard
- Logowanie przez Discord OAuth2
- Ustawienie XP per wiadomość/VC
- Ustawienie kanału ogłoszeń
- Dodawanie/usuwanie ról za levele
