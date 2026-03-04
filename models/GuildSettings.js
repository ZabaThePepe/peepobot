const mongoose = require('mongoose');

const levelRoleSchema = new mongoose.Schema({
  level: { type: Number, required: true },
  roleId: { type: String, required: true },
  roleName: { type: String },
});

const xpBoosterSchema = new mongoose.Schema({
  roleId: { type: String, required: true },
  roleName: { type: String },
  multiplier: { type: Number, required: true, min: 1.1, max: 10 },
});

const globalEventSchema = new mongoose.Schema({
  active: { type: Boolean, default: false },
  multiplier: { type: Number, default: 2, min: 1.1, max: 10 },
  name: { type: String, default: 'Event XP' },
  startedAt: { type: Date, default: null },
  endsAt: { type: Date, default: null }, // null = bez limitu czasu
});

const guildSettingsSchema = new mongoose.Schema({
  guildId: { type: String, required: true, unique: true },
  announcementChannelId: { type: String, default: null },
  xpPerMessage: { type: Number, default: 15, min: 1, max: 500 },
  xpPerMinuteVC: { type: Number, default: 10, min: 1, max: 500 },
  messageCooldownSeconds: { type: Number, default: 60 },
  levelRoles: [levelRoleSchema],
  xpBoosters: [xpBoosterSchema],
  globalEvent: { type: globalEventSchema, default: () => ({}) },
}, { timestamps: true });

// Zwraca aktywny mnożnik globalny (uwzględnia wygaśnięcie)
guildSettingsSchema.methods.getGlobalMultiplier = function () {
  const ev = this.globalEvent;
  if (!ev || !ev.active) return 1;
  if (ev.endsAt && new Date() > ev.endsAt) return 1;
  return ev.multiplier;
};

module.exports = mongoose.model('GuildSettings', guildSettingsSchema);
