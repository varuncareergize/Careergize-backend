# Employee attendance and leave

The dashboard includes Attendance and Leave pages. Employees check in/out, view their own attendance and leave history, apply for leave, and cancel pending requests. HR/Admin can view the employee roster, correct attendance with a required reason, and approve/reject other employees' pending requests. Managers and IT staff do not receive HR approval permissions.

Check-in/out timestamps come from the server. Hours are calculated as the exact elapsed duration. One attendance row per employee/date and one open check-in per employee are enforced by database constraints. Overnight check-outs close the open record from the previous date. Employees cannot edit timestamps, notes, or calculated hours.

HR corrections are saved atomically with before/after snapshots in AttendanceAuditLog. Django admin exposes attendance, leave, and audit records as read-only; corrections and reviews go through the dashboard/API to retain the audit trail. No delete endpoints are provided.

Leave dates are inclusive. Pending/approved requests cannot overlap. Backdated applications are disabled by default. Approved leave creates On Leave attendance on configured working dates and cannot overwrite already checked-in attendance. Calendar days and working days are displayed separately. LeaveAuditLog retains application, review, and cancellation history. HR cannot review their own request.

Company calendar settings in careergize_backend/settings.py:

- EMPLOYEE_TIME_ZONE: Asia/Kolkata
- EMPLOYEE_WEEK_OFF_DAYS: [5, 6] (Monday=0; Saturday/Sunday off)
- EMPLOYEE_HOLIDAYS: ISO date strings, for example ['2026-12-25']
- ALLOW_BACKDATED_LEAVE: False

A weekend/holiday with no attendance record still permits check-in if the employee is working. A day explicitly marked On Leave, Holiday, or Week Off by HR cannot be overwritten by an employee. The daily HR roster and Overview count missing attendance as Absent, without writing a record. Approved leave and explicit attendance statuses are preserved. Employees can still check in later.

Session-authenticated API routes (writes require a CSRF token):

- GET /api/attendance/options/ and /api/attendance/today/
- POST /api/attendance/check-in/ and /api/attendance/check-out/
- GET /api/attendance/history/?month=YYYY-MM&status=PRESENT
- GET /api/attendance/hr/?date=YYYY-MM-DD&employee=ID&department=ID
- POST /api/attendance/hr/correct/ (employee, date, status, optional check_in/check_out/notes, correction_reason)
- GET /api/attendance/ID/audit/
- GET/POST /api/leaves/ (HR uses view=all for the review queue)
- POST /api/leaves/ID/review/ (status APPROVED/REJECTED, hr_comment)
- POST /api/leaves/ID/cancel/ (owner; pending only)
