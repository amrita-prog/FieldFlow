# FieldFlow — Field Force Management System

FieldFlow is a role-based management system designed to streamline field operations. It enables managers to assign tasks, field agents to log visits and capture notes, and automatically utilizes AI to analyze visit notes for risk flagging and sentiment analysis.

## 🚀 Live Demo & Repositories

- **Frontend (Live)**: [https://field-flow-frontend-puce.vercel.app/login](https://field-flow-frontend-puce.vercel.app/login)
- **Backend (API)**: [https://fieldflow-6ykv.onrender.com/](https://fieldflow-6ykv.onrender.com/)

- **Frontend Repository**: [amrita-prog/FieldFlow-frontend](https://github.com/amrita-prog/FieldFlow-frontend)
- **Backend Repository**: [amrita-prog/FieldFlow](https://github.com/amrita-prog/FieldFlow) *(this repo)*

---

## ✨ Key Features

- **Role-Based Access Control**: Strict hierarchical access for Admin, Regional Managers, Team Leads, Field Agents, and Auditors.
- **Task & Visit Management**: Seamlessly assign tasks and track visit lifecycles (Scheduled → In Progress → Completed).
- **AI-Powered Insights**: Automatically analyzes visit notes using AI (Google Gemini) to detect sentiment, flag risks, and recommend follow-up actions.
- **Dynamic Scoping**: Users only see data relevant to their region, team, or personal assignments.

---

## 🛠️ Technology Stack

- **Backend**: Python, Django, Django REST Framework
- **Database**: SQLite (for demo/development)
- **Authentication**: JWT (JSON Web Tokens)
- **AI Integration**: Google Gemini API

---

## 💻 How to Run Locally

Follow these steps to get the backend API running on your local machine.

### 1. Clone the Repository
```bash
git clone https://github.com/amrita-prog/FieldFlow.git
cd FieldFlow
```

### 2. Set up the Virtual Environment
```bash
python -m venv env
# On Windows:
env\Scripts\activate
# On Mac/Linux:
source env/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations
*(Note: A pre-configured `db.sqlite3` with demo data might already be present. Running migrations ensures your schema is up to date.)*
```bash
python manage.py migrate
```

### 5. Start the Development Server
```bash
python manage.py runserver
```
The API will now be accessible at `http://127.0.0.1:8000/`.

---

## 🔑 Default Test Credentials

If you seeded the database or are using the provided SQLite file, you can log in with the following dummy accounts (All passwords except Admin are **`Pass@123`**):

| Role | Email | Password |
|---|---|---|
| **Admin** | `admin@fieldflow.com` | `Admin@123` |
| **Regional Manager** | `rm.north@fieldflow.com` | `Pass@123` |
| **Team Lead** | `tl.alpha@fieldflow.com` | `Pass@123` |
| **Field Agent** | `agent1@fieldflow.com` | `Pass@123` |
| **Auditor** | `auditor@fieldflow.com` | `Pass@123` |

*(Note: Check out the `accounts/management/commands/seed.py` file for the complete list of seeded users).*
