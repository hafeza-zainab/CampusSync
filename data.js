const semester = {
  start: "2025-12-08",
  end: "2026-04-15"
};

const holidays = [
  // National
  { date: "2026-01-26", name: "Republic Day", type: "national" },

  // Gazetted
  { date: "2026-03-04", name: "Holi", type: "gazetted" },
  { date: "2026-03-21", name: "Id-ul-Fitr", type: "gazetted" },
  { date: "2026-03-26", name: "Ram Navami", type: "gazetted" },
  { date: "2026-03-31", name: "Mahavir Jayanti", type: "gazetted" },
  { date: "2026-04-03", name: "Good Friday", type: "gazetted" },
  { date: "2026-01-01", name: "New Year", type: "restricted" },
  { date: "2026-04-14", name: "Vaisakhi", type: "restricted" }
];

const timetable = {
  Monday: [
    { time: "07-08", subject: "Hindi", color: "limegreen" },
    { time: "08-09", subject: "OOP C++", color: "gold" },
    { time: "09-10", subject: "Extension Work", color: "plum" }
  ],
  Tuesday: [
    { time: "10-11", subject: "Python", color: "violet" },
    { time: "12-01", subject: "Web Tech", color: "salmon" }
  ],
  Wednesday: [
    { time: "07-08", subject: "EVS", color: "springgreen" },
    { time: "08-09", subject: "DAA", color: "turquoise" }
  ],
  Thursday: [
    { time: "08-09", subject: "OOP C++", color: "gold" },
    { time: "12-01", subject: "Advanced Python", color: "orange" }
  ],
  Friday: [
    { time: "07-08", subject: "EVS", color: "springgreen" },
    { time: "08-09", subject: "Leadership", color: "mediumpurple" }
  ]
};

// Every semester has its own dates and its own subjects. The calendar shows a semester's lectures only
// between its start and end, and a semester that has not started yet is greyed out (no attendance, no stats).
// "semester" and "timetable" above stay as Semester 4 (Vision reads "timetable" from here).
// Semesters 1-3, 5 and 6 are PLACEHOLDERS (dates and subjects): replace them with the real ones.
const LECTURE_COLORS = { A: "gold", B: "violet", C: "turquoise", D: "salmon", E: "springgreen", F: "orange", G: "plum", H: "mediumpurple", I: "limegreen" };
// week("Mon", ...) helper: each day is [[time, subject, colour letter], ...]
function makeWeek(days) {
  const names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], out = {};
  names.forEach((n, i) => { out[n] = days[i].map(([time, subject, c]) => ({ time, subject, color: LECTURE_COLORS[c] })); });
  return out;
}

const semesters = [
  { name: "Semester 1", start: "2024-07-22", end: "2024-11-29", timetable: makeWeek([
    [["07-08", "Mathematics I", "A"], ["08-09", "Physics", "B"]],
    [["08-09", "Programming in C", "C"], ["12-01", "English Communication", "D"]],
    [["07-08", "Digital Electronics", "E"], ["09-10", "Mathematics I", "A"]],
    [["08-09", "Physics", "B"], ["10-11", "Programming in C", "C"]],
    [["07-08", "English Communication", "D"], ["08-09", "Digital Electronics", "E"]] ]) },
  { name: "Semester 2", start: "2024-12-09", end: "2025-04-17", timetable: makeWeek([
    [["07-08", "Mathematics II", "A"], ["08-09", "Data Structures", "B"]],
    [["08-09", "Chemistry", "C"], ["12-01", "Python Basics", "D"]],
    [["07-08", "Engineering Graphics", "E"], ["09-10", "Data Structures", "B"]],
    [["08-09", "Mathematics II", "A"], ["10-11", "Chemistry", "C"]],
    [["07-08", "Python Basics", "D"], ["08-09", "Engineering Graphics", "E"]] ]) },
  { name: "Semester 3", start: "2025-07-21", end: "2025-11-28", timetable: makeWeek([
    [["07-08", "Discrete Mathematics", "A"], ["08-09", "Computer Organization", "B"]],
    [["08-09", "Statistics", "C"], ["12-01", "Linux Lab", "D"]],
    [["07-08", "Technical Writing", "E"], ["09-10", "Discrete Mathematics", "A"]],
    [["08-09", "Computer Organization", "B"], ["10-11", "Statistics", "C"]],
    [["07-08", "Linux Lab", "D"], ["08-09", "Technical Writing", "E"]] ]) },
  { name: "Semester 4", start: semester.start, end: semester.end, timetable: JSON.parse(JSON.stringify(timetable)) },
  { name: "Semester 5", start: "2026-07-20", end: "2026-11-30", timetable: makeWeek([
    [["07-08", "Java", "A"], ["08-09", "DBMS", "B"]],
    [["08-09", "Operating Systems", "C"], ["12-01", "Computer Networks", "D"]],
    [["07-08", "Software Engineering", "E"], ["09-10", "DBMS", "B"]],
    [["08-09", "Java", "A"], ["10-11", "Operating Systems", "C"]],
    [["07-08", "Computer Networks", "D"], ["08-09", "Software Engineering", "E"]] ]) },
  { name: "Semester 6", start: "2026-12-14", end: "2027-04-16", timetable: makeWeek([
    [["07-08", "Machine Learning", "A"], ["08-09", "Cloud Computing", "B"]],
    [["08-09", "Cyber Security", "C"], ["12-01", "Mobile App Development", "D"]],
    [["07-08", "Project Work", "E"], ["09-10", "Machine Learning", "A"]],
    [["08-09", "Cloud Computing", "B"], ["10-11", "Cyber Security", "C"]],
    [["07-08", "Mobile App Development", "D"], ["08-09", "Project Work", "E"]] ]) }
];

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

let lectures = [];


let materials = [];
let announcements = [];
