from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set the GOOGLE_API_KEY environment variable (or create a .env file).")
genai.configure(api_key=API_KEY)

DATABASE = os.path.join(os.path.dirname(__file__), "database.db")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-me-to-a-random-secret")

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    if "user_id" in session:
        return redirect(url_for('chat_page'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            return render_template('register.html', error='Provide username and password.')
        db = get_db()
        cur = db.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            return render_template('register.html', error='Username already exists.')
        hashed = generate_password_hash(password)
        db.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, hashed))
        db.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()

        if user is None:
            error = "No account found for this username. Please sign up first 🌿"
        elif user[2] != password:
            error = "Incorrect password. Please try again 🔑"
        else:
            session['username'] = username
            return redirect(url_for('chat_page'))  # make sure your chat route name matches

    return render_template('login.html', error=error)
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    message = None
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()

        if user:
            c.execute("UPDATE users SET password=? WHERE username=?", (new_password, username))
            conn.commit()
            message = "✅ Password updated successfully! You can now log in."
        else:
            message = "⚠️ No user found with this username. Please check and try again."
        conn.close()

    return render_template('forgot_password.html', message=message)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/chat_page')
def chat_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html', username=session.get('username'))

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    user_id = session.get('user_id')
    if not message:
        return jsonify({'reply': "Please send a message."})
    # Save user message to DB
    db = get_db()
    db.execute("INSERT INTO chats (user_id, role, message, created_at) VALUES (?,?,?,?)",
               (user_id, 'user', message, datetime.utcnow().isoformat()))
    db.commit()

    # Build a supportive system prompt
    system_prompt = (
        "You are a kind, empathetic mental health companion named 'Mina'. "
        "Give short, supportive, non-judgmental responses. Offer breathing tips, grounding exercises, "
        "and ask gentle follow-up questions. Do NOT provide medical or legal advice; if the user is in danger, say you can't help and suggest seeking immediate help."
    )
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(f"System: {system_prompt}\nUser: {message}")
        reply_text = response.text if hasattr(response, 'text') else str(response)
    except Exception as e:
        reply_text = "I'm here for you, but I'm having trouble connecting to the AI right now."

    # Save bot reply to DB
    db.execute("INSERT INTO chats (user_id, role, message, created_at) VALUES (?,?,?,?)",
               (user_id, 'bot', reply_text, datetime.utcnow().isoformat()))
    db.commit()
    return jsonify({'reply': reply_text})

@app.route('/api/mood', methods=['POST'])
def api_mood():
    data = request.get_json() or {}
    mood = data.get('mood', '').strip()
    note = data.get('note', '').strip()
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status':'error','message':'Not logged in'}), 401
    db = get_db()
    db.execute("INSERT INTO mood_data (user_id, mood, note, created_at) VALUES (?,?,?,?)",
               (user_id, mood, note, datetime.utcnow().isoformat()))
    db.commit()
    return jsonify({'status':'ok'})

@app.route('/api/mood_history')
def api_mood_history():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify([])
    db = get_db()
    rows = db.execute("SELECT mood, note, created_at FROM mood_data WHERE user_id = ? ORDER BY created_at DESC LIMIT 30", (user_id,)).fetchall()
    items = [{'mood': r['mood'], 'note': r['note'], 'created_at': r['created_at']} for r in rows]
    return jsonify(items)

if __name__ == '__main__':
    # Ensure DB exists & tables
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY, user_id INTEGER, role TEXT, message TEXT, created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS mood_data (id INTEGER PRIMARY KEY, user_id INTEGER, mood TEXT, note TEXT, created_at TEXT)''')
    conn.commit()
    conn.close()
    app.run(host='0.0.0.0', port=5000, debug=True)
