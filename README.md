# 🧠 Contraceptive Chatbot

A Django-based AI-powered chatbot designed to provide contraceptive information and help users locate nearby health facilities in Kabale District

---

## 🚀 Features

* 🤖 AI-powered chatbot responses
* 🧾 contraceptive methods (e.g.,IUDs, pills, implants)
* 📍 Nearby health facility recommendations
* 🧠 Intent detection using NLP
* 💬 Interactive chat interface
* 🗂️ Chat history tracking 

---

## 🛠️ Tech Stack

* Backend: Django (Python)
* AI/NLP: Custom logic / ML model
* Database: SQLite (development)
* Frontend: HTML, CSS, JavaScript
* APIs: Location services (for facility search)

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/contraceptive_chatbot.git
cd contraceptive_chatbot
```

### 2. Create and activate virtual environment

```bash
# Windows
python -m venv chat
chat\Scripts\activate

# Linux / Mac
python3 -m venv chat
source chat/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the root directory:

```
SECRET_KEY=your_secret_key
DEBUG=True
API_KEY=your_api_key
```

### 5. Apply migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Run the server

```bash
python manage.py runserver
```

Visit: http://127.0.0.1:8000/

---

## 🔐 Security Notes

* Do NOT commit `.env` files or API keys
* Ensure `DEBUG=False` in production
* Use environment variables for sensitive data

---

## 📦 Project Structure (Simplified)

```
project/
│── chatbot/
│── templates/
│── static/
│── manage.py
│── requirements.txt
│── .env (not committed)
│── .gitignore
```

---

## 🌍 Future Improvements

* 🌐 Deploy to cloud platforms
* 📱 Mobile-friendly UI
* 🧠 Advanced NLP (Deep Learning)
* 🏥 Real-time health facility integration
* 🔊 Voice-based interaction

---

## 🤝 Contributing

Contributions are welcome! Feel free to fork the repo and submit a pull request.

---

## 📄 License

This project is for educational and research purposes.

---

## 👨‍💻 Author

Developed by **Kalanzi Charles and Kyakusiimire Antonius**

---

## ⭐ Support

If you like this project, consider giving it a star ⭐ on GitHub!
