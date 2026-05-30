import React, { useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

const SIDEBAR_ITEMS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "input", label: "Input Data" },
  { id: "generate", label: "Generate" },
  { id: "timetable", label: "Timetable" },
  { id: "analytics", label: "Analytics" },
  { id: "settings", label: "Settings" },
  { id: "about", label: "About" }
];

const INPUT_METHODS = [
  { value: "manual", label: "Manual Entry" },
  { value: "paste", label: "Paste Text" },
  { value: "upload", label: "Upload File" }
];

const ALGORITHMS = [
  { value: "auto", label: "Auto-Select" },
  { value: "greedy", label: "Greedy" },
  { value: "aco", label: "ACO" },
  { value: "pso", label: "PSO" },
  { value: "controller", label: "Controller" }
];

const SAMPLE_SCHOOL_DATA = {
  dataset_name: "Demo University",
  settings: { number_of_days: 5, periods_per_day: 6 },
  courses: [
    {
      course_code: "CSC101",
      course_title: "Data Structures",
      lecturer_id: "LEC001",
      lectures_per_week: 3,
      min_working_days: 2,
      number_of_students: 60,
      department: "Computer Science",
      level: "200"
    },
    {
      course_code: "MAT201",
      course_title: "Linear Algebra",
      lecturer_id: "LEC002",
      lectures_per_week: 2,
      min_working_days: 2,
      number_of_students: 40,
      department: "Mathematics",
      level: "200"
    },
    {
      course_code: "PHY101",
      course_title: "Mechanics",
      lecturer_id: "LEC003",
      lectures_per_week: 2,
      min_working_days: 2,
      number_of_students: 50,
      department: "Physics",
      level: "100"
    },
    {
      course_code: "CSC202",
      course_title: "Algorithms",
      lecturer_id: "LEC001",
      lectures_per_week: 2,
      min_working_days: 2,
      number_of_students: 55,
      department: "Computer Science",
      level: "200"
    },
    {
      course_code: "GST101",
      course_title: "Communication Skills",
      lecturer_id: "LEC002",
      lectures_per_week: 2,
      min_working_days: 2,
      number_of_students: 70,
      department: "General Studies",
      level: "100"
    }
  ],
  lecturers: [
    { lecturer_id: "LEC001", lecturer_name: "Dr. Adaeze" },
    { lecturer_id: "LEC002", lecturer_name: "Dr. Bello" },
    { lecturer_id: "LEC003", lecturer_name: "Dr. Chinedu" }
  ],
  rooms: [
    { room_id: "R-A1", room_name: "Main Hall", capacity: 120 },
    { room_id: "R-B2", room_name: "Science Lab", capacity: 80 },
    { room_id: "R-C3", room_name: "Engineering Room", capacity: 60 }
  ],
  curricula: [
    {
      curriculum_id: "CURR-CS-200",
      curriculum_name: "Computer Science 200",
      course_codes: "CSC101, CSC202, MAT201"
    },
    {
      curriculum_id: "CURR-FY-100",
      curriculum_name: "First Year Core",
      course_codes: "PHY101, GST101"
    }
  ],
  unavailability_constraints: [
    { course_code: "CSC101", day: 0, period: 0 },
    { course_code: "MAT201", day: 2, period: 1 },
    { course_code: "PHY101", day: 3, period: 3 },
    { course_code: "CSC202", day: 1, period: 4 },
    { course_code: "GST101", day: 4, period: 2 }
  ]
};

function newCourse() {
  return {
    course_code: "",
    course_title: "",
    lecturer_id: "",
    lectures_per_week: 1,
    min_working_days: 1,
    number_of_students: 1,
    department: "",
    level: ""
  };
}

function newLecturer() {
  return { lecturer_id: "", lecturer_name: "" };
}

function newRoom() {
  return { room_id: "", room_name: "", capacity: 1 };
}

function newCurriculum() {
  return { curriculum_id: "", curriculum_name: "", course_codes: "" };
}

function newUnavailability() {
  return { course_code: "", day: 0, period: 0 };
}

function toNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function parseCourseCodes(text) {
  return String(text)
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

export default function App() {
  const [activeSection, setActiveSection] = useState("dashboard");
  const [algorithm, setAlgorithm] = useState("auto");
  const [inputMethod, setInputMethod] = useState("manual");
  const [file, setFile] = useState(null);
  const [rawText, setRawText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const [datasetName, setDatasetName] = useState("My University");
  const [settings, setSettings] = useState({
    number_of_days: 5,
    periods_per_day: 6
  });
  const [courses, setCourses] = useState([]);
  const [lecturers, setLecturers] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [curricula, setCurricula] = useState([]);
  const [unavailability, setUnavailability] = useState([]);

  const [courseDraft, setCourseDraft] = useState(newCourse());
  const [lecturerDraft, setLecturerDraft] = useState(newLecturer());
  const [roomDraft, setRoomDraft] = useState(newRoom());
  const [curriculumDraft, setCurriculumDraft] = useState(newCurriculum());
  const [unavailabilityDraft, setUnavailabilityDraft] = useState(newUnavailability());

  const backendAlgorithm = algorithm === "auto" ? "controller" : algorithm;

  const filteredCourses = useMemo(
    () => courses.filter((row) => row.course_code.trim().length > 0),
    [courses]
  );
  const filteredLecturers = useMemo(
    () => lecturers.filter((row) => row.lecturer_id.trim().length > 0),
    [lecturers]
  );
  const filteredRooms = useMemo(
    () => rooms.filter((row) => row.room_id.trim().length > 0),
    [rooms]
  );
  const filteredCurricula = useMemo(
    () => curricula.filter((row) => row.curriculum_id.trim().length > 0),
    [curricula]
  );
  const filteredUnavailability = useMemo(
    () => unavailability.filter((row) => row.course_code.trim().length > 0),
    [unavailability]
  );

  const courseCodeOptions = useMemo(
    () => filteredCourses.map((row) => row.course_code.trim()),
    [filteredCourses]
  );

  const summary = useMemo(() => {
    const totalCourses = filteredCourses.length;
    const totalLectures = filteredCourses.reduce(
      (acc, row) => acc + Math.max(0, toNumber(row.lectures_per_week, 0)),
      0
    );
    const totalStudents = filteredCourses.reduce(
      (acc, row) => acc + Math.max(0, toNumber(row.number_of_students, 0)),
      0
    );
    const departments = new Set(
      filteredCourses
        .map((row) => row.department.trim())
        .filter((name) => name.length > 0)
    );
    const levels = new Set(
      filteredCourses.map((row) => row.level.trim()).filter((name) => name.length > 0)
    );
    return {
      totalCourses,
      totalLectures,
      totalStudents,
      departments: departments.size,
      levels: levels.size
    };
  }, [filteredCourses]);

  const detectionLabel = useMemo(() => {
    if (inputMethod === "manual") {
      return "Manual data detected";
    }
    if (inputMethod === "paste") {
      return rawText.trim().length > 0
        ? "Pasted data detected"
        : "Waiting for pasted data";
    }
    return file ? "Uploaded file detected" : "Waiting for uploaded file";
  }, [inputMethod, rawText, file]);

  const strategyText = useMemo(() => {
    if (algorithm === "auto") {
      return "Hybrid (ACO + PSO)";
    }
    if (algorithm === "controller") {
      return "Adaptive Controller";
    }
    if (algorithm === "aco") {
      return "Ant Colony Search";
    }
    if (algorithm === "pso") {
      return "Particle Swarm Search";
    }
    return "Greedy Constructor";
  }, [algorithm]);

  const focusText = useMemo(() => {
    if (algorithm === "auto" || algorithm === "controller") {
      return "Balanced";
    }
    if (algorithm === "greedy") {
      return "Fast Initialization";
    }
    return "Quality Refinement";
  }, [algorithm]);

  const canRun = useMemo(() => {
    if (inputMethod === "manual") {
      return (
        filteredCourses.length > 0 &&
        filteredRooms.length > 0 &&
        Math.max(1, toNumber(settings.number_of_days, 1)) > 0 &&
        Math.max(1, toNumber(settings.periods_per_day, 1)) > 0
      );
    }
    if (inputMethod === "paste") {
      return rawText.trim().length > 0;
    }
    return Boolean(file);
  }, [inputMethod, filteredCourses.length, filteredRooms.length, rawText, file, settings]);

  const downloadHref = result?.download_url ? `${API_BASE}${result.download_url}` : "";
  const selectedHeuristics = result?.selected_heuristics || [];
  const convergence = result?.convergence_history || [];
  const statusText = loading
    ? "Optimizing..."
    : error
      ? "Error"
      : result
        ? "Timetable Generated"
        : "System Ready";

  function updateRow(setter, index, field, value) {
    setter((prev) =>
      prev.map((row, rowIndex) =>
        rowIndex === index ? { ...row, [field]: value } : row
      )
    );
  }

  function removeRow(setter, index) {
    setter((prev) => prev.filter((_, rowIndex) => rowIndex !== index));
  }

  function loadSampleSchoolData() {
    setDatasetName(SAMPLE_SCHOOL_DATA.dataset_name);
    setSettings({ ...SAMPLE_SCHOOL_DATA.settings });
    setCourses(SAMPLE_SCHOOL_DATA.courses.map((row) => ({ ...row })));
    setLecturers(SAMPLE_SCHOOL_DATA.lecturers.map((row) => ({ ...row })));
    setRooms(SAMPLE_SCHOOL_DATA.rooms.map((row) => ({ ...row })));
    setCurricula(SAMPLE_SCHOOL_DATA.curricula.map((row) => ({ ...row })));
    setUnavailability(
      SAMPLE_SCHOOL_DATA.unavailability_constraints.map((row) => ({ ...row }))
    );
    setInputMethod("manual");
    setActiveSection("input");
    setError("");
  }

  function addCourseRow() {
    setCourses((prev) => [...prev, { ...courseDraft }]);
    setCourseDraft(newCourse());
  }

  function addLecturerRow() {
    setLecturers((prev) => [...prev, { ...lecturerDraft }]);
    setLecturerDraft(newLecturer());
  }

  function addRoomRow() {
    setRooms((prev) => [...prev, { ...roomDraft }]);
    setRoomDraft(newRoom());
  }

  function addCurriculumRow() {
    setCurricula((prev) => [...prev, { ...curriculumDraft }]);
    setCurriculumDraft(newCurriculum());
  }

  function addUnavailabilityRow() {
    setUnavailability((prev) => [...prev, { ...unavailabilityDraft }]);
    setUnavailabilityDraft(newUnavailability());
  }

  async function handleRunOptimization(event) {
    if (event) {
      event.preventDefault();
    }
    if (!canRun) {
      setError("Provide input data before running optimization.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      let response;
      if (inputMethod === "manual") {
        const payload = {
          dataset_name: datasetName || "Manual_Dataset",
          algorithm: backendAlgorithm,
          settings: {
            number_of_days: Math.max(1, toNumber(settings.number_of_days, 1)),
            periods_per_day: Math.max(1, toNumber(settings.periods_per_day, 1))
          },
          courses: filteredCourses.map((row) => ({
            ...row,
            lectures_per_week: Math.max(1, toNumber(row.lectures_per_week, 1)),
            min_working_days: Math.max(1, toNumber(row.min_working_days, 1)),
            number_of_students: Math.max(1, toNumber(row.number_of_students, 1))
          })),
          lecturers: filteredLecturers,
          rooms: filteredRooms.map((row) => ({
            ...row,
            capacity: Math.max(1, toNumber(row.capacity, 1))
          })),
          curricula: filteredCurricula.map((row) => ({
            curriculum_id: row.curriculum_id,
            curriculum_name: row.curriculum_name,
            selected_course_codes: parseCourseCodes(row.course_codes)
          })),
          unavailability_constraints: filteredUnavailability.map((row) => ({
            course_code: row.course_code,
            day: Math.max(0, toNumber(row.day, 0)),
            period: Math.max(0, toNumber(row.period, 0))
          }))
        };

        response = await fetch(`${API_BASE}/optimize-school-data`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      } else {
        const formData = new FormData();
        formData.append("algorithm", backendAlgorithm);
        if (inputMethod === "upload" && file) {
          formData.append("file", file);
        } else {
          formData.append("raw_text", rawText);
        }
        response = await fetch(`${API_BASE}/optimize`, {
          method: "POST",
          body: formData
        });
      }

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Optimization failed.");
      }
      setResult(payload);
      setActiveSection("timetable");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error.");
    } finally {
      setLoading(false);
    }
  }

  function renderInputSection() {
    return (
      <section className="glass-card section-card">
        <div className="section-header">
          <div>
            <h3>Timetable Information</h3>
            <p>Provide scheduling details below. One system accepts manual, pasted, and uploaded data.</p>
          </div>
          <div className="section-actions">
            <button type="button" className="ghost-btn" onClick={loadSampleSchoolData}>
              Load Sample School Data
            </button>
            <button type="button" className="ghost-btn">Auto-Detect</button>
            <span className="detect-badge">{detectionLabel}</span>
          </div>
        </div>

        <div className="settings-row">
          <label className="field">
            Dataset Name
            <input
              type="text"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
            />
          </label>
          <label className="field">
            Academic Days
            <input
              type="number"
              min={1}
              value={settings.number_of_days}
              onChange={(e) =>
                setSettings((prev) => ({
                  ...prev,
                  number_of_days: e.target.value
                }))
              }
            />
          </label>
          <label className="field">
            Periods Per Day
            <input
              type="number"
              min={1}
              value={settings.periods_per_day}
              onChange={(e) =>
                setSettings((prev) => ({
                  ...prev,
                  periods_per_day: e.target.value
                }))
              }
            />
          </label>
        </div>

        <div className="method-tabs">
          {INPUT_METHODS.map((method) => (
            <button
              key={method.value}
              type="button"
              className={inputMethod === method.value ? "method-tab active" : "method-tab"}
              onClick={() => setInputMethod(method.value)}
            >
              {method.label}
            </button>
          ))}
        </div>

        {inputMethod === "manual" && (
          <div className="manual-grid">
            <div className="subcard">
              <h4>Courses</h4>
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Course Code</th>
                      <th>Course Title</th>
                      <th>Lecturer</th>
                      <th>Lectures/Week</th>
                      <th>Min Days</th>
                      <th>Students</th>
                      <th>Department</th>
                      <th>Level</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {courses.map((row, idx) => (
                      <tr key={`course-${idx}`}>
                        <td><input value={row.course_code} onChange={(e) => updateRow(setCourses, idx, "course_code", e.target.value)} /></td>
                        <td><input value={row.course_title} onChange={(e) => updateRow(setCourses, idx, "course_title", e.target.value)} /></td>
                        <td><input value={row.lecturer_id} onChange={(e) => updateRow(setCourses, idx, "lecturer_id", e.target.value)} /></td>
                        <td><input type="number" min={1} value={row.lectures_per_week} onChange={(e) => updateRow(setCourses, idx, "lectures_per_week", e.target.value)} /></td>
                        <td><input type="number" min={1} value={row.min_working_days} onChange={(e) => updateRow(setCourses, idx, "min_working_days", e.target.value)} /></td>
                        <td><input type="number" min={1} value={row.number_of_students} onChange={(e) => updateRow(setCourses, idx, "number_of_students", e.target.value)} /></td>
                        <td><input value={row.department} onChange={(e) => updateRow(setCourses, idx, "department", e.target.value)} /></td>
                        <td><input value={row.level} onChange={(e) => updateRow(setCourses, idx, "level", e.target.value)} /></td>
                        <td><button type="button" className="icon-btn" onClick={() => removeRow(setCourses, idx)}>×</button></td>
                      </tr>
                    ))}
                    <tr className="draft-row">
                      <td><input placeholder="CSC101" value={courseDraft.course_code} onChange={(e) => setCourseDraft((prev) => ({ ...prev, course_code: e.target.value }))} /></td>
                      <td><input placeholder="Data Structures" value={courseDraft.course_title} onChange={(e) => setCourseDraft((prev) => ({ ...prev, course_title: e.target.value }))} /></td>
                      <td><input placeholder="LEC001" value={courseDraft.lecturer_id} onChange={(e) => setCourseDraft((prev) => ({ ...prev, lecturer_id: e.target.value }))} /></td>
                      <td><input type="number" min={1} value={courseDraft.lectures_per_week} onChange={(e) => setCourseDraft((prev) => ({ ...prev, lectures_per_week: e.target.value }))} /></td>
                      <td><input type="number" min={1} value={courseDraft.min_working_days} onChange={(e) => setCourseDraft((prev) => ({ ...prev, min_working_days: e.target.value }))} /></td>
                      <td><input type="number" min={1} value={courseDraft.number_of_students} onChange={(e) => setCourseDraft((prev) => ({ ...prev, number_of_students: e.target.value }))} /></td>
                      <td><input placeholder="Computer Science" value={courseDraft.department} onChange={(e) => setCourseDraft((prev) => ({ ...prev, department: e.target.value }))} /></td>
                      <td><input placeholder="200" value={courseDraft.level} onChange={(e) => setCourseDraft((prev) => ({ ...prev, level: e.target.value }))} /></td>
                      <td><button type="button" className="icon-btn add" onClick={addCourseRow}>+</button></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div className="two-column">
              <div className="subcard">
                <h4>Lecturers</h4>
                <div className="table-scroll">
                  <table className="data-table compact">
                    <thead>
                      <tr>
                        <th>Lecturer ID</th>
                        <th>Lecturer Name</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {lecturers.map((row, idx) => (
                        <tr key={`lec-${idx}`}>
                          <td><input value={row.lecturer_id} onChange={(e) => updateRow(setLecturers, idx, "lecturer_id", e.target.value)} /></td>
                          <td><input value={row.lecturer_name} onChange={(e) => updateRow(setLecturers, idx, "lecturer_name", e.target.value)} /></td>
                          <td><button type="button" className="icon-btn" onClick={() => removeRow(setLecturers, idx)}>×</button></td>
                        </tr>
                      ))}
                      <tr className="draft-row">
                        <td><input placeholder="LEC001" value={lecturerDraft.lecturer_id} onChange={(e) => setLecturerDraft((prev) => ({ ...prev, lecturer_id: e.target.value }))} /></td>
                        <td><input placeholder="Dr. Name" value={lecturerDraft.lecturer_name} onChange={(e) => setLecturerDraft((prev) => ({ ...prev, lecturer_name: e.target.value }))} /></td>
                        <td><button type="button" className="icon-btn add" onClick={addLecturerRow}>+</button></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="subcard">
                <h4>Rooms</h4>
                <div className="table-scroll">
                  <table className="data-table compact">
                    <thead>
                      <tr>
                        <th>Room ID</th>
                        <th>Room Name</th>
                        <th>Capacity</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {rooms.map((row, idx) => (
                        <tr key={`room-${idx}`}>
                          <td><input value={row.room_id} onChange={(e) => updateRow(setRooms, idx, "room_id", e.target.value)} /></td>
                          <td><input value={row.room_name} onChange={(e) => updateRow(setRooms, idx, "room_name", e.target.value)} /></td>
                          <td><input type="number" min={1} value={row.capacity} onChange={(e) => updateRow(setRooms, idx, "capacity", e.target.value)} /></td>
                          <td><button type="button" className="icon-btn" onClick={() => removeRow(setRooms, idx)}>×</button></td>
                        </tr>
                      ))}
                      <tr className="draft-row">
                        <td><input placeholder="R-A1" value={roomDraft.room_id} onChange={(e) => setRoomDraft((prev) => ({ ...prev, room_id: e.target.value }))} /></td>
                        <td><input placeholder="Main Hall" value={roomDraft.room_name} onChange={(e) => setRoomDraft((prev) => ({ ...prev, room_name: e.target.value }))} /></td>
                        <td><input type="number" min={1} value={roomDraft.capacity} onChange={(e) => setRoomDraft((prev) => ({ ...prev, capacity: e.target.value }))} /></td>
                        <td><button type="button" className="icon-btn add" onClick={addRoomRow}>+</button></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className="two-column">
              <div className="subcard">
                <h4>Curricula / Student Groups</h4>
                <div className="table-scroll">
                  <table className="data-table compact">
                    <thead>
                      <tr>
                        <th>Curriculum ID</th>
                        <th>Curriculum Name</th>
                        <th>Course Codes</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {curricula.map((row, idx) => (
                        <tr key={`curr-${idx}`}>
                          <td><input value={row.curriculum_id} onChange={(e) => updateRow(setCurricula, idx, "curriculum_id", e.target.value)} /></td>
                          <td><input value={row.curriculum_name} onChange={(e) => updateRow(setCurricula, idx, "curriculum_name", e.target.value)} /></td>
                          <td><input placeholder="CSC101, MAT201" value={row.course_codes} onChange={(e) => updateRow(setCurricula, idx, "course_codes", e.target.value)} /></td>
                          <td><button type="button" className="icon-btn" onClick={() => removeRow(setCurricula, idx)}>×</button></td>
                        </tr>
                      ))}
                      <tr className="draft-row">
                        <td><input placeholder="CURR-CS-200" value={curriculumDraft.curriculum_id} onChange={(e) => setCurriculumDraft((prev) => ({ ...prev, curriculum_id: e.target.value }))} /></td>
                        <td><input placeholder="CS 200" value={curriculumDraft.curriculum_name} onChange={(e) => setCurriculumDraft((prev) => ({ ...prev, curriculum_name: e.target.value }))} /></td>
                        <td><input placeholder="CSC101, CSC202" value={curriculumDraft.course_codes} onChange={(e) => setCurriculumDraft((prev) => ({ ...prev, course_codes: e.target.value }))} /></td>
                        <td><button type="button" className="icon-btn add" onClick={addCurriculumRow}>+</button></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="subcard">
                <h4>Unavailability</h4>
                <div className="table-scroll">
                  <table className="data-table compact">
                    <thead>
                      <tr>
                        <th>Course Code</th>
                        <th>Day</th>
                        <th>Period</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {unavailability.map((row, idx) => (
                        <tr key={`un-${idx}`}>
                          <td>
                            <input
                              list="course-codes"
                              value={row.course_code}
                              onChange={(e) => updateRow(setUnavailability, idx, "course_code", e.target.value)}
                            />
                          </td>
                          <td><input type="number" min={0} value={row.day} onChange={(e) => updateRow(setUnavailability, idx, "day", e.target.value)} /></td>
                          <td><input type="number" min={0} value={row.period} onChange={(e) => updateRow(setUnavailability, idx, "period", e.target.value)} /></td>
                          <td><button type="button" className="icon-btn" onClick={() => removeRow(setUnavailability, idx)}>×</button></td>
                        </tr>
                      ))}
                      <tr className="draft-row">
                        <td>
                          <input
                            list="course-codes"
                            placeholder="CSC101"
                            value={unavailabilityDraft.course_code}
                            onChange={(e) => setUnavailabilityDraft((prev) => ({ ...prev, course_code: e.target.value }))}
                          />
                        </td>
                        <td><input type="number" min={0} value={unavailabilityDraft.day} onChange={(e) => setUnavailabilityDraft((prev) => ({ ...prev, day: e.target.value }))} /></td>
                        <td><input type="number" min={0} value={unavailabilityDraft.period} onChange={(e) => setUnavailabilityDraft((prev) => ({ ...prev, period: e.target.value }))} /></td>
                        <td><button type="button" className="icon-btn add" onClick={addUnavailabilityRow}>+</button></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <datalist id="course-codes">
                  {courseCodeOptions.map((code) => (
                    <option key={code} value={code} />
                  ))}
                </datalist>
              </div>
            </div>
          </div>
        )}

        {inputMethod === "paste" && (
          <div className="subcard">
            <h4>Paste Raw Dataset Text</h4>
            <textarea
              rows={14}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="Paste ITC dataset content here..."
            />
          </div>
        )}

        {inputMethod === "upload" && (
          <div className="subcard upload-card">
            <h4>Upload Dataset File</h4>
            <p>Select ITC `.txt` or Excel `.xlsx` input file.</p>
            <input
              type="file"
              accept=".txt,.xlsx,text/plain,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <p className="upload-name">{file ? `Selected: ${file.name}` : "No file selected"}</p>
            <p className="upload-name">Supported: ITC `.txt` and Excel `.xlsx`.</p>
          </div>
        )}

        <div className="footer-row">
          <button
            type="button"
            className="generate-btn"
            disabled={loading || !canRun}
            onClick={handleRunOptimization}
          >
            {loading ? "Optimizing..." : "Generate Timetable"}
          </button>
        </div>
      </section>
    );
  }

  function renderDashboardSection() {
    return (
      <section className="glass-card section-card">
        <div className="section-header">
          <div>
            <h3>Dashboard</h3>
            <p>Overview and quick control for your smart scheduling system.</p>
          </div>
        </div>
        <div className="welcome-banner">
          <h4>One System. Any Data. Smarter Timetables.</h4>
          <p>Load data quickly, preview strategy, and generate timetables with adaptive optimization.</p>
        </div>
        <div className="metric-grid">
          <article className="metric-card"><span>Total Courses</span><strong>{summary.totalCourses}</strong></article>
          <article className="metric-card"><span>Total Lectures</span><strong>{summary.totalLectures}</strong></article>
          <article className="metric-card"><span>Total Students</span><strong>{summary.totalStudents}</strong></article>
          <article className="metric-card"><span>Departments</span><strong>{summary.departments}</strong></article>
          <article className="metric-card"><span>Levels</span><strong>{summary.levels}</strong></article>
          <article className="metric-card"><span>Status</span><strong>{statusText}</strong></article>
        </div>
        <div className="quick-actions">
          <button type="button" className="ghost-btn" onClick={loadSampleSchoolData}>
            Load Sample School Data
          </button>
          <button type="button" className="ghost-btn" onClick={() => setActiveSection("input")}>
            Go to Input Data
          </button>
          <button type="button" className="ghost-btn" onClick={() => setActiveSection("generate")}>
            Open Generate Panel
          </button>
        </div>
        <button
          type="button"
          className="generate-btn dashboard-cta"
          disabled={loading || !canRun}
          onClick={handleRunOptimization}
        >
          {loading ? "Optimizing..." : "Generate Timetable"}
        </button>
      </section>
    );
  }

  function renderGenerateSection() {
    return (
      <section className="glass-card section-card">
        <div className="section-header">
          <div>
            <h3>Generate</h3>
            <p>Select optimization strategy and launch timetable generation.</p>
          </div>
        </div>
        <div className="two-column">
          <div className="subcard">
            <h4>Algorithm Selector</h4>
            <label className="field">
              Algorithm
              <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value)}>
                {ALGORITHMS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="subcard">
            <h4>Optimization Preview</h4>
            <div className="preview-items">
              <div><span>Algorithm</span><strong>{ALGORITHMS.find((a) => a.value === algorithm)?.label || "Auto-Select"}</strong></div>
              <div><span>Strategy</span><strong>{strategyText}</strong></div>
              <div><span>Focus</span><strong>{focusText}</strong></div>
            </div>
          </div>
        </div>
        <button
          type="button"
          className="generate-btn"
          disabled={loading || !canRun}
          onClick={handleRunOptimization}
        >
          {loading ? "Optimizing..." : "Generate Timetable"}
        </button>
      </section>
    );
  }

  function renderTimetableSection() {
    if (!result) {
      return (
        <section className="glass-card section-card empty-state">
          <h3>Timetable</h3>
          <p>No timetable generated yet.</p>
        </section>
      );
    }
    return (
      <section className="glass-card section-card">
        <div className="section-header">
          <div>
            <h3>Timetable</h3>
            <p>Generated timetable output and downloadable export.</p>
          </div>
        </div>
        <div className="result-actions">
          {downloadHref && (
            <a className="download-btn" href={downloadHref} target="_blank" rel="noreferrer">
              Download Generated Timetable CSV
            </a>
          )}
          <span className="dataset-label">Dataset: {result.dataset_name}</span>
        </div>
        {selectedHeuristics.length > 0 && (
          <div className="heuristics-history">
            Controller Selection History: {selectedHeuristics.join(" → ")}
          </div>
        )}
      </section>
    );
  }

  function renderAnalyticsSection() {
    if (!result) {
      return (
        <section className="glass-card section-card empty-state">
          <h3>Analytics</h3>
          <p>No analytics yet. Generate a timetable first.</p>
        </section>
      );
    }
    return (
      <section className="glass-card section-card">
        <div className="section-header">
          <div>
            <h3>Analytics</h3>
            <p>Optimization metrics and convergence history.</p>
          </div>
        </div>
        <div className="metric-grid">
          <article className="metric-card"><span>Final Fitness</span><strong>{result.final_fitness}</strong></article>
          <article className="metric-card"><span>Hard Violations</span><strong>{result.hard_violations}</strong></article>
          <article className="metric-card"><span>Soft Penalty</span><strong>{result.soft_penalty}</strong></article>
          <article className="metric-card"><span>Runtime</span><strong>{result.runtime_seconds}s</strong></article>
          <article className="metric-card"><span>Scheduled</span><strong>{result.scheduled_lectures}</strong></article>
          <article className="metric-card"><span>Total</span><strong>{result.total_lectures}</strong></article>
        </div>
        <div className="subcard">
          <h4>Convergence History</h4>
          <div className="table-scroll">
            <table className="data-table compact">
              <thead>
                <tr>
                  <th>Iteration</th>
                  <th>Fitness</th>
                </tr>
              </thead>
              <tbody>
                {convergence.map((value, idx) => (
                  <tr key={`${idx}-${value}`}>
                    <td>{idx + 1}</td>
                    <td>{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    );
  }

  function renderSettingsSection() {
    return (
      <section className="glass-card section-card">
        <div className="section-header">
          <div>
            <h3>Settings</h3>
            <p>System preferences for timetable generation.</p>
          </div>
        </div>
        <div className="two-column">
          <div className="subcard">
            <label className="field">
              Default Algorithm
              <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value)}>
                {ALGORITHMS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Academic Days
              <input
                type="number"
                min={1}
                value={settings.number_of_days}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    number_of_days: e.target.value
                  }))
                }
              />
            </label>
            <label className="field">
              Periods Per Day
              <input
                type="number"
                min={1}
                value={settings.periods_per_day}
                onChange={(e) =>
                  setSettings((prev) => ({
                    ...prev,
                    periods_per_day: e.target.value
                  }))
                }
              />
            </label>
          </div>
          <div className="subcard">
            <h4>Theme</h4>
            <p>Dark Navy Dashboard (active)</p>
            <h4>Status</h4>
            <p>{statusText}</p>
          </div>
        </div>
      </section>
    );
  }

  function renderAboutSection() {
    return (
      <section className="glass-card section-card">
        <h3>About</h3>
        <p>
          Selection Hyper-Heuristic Timetabling System using Ant Colony Optimization (ACO)
          and Particle Swarm Optimization (PSO). The controller adaptively selects heuristics
          based on current timetable state and recent optimization performance.
        </p>
      </section>
    );
  }

  function renderActiveSection() {
    if (activeSection === "dashboard") {
      return renderDashboardSection();
    }
    if (activeSection === "input") {
      return renderInputSection();
    }
    if (activeSection === "generate") {
      return renderGenerateSection();
    }
    if (activeSection === "timetable") {
      return renderTimetableSection();
    }
    if (activeSection === "analytics") {
      return renderAnalyticsSection();
    }
    if (activeSection === "settings") {
      return renderSettingsSection();
    }
    return renderAboutSection();
  }

  return (
    <div className="dashboard-shell">
      <aside className="sidebar glass-card">
        <div className="brand">
          <div className="brand-logo">T</div>
          <div>
            <h1>Timetable Optimizer</h1>
            <p>Smart Scheduling for Universities</p>
          </div>
        </div>
        <nav className="sidebar-nav">
          {SIDEBAR_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={activeSection === item.id ? "nav-item active" : "nav-item"}
              onClick={() => setActiveSection(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-status">
          <span className={`status-dot ${loading ? "loading" : result ? "done" : "ready"}`} />
          <span>{statusText}</span>
        </div>
      </aside>

      <main className="main-content">
        <header className="top-header glass-card">
          <div>
            <h2>One System. Any Data. Smarter Timetables.</h2>
            <p>Enter your data and let the system handle the optimization.</p>
          </div>
          <span className="version-pill">v1.0.0</span>
        </header>

        <section className={`glass-card status-card ${loading ? "optimizing" : result ? "generated" : error ? "error" : "ready"}`}>
          <strong>{statusText}</strong>
          {!loading && !error && !result && <span>System is ready for optimization.</span>}
          {loading && <span>Please wait while the optimizer is running.</span>}
          {result && <span>Latest result is available in Timetable and Analytics sections.</span>}
          {error && <span>{error}</span>}
        </section>

        {renderActiveSection()}
      </main>

      <aside className="right-panel">
        <section className="glass-card side-card">
          <h3>System Summary</h3>
          <div className="summary-list">
            <div><span>Total Courses</span><strong>{summary.totalCourses}</strong></div>
            <div><span>Total Lectures</span><strong>{summary.totalLectures}</strong></div>
            <div><span>Total Students</span><strong>{summary.totalStudents}</strong></div>
            <div><span>Departments</span><strong>{summary.departments}</strong></div>
            <div><span>Levels</span><strong>{summary.levels}</strong></div>
          </div>
        </section>

        <section className="glass-card side-card">
          <h3>Optimization Preview</h3>
          <div className="preview-items">
            <div>
              <span>Algorithm</span>
              <strong>{ALGORITHMS.find((a) => a.value === algorithm)?.label || "Auto-Select"}</strong>
            </div>
            <div>
              <span>Strategy</span>
              <strong>{strategyText}</strong>
            </div>
            <div>
              <span>Focus</span>
              <strong>{focusText}</strong>
            </div>
          </div>
        </section>
      </aside>
    </div>
  );
}
