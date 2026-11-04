# Classroom Attendance Monitoring System

A simple offline Python Tkinter application for classroom attendance. Students are located primarily by **Student ID** and secondarily by **name**. The program starts with **16 fictional sample students** on the first run.

## Features

- Search by ID or name (ID prefix matches are prioritized)
- Register, rename, and delete students
- Mark **Present**, **Late**, **Absent**, or **Excused** for any valid class date
- Display **Not Marked** for students whose attendance has not yet been recorded
- Prevent duplicate student IDs and overwrite an existing date's mark rather than duplicate it
- Attendance summary and full-class CSV export for the selected date
- Save data in `data/attendance.json` using an atomic file replacement
- Works offline without third-party libraries

## Run

Requires Python 3.10 or newer and Tkinter (typically included with Windows Python).

```powershell
git clone https://github.com/irincovictor-cmd/py-project-8.git
cd py-project-8
python main.py
```

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Data and privacy

- `data/attendance.json` is created automatically on the first launch, with fictional example students.
- The `data/` folder is ignored by Git so class records are not accidentally committed.
- **Do not delete** `data/attendance.json` when updating the program; it holds your student records and attendance history.
- CSV exports are user-selected files and should be handled as classroom records.
- This prototype is an offline, single-computer app, not a secured networked student information system.
