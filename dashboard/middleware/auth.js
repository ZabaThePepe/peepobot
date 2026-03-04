module.exports = function requireAuth(req, res, next) {
  if (!req.session.user) return res.redirect('/auth/login');
  if (!req.session.user.isAdmin) return res.status(403).render('error', { message: 'Brak uprawnień administratora.' });
  next();
};
