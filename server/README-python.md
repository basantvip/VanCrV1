Python Flask alternative to save contact submissions to Excel

Prereqs
- Python 3.8+
- pip

Install

```powershell
cd server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-python.txt
```

Run

```powershell
python py_server.py
# Server will listen on http://localhost:3000 by default
```

This exposes `POST /save-contact` which accepts JSON payload:

{
  "phone": "+91-...",
  "email": "user@example.com",
  "message": "Hello"
}

Each submission is appended to `server/contact.xlsx` in sheet `Contacts` with columns:
- Contact Number
- Email Address
- Message
- DateTime
- ActionTaken (defaults to "Pending")
