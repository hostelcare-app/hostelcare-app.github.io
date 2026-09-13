/*
  Hostel Care — auth helpers
  No server, so this is demo-level auth only: plain-text password
  matching against the local users list. Good enough to demonstrate
  the flow, not meant as real security.
*/
(function (global) {
  function login(username, password) {
    const user = Store.findUserByUsername(username);
    if (user && user.password === password) {
      Store.setSession(user.id);
      return { ok: true, user };
    }
    return { ok: false, error: "Invalid username or password." };
  }

  function register(fields) {
    if (Store.findUserByUsername(fields.username)) {
      return { ok: false, error: "That username is already taken." };
    }
    const user = Store.addUser({
      username: fields.username,
      password: fields.password,
      name: fields.name,
      email: fields.email,
      roomNumber: fields.roomNumber,
      role: "student",
    });
    return { ok: true, user };
  }

  function logout() {
    Store.clearSession();
    window.location.href = "index.html";
  }

  // Call at the top of any protected page. Redirects to login if there
  // is no session, and returns the current user otherwise.
  function requireAuth() {
    const user = Store.getCurrentUser();
    if (!user) {
      window.location.href = "index.html";
      return null;
    }
    return user;
  }

  global.Auth = { login, register, logout, requireAuth };
})(window);
