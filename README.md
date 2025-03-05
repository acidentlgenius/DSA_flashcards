# 📚 DSA Flashcards

<div align="center">

![DSA Flashcards Logo](static/images/logo.png)

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-lightgrey.svg)](https://flask.palletsprojects.com/)

**Master Data Structures and Algorithms through interactive flashcards!**

[Features](#features) • [Demo](#live-demo) • [Installation](#installation) • [Usage](#usage) • [Tech Stack](#tech-stack) • [Architecture](#architecture) • [Contributing](#contributing)

</div>

## 🌟 Features

<details>
<summary>Click to expand features list!</summary>

- **Google Authentication** - Secure login via Google OAuth
- **Interactive Flashcards** - Learn DSA concepts through engaging flashcards
- **Progress Tracking** - Monitor your learning journey
- **Categorized Topics** - Organized by data structures, algorithms, and complexity
- **Spaced Repetition** - Smart algorithm to optimize your learning
- **Mobile Responsive** - Learn on any device

</details>

## 🎮 Live Demo

Check out the live application: [DSA Flashcards Demo](https://dsa-flashcards.example.com)

### Preview

<div align="center">
<details>
<summary>📸 Click to view screenshots</summary>
<br>

| Login Screen | Dashboard | Flashcard View |
|:-------------------------:|:-------------------------:|:-------------------------:|
| <img src="static/images/screenshot-login.png" alt="Login Screen" width="250"> | <img src="static/images/screenshot-dashboard.png" alt="Dashboard" width="250"> | <img src="static/images/screenshot-card.png" alt="Flashcard" width="250"> |

</details>
</div>

## ⚙️ Installation

<details>
<summary>Step-by-step installation guide</summary>

### Prerequisites
- Python 3.9+
- Git
- Google OAuth credentials

### Clone the repository
```bash
git clone https://github.com/yourusername/DSA_flashcards.git
cd DSA_flashcards
```

### Set up a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install dependencies
```bash
pip install -r requirements.txt
```

### Environment variables
Create a `.env` file in the root directory:
```
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your_secret_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### Initialize the database
```bash
flask db upgrade
```

### Run the application
```bash
flask run
```

Access the app at: http://localhost:5000

</details>

## 📝 Usage

<details>
<summary>How to use DSA Flashcards</summary>

1. **Sign in** with your Google account
2. **Select a topic** from the dashboard (Arrays, Linked Lists, Trees, etc.)
3. **Study flashcards** by flipping them to see questions and answers
4. **Mark cards** as "Easy," "Medium," or "Hard" to customize your learning path
5. **Track your progress** through the analytics dashboard
6. **Create custom sets** of flashcards for targeted practice

</details>

## 💻 Tech Stack

<div align="center">

| Frontend | Backend | Database | Tools |
|:--------:|:-------:|:--------:|:-----:|
| HTML5 | Python | SQLite | Git |
| CSS3 | Flask | PostgreSQL | Docker |
| JavaScript | SQLAlchemy | | OAuth |
| Bootstrap | | | Pytest |

</div>

## 🏗️ Architecture

```
DSA_flashcards/
├── app.py            # Application entry point
├── config.py         # Configuration settings
├── models/           # Database models
├── routes/           # Application routes
├── services/         # Business logic
├── static/           # Static assets
│   ├── css/          # Stylesheets
│   ├── js/           # JavaScript files
│   └── images/       # Images
├── templates/        # HTML templates
├── tests/            # Unit tests
└── utils/            # Utility functions
```

## 🎓 Skills Demonstrated

<details>
<summary>Technical skills showcased in this project</summary>

- **Backend Development**: Flask, API design, authentication
- **Frontend Development**: Responsive design, interactive UI
- **Database Design**: Relational database modeling, ORM
- **Authentication**: OAuth 2.0 integration with Google
- **Testing**: Unit testing, integration testing
- **DevOps**: Deployment, containerization
- **Software Architecture**: MVC pattern
- **Algorithm Knowledge**: DSA content creation

</details>

## 🚀 Future Enhancements

- [ ] User-created custom flashcards
- [ ] Social features (share progress, compete with friends)
- [ ] Dark mode
- [ ] Mobile app version
- [ ] AI-powered learning recommendations

## 📫 Contact

<div align="center">

Have questions or want to discuss this project? Reach out!

[![Email](https://img.shields.io/badge/Email-youremail%40example.com-blue)](mailto:youremail@example.com)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-YourName-blue)](https://www.linkedin.com/in/yourname/)
[![GitHub](https://img.shields.io/badge/GitHub-yourusername-blue)](https://github.com/yourusername)

</div>

---

<div align="center">
Created with ❤️ by Your Name
</div>
