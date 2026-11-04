"""Classroom Attendance Monitoring System — simple offline Tkinter desktop app."""
import csv
import tkinter as tk
from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from attendance_service import AttendanceStore, AttendanceError, STATUSES, valid_day

DATA_PATH = Path(__file__).resolve().parent / 'data' / 'attendance.json'


class AttendanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Classroom Attendance Monitoring System')
        self.root.geometry('1000x675')
        self.root.minsize(800, 550)
        self.store = AttendanceStore(DATA_PATH)
        self.day = tk.StringVar(value=date.today().isoformat())
        self.query = tk.StringVar()
        self.selected_id = None
        self.student_id = tk.StringVar()
        self.student_name = tk.StringVar()
        self.status_choice = tk.StringVar(value='Present')
        self._build()
        self.refresh()

    def _build(self):
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('Treeview', rowheight=29, font=('Segoe UI', 10))
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        style.configure('TButton', padding=(9, 6), font=('Segoe UI', 10))
        style.configure('TLabel', font=('Segoe UI', 10))

        header = ttk.Frame(self.root, padding=(18, 14))
        header.pack(fill='x')
        ttk.Label(header, text='Classroom Attendance Monitoring', font=('Segoe UI', 18, 'bold')).pack(anchor='w')
        ttk.Label(header, text='Search students by ID first, or by name. Attendance is recorded for the selected date.').pack(anchor='w', pady=(2, 0))

        actions = ttk.Frame(self.root, padding=(18, 0, 18, 12))
        actions.pack(fill='x')
        ttk.Label(actions, text='Class date (YYYY-MM-DD):').pack(side='left')
        day_entry = ttk.Entry(actions, textvariable=self.day, width=14)
        day_entry.pack(side='left', padx=(8, 5))
        day_entry.bind('<Return>', lambda _: self.refresh())
        ttk.Button(actions, text='Today', command=lambda: self.change_day(date.today().isoformat())).pack(side='left', padx=3)
        ttk.Button(actions, text='Previous', command=lambda: self.shift_day(-1)).pack(side='left', padx=3)
        ttk.Button(actions, text='Next', command=lambda: self.shift_day(1)).pack(side='left', padx=3)
        ttk.Button(actions, text='Load Date', command=self.refresh).pack(side='left', padx=3)
        ttk.Button(actions, text='Export CSV', command=self.export_csv).pack(side='right')

        summary_frame = ttk.Frame(self.root, padding=(18, 0, 18, 10))
        summary_frame.pack(fill='x')
        self.summary_label = ttk.Label(summary_frame, text='', font=('Segoe UI', 10, 'bold'))
        self.summary_label.pack(anchor='w')

        search_bar = ttk.Frame(self.root, padding=(18, 0, 18, 8))
        search_bar.pack(fill='x')
        ttk.Label(search_bar, text='Student ID / Name:').pack(side='left')
        search_entry = ttk.Entry(search_bar, textvariable=self.query, width=35)
        search_entry.pack(side='left', padx=(10, 8))
        search_entry.bind('<Return>', lambda _: self.refresh())
        ttk.Button(search_bar, text='Search', command=self.refresh).pack(side='left', padx=3)
        ttk.Button(search_bar, text='Clear Search', command=lambda: self.query.set('')).pack(side='left', padx=3)
        self.query.trace_add('write', lambda *_: self.refresh())

        table_frame = ttk.Frame(self.root, padding=(18, 0, 18, 8))
        table_frame.pack(fill='both', expand=True)
        columns = ('id', 'name', 'status')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', selectmode='browse')
        self.tree.heading('id', text='Student ID')
        self.tree.heading('name', text='Student Name')
        self.tree.heading('status', text='Attendance Status')
        self.tree.column('id', width=165, anchor='w', stretch=False)
        self.tree.column('name', width=420, anchor='w')
        self.tree.column('status', width=190, anchor='center', stretch=False)
        bar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(side='left', fill='both', expand=True)
        bar.pack(side='right', fill='y')
        self.tree.bind('<<TreeviewSelect>>', self._select)

        editor = ttk.LabelFrame(self.root, text='Selected Student / Attendance', padding=(14, 10))
        editor.pack(fill='x', padx=18, pady=(0, 8))
        fields = ttk.Frame(editor)
        fields.pack(fill='x')
        ttk.Label(fields, text='Student ID').grid(row=0, column=0, sticky='w')
        ttk.Entry(fields, textvariable=self.student_id, width=19).grid(row=1, column=0, padx=(0, 12), sticky='w')
        ttk.Label(fields, text='Student Name').grid(row=0, column=1, sticky='w')
        ttk.Entry(fields, textvariable=self.student_name, width=38).grid(row=1, column=1, padx=(0, 12), sticky='w')
        ttk.Label(fields, text='Attendance').grid(row=0, column=2, sticky='w')
        ttk.Combobox(fields, textvariable=self.status_choice, values=STATUSES, state='readonly', width=13).grid(row=1, column=2, sticky='w')
        buttons = ttk.Frame(editor)
        buttons.pack(fill='x', pady=(10, 0))
        for caption, callback in [
            ('Mark Attendance', self.mark), ('Clear Mark', self.clear_mark),
            ('Add Student', self.add_student), ('Update Name', self.update_name),
            ('Delete Student', self.delete_student), ('New / Clear Selection', self.clear_selection),
        ]:
            ttk.Button(buttons, text=caption, command=callback).pack(side='left', padx=(0, 7))
        ttk.Label(self.root, text='Sample students are included on first launch. Changes are saved locally in data/attendance.json.', foreground='#555').pack(anchor='w', padx=20, pady=(0, 12))

    def _day(self):
        return valid_day(self.day.get().strip())

    def change_day(self, value):
        self.day.set(value)
        self.refresh()

    def shift_day(self, delta):
        try:
            day = date.fromisoformat(self._day())
            self.change_day((day + timedelta(days=delta)).isoformat())
        except (AttendanceError, OverflowError) as exc:
            messagebox.showerror('Invalid date', str(exc))

    def refresh(self):
        try:
            day = self._day()
        except AttendanceError:
            self.summary_label.configure(text='Enter a valid date in YYYY-MM-DD format.')
            return
        selected = self.selected_id
        self.tree.delete(*self.tree.get_children())
        for student in self.store.students(self.query.get()):
            sid = student['id']
            self.tree.insert('', 'end', iid=sid, values=(sid, student['name'], self.store.status(day, sid)))
        if selected and self.tree.exists(selected):
            self.tree.selection_set(selected)
        counts = self.store.summary(day)
        self.summary_label.configure(text=f"Total: {len(self.store.data['students'])}     Present: {counts['Present']}     Late: {counts['Late']}     Absent: {counts['Absent']}     Excused: {counts['Excused']}     Not Marked: {counts['Not Marked']}")

    def _select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        sid = selection[0]
        self.selected_id = sid
        student = next(s for s in self.store.data['students'] if s['id'] == sid)
        self.student_id.set(sid)
        self.student_name.set(student['name'])
        current = self.store.status(self._day(), sid)
        if current in STATUSES:
            self.status_choice.set(current)

    def clear_selection(self):
        self.selected_id = None
        self.tree.selection_remove(self.tree.selection())
        self.student_id.set('')
        self.student_name.set('')
        self.status_choice.set('Present')

    def _handle(self, callback):
        try:
            callback()
            self.refresh()
        except AttendanceError as exc:
            messagebox.showwarning('Validation', str(exc))
        except OSError as exc:
            messagebox.showerror('File error', str(exc))

    def add_student(self):
        def work():
            self.store.add_student(self.student_id.get(), self.student_name.get())
            messagebox.showinfo('Saved', 'Student registered successfully.')
            self.clear_selection()
        self._handle(work)

    def update_name(self):
        self._handle(lambda: self.store.update_student(self._selected(), self.student_name.get()))

    def _selected(self):
        if not self.selected_id:
            raise AttendanceError('Select an existing student from the table first.')
        return self.selected_id

    def delete_student(self):
        def work():
            sid = self._selected()
            if not messagebox.askyesno('Confirm removal', f'Delete {sid} and all their attendance records?'):
                return
            self.store.remove_student(sid)
            self.clear_selection()
        self._handle(work)

    def mark(self):
        self._handle(lambda: self.store.mark(self._day(), self._selected(), self.status_choice.get()))

    def clear_mark(self):
        self._handle(lambda: self.store.clear_mark(self._day(), self._selected()))

    def export_csv(self):
        try:
            day = self._day()
        except AttendanceError as exc:
            messagebox.showwarning('Invalid date', str(exc))
            return
        path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV Files', '*.csv')], initialfile=f'attendance_{day}.csv')
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as fh:
                writer = csv.writer(fh)
                writer.writerow(['Date', 'Student ID', 'Student Name', 'Status'])
                for student in self.store.students():
                    writer.writerow([day, student['id'], student['name'], self.store.status(day, student['id'])])
            messagebox.showinfo('Export complete', 'Attendance report exported to CSV.')
        except OSError as exc:
            messagebox.showerror('Export error', str(exc))


def main():
    root = tk.Tk()
    try:
        AttendanceApp(root)
    except AttendanceError as exc:
        messagebox.showerror('Cannot open attendance data', str(exc))
        root.destroy()
        return
    root.mainloop()


if __name__ == '__main__':
    main()
