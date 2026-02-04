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

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

let lectures = [];


let materials = [];
let announcements = [];
