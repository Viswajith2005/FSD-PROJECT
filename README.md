# Lost & Found Portal

A full-stack web application built with **Flask + Bootstrap + SQLite** that allows users to report and recover lost items in their community.

## 🌟 Features
- Report lost or found items with image upload
- Search & filter items by type and keyword
- User authentication (signup / login / logout)
- In-app notifications between users
- Profile management (edit name, change password)
- Admin panel: user management, analytics, ban/promote users
- Miruro-inspired premium dark UI

## 🛠️ Technologies
- **Backend:** Python, Flask, SQLite
- **Frontend:** HTML5, Bootstrap 5, Vanilla CSS, jQuery
- **Auth:** Werkzeug password hashing
- **Templating:** Jinja2

## 🚀 Setup Instructions

```bash
# 1. Clone the repo
git clone https://github.com/Viswajith2005/FSD-PROJECT.git
cd FSD-PROJECT

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## 📁 Project Structure
```
FSD project/
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── uploads/
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── dashboard.html
│   ├── login.html
│   ├── signup.html
│   ├── report.html
│   ├── item.html
│   ├── profile.html
│   ├── admin.html
│   └── notifications.html
├── app.py
├── database.py
├── schema.sql
└── requirements.txt
```
