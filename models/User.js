const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
  userId: {
    type: String,
    required: true,
    unique: true,
  },
  guildId: {
    type: String,
    required: true,
  },
  xp: {
    type: Number,
    default: 0,
  },
  level: {
    type: Number,
    default: 0,
  },
  lastMessage: {
    type: Date,
    default: null,
  },
}, { timestamps: true });

// Oblicz wymagane XP do następnego levelu
userSchema.methods.xpForNextLevel = function () {
  return 100 * (this.level + 1) * 1.5;
};

// Sprawdź czy awansował
userSchema.methods.checkLevelUp = function () {
  const required = this.xpForNextLevel();
  if (this.xp >= required) {
    this.xp -= required;
    this.level += 1;
    return true;
  }
  return false;
};

module.exports = mongoose.model('User', userSchema);
