let user = {};
let attendance = {};
let currentDate = new Date(2026, 1); // Feb 2026
let currentUser = null;
let currentRole = null;

function login() {
  const name = document.getElementById("username").value.trim();
  const role = document.getElementById("role").value;

  if (!name) {
    alert("Please enter your name");
    return;
  }

  currentUser = name;
  currentRole = role;

  document.getElementById("loginBox").style.display = "none";
  document.getElementById("dashboard").classList.remove("hidden");

  document.getElementById("welcome").innerText =
    `Welcome ${currentUser} (${currentRole.toUpperCase()})`;

  renderCalendar();
}

// Turns the end of a lecture time into [hour, minute].
// data.js writes times like "07-08" or "12-01" (no minutes), the old code expected "09:00".
// Accepts both. Hours below 7 are afternoon ("01" -> 13) because lectures don't start at 1am.
function parseEndTime(text) {
  const [h, m] = text.split(":").map(Number);
  const hour = h < 7 ? h + 12 : h;
  return [hour, m || 0];
}

/* UPDATED CALENDAR LOGIC */
function renderCalendar() {
  const grid = document.getElementById("calendarGrid");
  const title = document.getElementById("monthYear");
  const statsDiv = document.getElementById("stats");

  grid.innerHTML = "";
  statsDiv.innerHTML = "";

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const now = new Date(); // Real-time for comparison

  title.innerText = currentDate.toLocaleString("default", { month: "long", year: "numeric" });

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const offset = (firstDay + 6) % 7;

  for (let i = 0; i < offset; i++) {
    grid.appendChild(document.createElement("div"));
  }

  let subjectCount = {};
  let subjectPresent = {};

  for (let day = 1; day <= daysInMonth; day++) {
    const box = document.createElement("div");
    box.className = "day";
    box.innerHTML = `<strong>${day}</strong><br>`;

    const dateOfBox = new Date(year, month, day);
    const weekday = dateOfBox.toLocaleString("default", { weekday: "long" });

    if (timetable[weekday]) {
      timetable[weekday].forEach(lec => {
        if (lec.subject === "Break") return; // Skip breaks

        const key = `${year}-${month}-${day}-${lec.subject}-${lec.time}`;
        const status = attendance[key];

        // Parse Lecture End Time
        const endTimeStr = lec.time.split("-")[1]; // e.g., "09:00" or "08"
        const [endHour, endMin] = parseEndTime(endTimeStr);
        const lectureEndTime = new Date(year, month, day, endHour, endMin);

        const isOver = now > lectureEndTime;

        // Statistics Logic
        if (isOver) {
          subjectCount[lec.subject] = (subjectCount[lec.subject] || 0) + 1;
          if (status === "present") {
            subjectPresent[lec.subject] = (subjectPresent[lec.subject] || 0) + 1;
          }
        }

        // Create UI element
        const l = document.createElement("div");
        l.className = "lecture";
        l.style.background = isOver ? "#ccc" : (lec.color || "#4ea8de"); // Grey if over
        l.style.color = isOver ? "#666" : "white";
        l.style.cursor = isOver ? "pointer" : "not-allowed";

        if (status === "present") l.classList.add("present");
        if (status === "absent") l.classList.add("absent");

        l.innerText = `${lec.time} ${lec.subject}`;
        
        // Only allow marking if lecture is over
        l.onclick = () => {
          if (isOver) {
            markAttendance(key);
          } else {
            alert("This lecture hasn't finished yet! Attendance opens after " + endTimeStr);
          }
        };

        box.appendChild(l);
      });
    }
    grid.appendChild(box);
  }

  // Render stats (remains same)
  for (let sub in subjectCount) {
    const percent = Math.round(((subjectPresent[sub] || 0) / subjectCount[sub]) * 100);
    statsDiv.innerHTML += `<p>${sub}: <strong>${percent}%</strong></p>`;
  }
}

/* STUDY MATERIAL */
function uploadMaterial() {
  materials.push({
    topic: topic.value,
    by: user.name
  });
  renderMaterials();
}

function renderMaterials() {
  let div = document.getElementById("materials");
  div.innerHTML = "";
  materials.forEach(m => {
    div.innerHTML += `<p>${m.topic} (by ${m.by})</p>`;
  });
}

/* ANNOUNCEMENTS */
function postAnnouncement() {
  announcements.push({
    msg: msg.value,
    by: currentRole
  });
  renderAnnouncements();
}

function renderAnnouncements() {
  let div = document.getElementById("announceList");
  div.innerHTML = "";
  announcements.forEach(a => {
    div.innerHTML += `<p>📢 ${a.msg} — ${a.by}</p>`;
  });
}

function markAttendance(key) {
  const choice = prompt("Type P for Present or A for Absent");

  if (choice === "P" || choice === "p") {
    attendance[key] = "present";
  } else if (choice === "A" || choice === "a") {
    attendance[key] = "absent";
  }

  renderCalendar();
    checkWarnings();
}

function checkWarnings() {
  let warnings = [];

  for (let sub in subjectCount) {
    const percent = Math.round(
      ((subjectPresent[sub] || 0) / subjectCount[sub]) * 100
    );
    if (percent < 75) {
      warnings.push(`${sub} below 75%`);
    }
  }

  if (warnings.length) {
    alert("⚠ Attendance Warning:\n" + warnings.join("\n"));
  }
}

function showTab(id) {
  document.querySelectorAll(".tab").forEach(t =>
    t.classList.add("hidden")
  );
  document.getElementById(id).classList.remove("hidden");
}

function changeMonth(dir) {
  currentDate.setMonth(currentDate.getMonth() + dir);
  renderCalendar();
}

// index.html calls these two names; they just forward to changeMonth
function prevMonth() { changeMonth(-1); }
function nextMonth() { changeMonth(1); }



