# 🎓 Campus Connect

**Campus Connect** is a student-oriented web application designed to streamline academic information access. It enables students to view and interact with class schedules and manage basic academic data.

## 🚀 Features

- 📅 Upload and parse schedules (CSV/XLSX)
- 🗃️ Store and manage data in a structured database
- 🔍 Query and display schedule data in a web interface
- 🛠️ Simple API/backend logic using Python

## 🧠 Tech Stack

- **Python**
- **Flask** or **FastAPI** (based on `app.py`)
- **SQLite / SQLAlchemy** for database
- **Pandas** for reading `.csv` and `.xlsx` files
- **dotenv** for environment variable management

## 📁 Project Structure


## 📦 Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/campus-connect.git
cd campus-connect
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
DATABASE_URL=sqlite:///campus_connect.db
python app.py
