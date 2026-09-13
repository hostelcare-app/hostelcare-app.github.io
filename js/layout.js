(function (global) {
  function renderSidebar(activePage, user) {
    const isAdmin = user.role === "admin";
    const links = [{ href: "dashboard.html", label: "Dashboard", page: "dashboard" }];
    if (!isAdmin) {
      links.push({ href: "submit-complaint.html", label: "Submit complaint", page: "submit" });
    }
    const linkHtml = links
      .map(function (l) {
        const cls = l.page === activePage ? "active" : "";
        return '<a class="' + cls + '" href="' + l.href + '"><span class="nav-dot"></span>' + l.label + "</a>";
      })
      .join("");

    const sidebarEl = document.getElementById("sidebar");
    if (sidebarEl && isAdmin) sidebarEl.classList.add("sidebar-admin");

    return (
      '<a class="brand-mark" href="dashboard.html"><span class="brand-dot"></span>Hostel Care</a>' +
      '<ul class="nav-links">' + linkHtml + "</ul>" +
      '<div class="sidebar-user">' +
        '<div class="name">' + escapeHtml(user.name) + "</div>" +
        '<div class="role' + (isAdmin ? " role-admin" : "") + '">' + (isAdmin ? "Warden / Admin" : escapeHtml(user.role)) + "</div>" +
        '<button class="btn btn-danger-text btn-sm" id="logoutBtn" type="button">Log out</button>' +
      "</div>"
    );
  }

  function escapeHtml(str) {
    return String(str || "").replace(/[&<>"']/g, function (m) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m];
    });
  }

  function mount(activePage) {
    const user = Auth.requireAuth();
    if (!user) return null;
    const el = document.getElementById("sidebar");
    if (el) el.innerHTML = renderSidebar(activePage, user);
    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) logoutBtn.addEventListener("click", Auth.logout);
    return user;
  }

  global.Layout = { mount, escapeHtml };
})(window);
