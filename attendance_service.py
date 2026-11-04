"""Validated local attendance data and CRUD operations (no GUI dependency)."""
from __future__ import annotations
import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path

STATUSES = ('Present', 'Late', 'Absent', 'Excused')
SAMPLE_STUDENTS = [
    ('2026-0001', 'Alex Rivera'), ('2026-0002', 'Jamie Santos'),
    ('2026-0003', 'Morgan Cruz'), ('2026-0004', 'Taylor Reyes'),
    ('2026-0005', 'Casey Mendoza'), ('2026-0006', 'Jordan Lim'),
    ('2026-0007', 'Sam Navarro'), ('2026-0008', 'Riley Garcia'),
    ('2026-0009', 'Avery Ramos'), ('2026-0010', 'Drew Aquino'),
    ('2026-0011', 'Robin Flores'), ('2026-0012', 'Skyler Bautista'),
    ('2026-0013', 'Parker Villanueva'), ('2026-0014', 'Quinn Dela Cruz'),
    ('2026-0015', 'Cameron Tan'), ('2026-0016', 'Emery Torres'),
]

class AttendanceError(ValueError):
    pass


def valid_day(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise AttendanceError('Date must use YYYY-MM-DD.') from None


def new_data() -> dict:
    return {'students': [{'id': sid, 'name': name} for sid, name in SAMPLE_STUDENTS], 'attendance': {}}


class AttendanceStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            data = new_data()
            self._write(data)
            return data
        try:
            with self.path.open('r', encoding='utf-8') as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise AttendanceError(f'Cannot read attendance file: {exc}. Back it up before modifying it.') from exc
        if not isinstance(data, dict) or not isinstance(data.get('students'), list) or not isinstance(data.get('attendance'), dict):
            raise AttendanceError('The saved file is not a valid attendance database.')
        ids = [s.get('id') for s in data['students'] if isinstance(s, dict)]
        if len(ids) != len(data['students']) or len(ids) != len(set(ids)) or not all(isinstance(s.get('name'), str) for s in data['students']):
            raise AttendanceError('The saved student records are invalid or contain duplicate IDs.')
        return data

    def _write(self, data: dict):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent, suffix='.tmp', delete=False) as fh:
                temp_path = Path(fh.name)
                json.dump(data, fh, indent=2, ensure_ascii=False)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(temp_path, self.path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()

    def _save(self):
        self._write(self.data)

    def students(self, search: str = '') -> list[dict]:
        term = search.strip().casefold()
        matches = [s for s in self.data['students'] if not term or term in s['id'].casefold() or term in s['name'].casefold()]
        if term:
            matches.sort(key=lambda s: (not s['id'].casefold().startswith(term), not s['name'].casefold().startswith(term), s['id']))
        else:
            matches.sort(key=lambda s: s['id'])
        return matches

    def add_student(self, student_id: str, name: str):
        student_id, name = student_id.strip().upper(), ' '.join(name.split())
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9-]{2,24}', student_id):
            raise AttendanceError('Student ID must be 3–25 letters, numbers or hyphens.')
        if len(name) < 2 or len(name) > 80:
            raise AttendanceError('Enter a student name between 2 and 80 characters.')
        if any(s['id'].upper() == student_id for s in self.data['students']):
            raise AttendanceError(f'Student ID {student_id} already exists.')
        self.data['students'].append({'id': student_id, 'name': name})
        self._save()

    def update_student(self, student_id: str, name: str):
        name = ' '.join(name.split())
        if not 2 <= len(name) <= 80:
            raise AttendanceError('Enter a student name between 2 and 80 characters.')
        student = self._student(student_id)
        student['name'] = name
        self._save()

    def _student(self, student_id: str) -> dict:
        student = next((s for s in self.data['students'] if s['id'] == student_id), None)
        if student is None:
            raise AttendanceError('Student ID not found.')
        return student

    def remove_student(self, student_id: str):
        self._student(student_id)
        self.data['students'] = [s for s in self.data['students'] if s['id'] != student_id]
        for day_records in self.data['attendance'].values():
            day_records.pop(student_id, None)
        self._save()

    def mark(self, day: str, student_id: str, status: str):
        valid_day(day)
        self._student(student_id)
        if status not in STATUSES:
            raise AttendanceError('Choose a valid attendance status.')
        self.data['attendance'].setdefault(day, {})[student_id] = status
        self._save()

    def clear_mark(self, day: str, student_id: str):
        valid_day(day)
        self._student(student_id)
        self.data['attendance'].get(day, {}).pop(student_id, None)
        self._save()

    def status(self, day: str, student_id: str) -> str:
        valid_day(day)
        return self.data['attendance'].get(day, {}).get(student_id, 'Not Marked')

    def summary(self, day: str) -> dict:
        valid_day(day)
        counts = {status: 0 for status in (*STATUSES, 'Not Marked')}
        for student in self.data['students']:
            counts[self.status(day, student['id'])] += 1
        return counts
