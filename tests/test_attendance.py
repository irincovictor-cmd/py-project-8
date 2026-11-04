import tempfile
import unittest
from pathlib import Path
from attendance_service import AttendanceStore, AttendanceError, SAMPLE_STUDENTS

DAY = '2026-11-04'


class AttendanceStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'data' / 'attendance.json'
        self.store = AttendanceStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_initial_samples(self):
        self.assertEqual(len(self.store.students()), len(SAMPLE_STUDENTS))

    def test_primary_id_search(self):
        self.assertEqual(self.store.students('2026-0003')[0]['name'], 'Morgan Cruz')

    def test_secondary_name_search(self):
        self.assertEqual(self.store.students('morgan')[0]['id'], '2026-0003')

    def test_search_id_has_priority(self):
        self.store.add_student('MORGAN-99', 'Another Person')
        self.assertEqual(self.store.students('morgan')[0]['id'], 'MORGAN-99')

    def test_register_student_and_reload(self):
        self.store.add_student('2026-0100', 'New Student')
        self.assertEqual(AttendanceStore(self.path).students('2026-0100')[0]['name'], 'New Student')

    def test_duplicate_student_id_rejected(self):
        with self.assertRaises(AttendanceError):
            self.store.add_student('2026-0001', 'Someone Else')

    def test_blank_and_invalid_student_id_rejected(self):
        for sid in ['', 'a', '*abc']:
            with self.subTest(sid=sid), self.assertRaises(AttendanceError):
                self.store.add_student(sid, 'Valid Student')

    def test_mark_and_change_same_day(self):
        self.store.mark(DAY, '2026-0001', 'Present')
        self.store.mark(DAY, '2026-0001', 'Late')
        self.assertEqual(self.store.status(DAY, '2026-0001'), 'Late')
        self.assertEqual(len(self.store.data['attendance'][DAY]), 1)

    def test_dates_are_independent(self):
        self.store.mark(DAY, '2026-0001', 'Present')
        self.assertEqual(self.store.status('2026-11-05', '2026-0001'), 'Not Marked')

    def test_summary_counts_not_marked(self):
        self.store.mark(DAY, '2026-0001', 'Absent')
        summary = self.store.summary(DAY)
        self.assertEqual(summary['Absent'], 1)
        self.assertEqual(summary['Not Marked'], len(SAMPLE_STUDENTS) - 1)

    def test_clear_mark(self):
        self.store.mark(DAY, '2026-0001', 'Present')
        self.store.clear_mark(DAY, '2026-0001')
        self.assertEqual(self.store.status(DAY, '2026-0001'), 'Not Marked')

    def test_update_name(self):
        self.store.update_student('2026-0001', 'Changed Name')
        self.assertEqual(self.store.students('2026-0001')[0]['name'], 'Changed Name')

    def test_delete_removes_student_and_history(self):
        self.store.mark(DAY, '2026-0001', 'Present')
        self.store.remove_student('2026-0001')
        self.assertEqual(self.store.students('2026-0001'), [])
        self.assertNotIn('2026-0001', self.store.data['attendance'][DAY])

    def test_unknown_student_rejected(self):
        with self.assertRaises(AttendanceError):
            self.store.mark(DAY, 'NOT-FOUND', 'Present')

    def test_invalid_day_rejected(self):
        with self.assertRaises(AttendanceError):
            self.store.mark('2026-02-30', '2026-0001', 'Present')

    def test_invalid_status_rejected(self):
        with self.assertRaises(AttendanceError):
            self.store.mark(DAY, '2026-0001', 'Unknown')

    def test_corrupt_file_not_overwritten(self):
        self.path.write_text('{bad JSON', encoding='utf-8')
        with self.assertRaises(AttendanceError):
            AttendanceStore(self.path)
        self.assertEqual(self.path.read_text(encoding='utf-8'), '{bad JSON')


if __name__ == '__main__':
    unittest.main()
