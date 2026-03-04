const mongoose = require('mongoose');

const levelRoleSchema = new mongoose.Schema({
  level: { type: Number, required: true },
  roleId: { type: String, required: true },
  roleName: { type: String },
});

const guildSettingsSchema = new mongoose.Schema({
  guildId: {
    type: String,
    required: true,
    unique: true,
  },
  announcementChannelId: {
    type: String,
    default: null,
  },
  xpPerMessage: {
    type: Number,
    default: 15,
    min: 1,
    max: 500,
  },
  xpPerMinuteVC: {
    type: Number,
    default: 10,
    min: 1,
    max: 500,
  },
  messageCooldownSeconds: {
    type: Number,
    default: 60,
  },
  levelRoles: [levelRoleSchema],
}, { timestamps: true });

module.exports = mongoose.model('GuildSettings', guildSettingsSchema);
