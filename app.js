alert("JS is connected");
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

/* CALENDAR */
function renderCalendar() {
  const grid = document.getElementById("calendarGrid");
  const title = document.getElementById("monthYear");
  const statsDiv = document.getElementById("stats");

  grid.innerHTML = "";
  statsDiv.innerHTML = "";

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  title.innerText = currentDate.toLocaleString("default", {
    month: "long",
    year: "numeric"
  });

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

    const weekday = new Date(year, month, day)
      .toLocaleString("default", { weekday: "long" });

    if (timetable[weekday]) {
      timetable[weekday].forEach(lec => {
        const key = `${year}-${month}-${day}-${lec.subject}`;
        const status = attendance[key];

        subjectCount[lec.subject] =
          (subjectCount[lec.subject] || 0) + 1;
        if (attendance[key] === "present") {
         subjectPresent[lec.subject] =
            (subjectPresent[lec.subject] || 0) + 1;
        }

        const l = document.createElement("div");
        l.className = "lecture";
        l.style.background = lec.color;
        if (status === "present") l.classList.add("present");
        if (status === "absent") l.classList.add("absent");

        l.innerText = lec.subject;
        l.onclick = () => markAttendance(key);
        box.appendChild(l);
      });
    }

    grid.appendChild(box);
  }

  // Render stats
  for (let sub in subjectCount) {
  const percent = Math.round(
    ((subjectPresent[sub] || 0) / subjectCount[sub]) * 100
  );

  statsDiv.innerHTML += `
    <p>
      ${sub}: <strong>${percent}%</strong>
    </p>
  `;
}

}


    // Add lectures
    timetable[weekday]?.forEach(lec => {
      const key = `Day${day}-${lec.subject}`;
const status = attendance[key];

const l = document.createElement("div");
l.className = "lecture";
l.innerText = `${lec.time} ${lec.subject}`;

if (status === "present") l.classList.add("present");
if (status === "absent") l.classList.add("absent");

l.onclick = () => markAttendance(key);

box.appendChild(l);

    });

    grid.appendChild(box);

function renderWeeklyCalendar(dayName, dateStr) {
  const container = document.getElementById("calendarGrid");
  container.innerHTML = "";

  const holiday = holidays.find(h => h.date === dateStr);
  if (holiday) {
    container.innerHTML = `
      <div class="day ${holiday.type}">
        <strong>${holiday.name}</strong><br>
        (${holiday.type} holiday)
      </div>`;
    return;
  }

  const lectures = timetable[dayName] || [];

  lectures.forEach(l => {
    const div = document.createElement("div");
    div.className = "lecture";
    div.style.background = l.color;
    div.innerText = `${l.time} ${l.subject}`;
    container.appendChild(div);
  });
}

function addLecture() {
  let d = new Date(document.getElementById("date").value).getDate();

  lectures.push({
    date: d,
    subject: sub.value,
    room: room.value
  });

  renderCalendar();
}

/* ATTENDANCE */
function renderAttendance() {
  let div = document.getElementById("attendanceList");
  div.innerHTML = "";

  let present = 0;

  lectures.forEach(l => {
    let state = attendance[l.id] || "";
    if (state === "present") present++;

    div.innerHTML += `
      <div class="lecture ${state}">
        ${l.subject}
        <button onclick="mark(${l.id},'present')">P</button>
        <button onclick="mark(${l.id},'absent')">A</button>
      </div>`;
  });

  let percent = lectures.length
    ? Math.round((present / lectures.length) * 100)
    : 100;

  document.getElementById("warning").innerText =
    percent < 75
      ? "⚠ Attendance below 75% (" + percent + "%)"
      : "Attendance: " + percent + "%";
}

function mark(id, state) {
  attendance[id] = state;
  renderAttendance();
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
    by: user.role
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
