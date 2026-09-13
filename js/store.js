/*
  Hostel Care — data store
  Everything lives in the browser's localStorage. There is no server,
  so this data is local to this browser only (perfect for a demo,
  not meant for real multi-device use).
*/
(function (global) {
  const USERS_KEY = "hc_users";
  const COMPLAINTS_KEY = "hc_complaints";
  const SEQ_KEY = "hc_ticket_seq";
  const SESSION_KEY = "hc_session";

  const WORKERS = [
    "Ramesh Yadav — Plumbing",
    "Suresh Singh — Electrical",
    "Mahesh Verma — Carpentry",
    "Sunita Devi — Mess Supervisor",
    "General Maintenance Staff",
  ];

  // Maps a complaint category to the worker best suited to handle it.
  // Used to auto-suggest an assignee on the admin ticket view.
  const CATEGORY_WORKER_MAP = {
    Plumber: "Ramesh Yadav — Plumbing",
    Electrician: "Suresh Singh — Electrical",
    Carpenter: "Mahesh Verma — Carpentry",
    Mess: "Sunita Devi — Mess Supervisor",
    General: "General Maintenance Staff",
  };

  function suggestWorkerForCategory(category) {
    return CATEGORY_WORKER_MAP[category] || "General Maintenance Staff";
  }

  function read(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }
  function write(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function seedIfEmpty() {
    let users = read(USERS_KEY, null);
    if (!users) {
      users = [
        {
          id: 1,
          username: "student1",
          password: "password123",
          name: "Rajesh Kumar",
          email: "rajesh@college.edu",
          roomNumber: "A101",
          role: "student",
        },
        {
          id: 2,
          username: "admin",
          password: "admin123",
          name: "Warden Office",
          email: "admin@hostel.edu",
          role: "admin",
        },
      ];
      write(USERS_KEY, users);
    }
    if (!read(COMPLAINTS_KEY, null)) {
      write(COMPLAINTS_KEY, []);
    }
    if (read(SEQ_KEY, null) === null) {
      write(SEQ_KEY, 1);
    }
  }

  function getUsers() {
    return read(USERS_KEY, []);
  }
  function saveUsers(users) {
    write(USERS_KEY, users);
  }
  function findUserByUsername(username) {
    return getUsers().find(
      (u) => u.username.toLowerCase() === String(username).toLowerCase()
    );
  }
  function addUser(user) {
    const users = getUsers();
    const nextId = users.reduce((m, u) => Math.max(m, u.id), 0) + 1;
    const record = Object.assign({ id: nextId, role: "student" }, user);
    users.push(record);
    saveUsers(users);
    return record;
  }

  function getComplaints() {
    return read(COMPLAINTS_KEY, []);
  }
  function saveComplaints(list) {
    write(COMPLAINTS_KEY, list);
  }
  function getComplaintById(id) {
    return getComplaints().find((c) => c.id === Number(id));
  }
  function nextTicketNo() {
    const seq = read(SEQ_KEY, 1);
    write(SEQ_KEY, seq + 1);
    return "HC-" + String(seq).padStart(4, "0");
  }
  function addComplaint(data) {
    const list = getComplaints();
    const nextId = list.reduce((m, c) => Math.max(m, c.id), 0) + 1;
    const record = Object.assign(
      {
        id: nextId,
        ticketNo: nextTicketNo(),
        status: "open",
        assignedWorker: "",
        resolutionNotes: "",
        createdAt: new Date().toISOString(),
        resolvedAt: null,
      },
      data
    );
    list.push(record);
    saveComplaints(list);
    return record;
  }
  function updateComplaint(id, patch) {
    const list = getComplaints();
    const idx = list.findIndex((c) => c.id === Number(id));
    if (idx === -1) return null;
    list[idx] = Object.assign({}, list[idx], patch);
    saveComplaints(list);
    return list[idx];
  }
  function deleteComplaint(id) {
    const list = getComplaints();
    const filtered = list.filter((c) => c.id !== Number(id));
    saveComplaints(filtered);
    return filtered.length !== list.length;
  }
  function submitFeedback(id, rating, comment) {
    return updateComplaint(id, {
      rating: Number(rating),
      feedbackComment: comment || "",
      feedbackAt: new Date().toISOString(),
    });
  }

  function getSession() {
    return read(SESSION_KEY, null);
  }
  function setSession(userId) {
    write(SESSION_KEY, { userId: userId });
  }
  function clearSession() {
    localStorage.removeItem(SESSION_KEY);
  }
  function getCurrentUser() {
    const s = getSession();
    if (!s) return null;
    return getUsers().find((u) => u.id === s.userId) || null;
  }

  global.Store = {
    WORKERS,
    seedIfEmpty,
    getUsers,
    findUserByUsername,
    addUser,
    getComplaints,
    getComplaintById,
    addComplaint,
    updateComplaint,
    deleteComplaint,
    submitFeedback,
    suggestWorkerForCategory,
    getSession,
    setSession,
    clearSession,
    getCurrentUser,
  };
})(window);
