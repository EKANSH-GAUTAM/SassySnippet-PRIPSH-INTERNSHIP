import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'SASSY_SENTINEL_V29_ULTIMATE'

def get_db():
    conn = sqlite3.connect('snippets.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)')
    conn.execute('''CREATE TABLE IF NOT EXISTS snippets 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                    title TEXT, language TEXT, code TEXT, tags TEXT DEFAULT "", 
                    favorite INTEGER DEFAULT 0, is_deleted INTEGER DEFAULT 0)''')
    try: conn.execute('ALTER TABLE snippets ADD COLUMN tags TEXT DEFAULT ""')
    except: pass
    try: conn.execute('ALTER TABLE snippets ADD COLUMN is_deleted INTEGER DEFAULT 0')
    except: pass
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return redirect(url_for('dashboard')) if 'user_id' in session else redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user, pw = request.form.get('username').strip(), generate_password_hash(request.form.get('password'))
        conn = get_db()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (user, pw))
            conn.commit()
            flash('Identity Initialized. The Watchers are satisfied.', 'success')
            return redirect(url_for('login'))
        except: flash('Error: Username already exists.', 'error')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user, pw = request.form.get('username').strip(), request.form.get('password')
        res = get_db().execute('SELECT * FROM users WHERE username = ?', (user,)).fetchone()
        if res and check_password_hash(res['password'], pw):
            session.clear()
            session['user_id'], session['username'] = res['id'], res['username']
            return redirect(url_for('dashboard'))
        flash('Authorization Failed. Observers blocking access.', 'error')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    snippets = conn.execute('SELECT * FROM snippets WHERE user_id = ? AND is_deleted = 0 ORDER BY id DESC', (session['user_id'],)).fetchall()
    trash = conn.execute('SELECT * FROM snippets WHERE user_id = ? AND is_deleted = 1', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('index.html', user=session['username'], snippets=snippets, trash=trash)

@app.route('/add', methods=['POST'])
def add_snippet():
    title, lang = request.form.get('title'), request.form.get('language')
    boiler = {
        'python': 'def main():\n    print("Hello Sassy")\n\nif __name__ == "__main__":\n    main()',
        'javascript': 'console.log("Elite Sync Online");',
        'html': '<!DOCTYPE html>\n<html>\n<body>\n  <h1>Sassy Master</h1>\n</body>\n</html>',
        'cpp': '#include <iostream>\nusing namespace std;\n\nint main() {\n    return 0;\n}',
        'java': 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Java Master");\n    }\n}',
        'rust': 'fn main() {\n    println!("Hello Rust");\n}',
        'sql': 'CREATE TABLE data (id INT, name TEXT);'
    }
    code = boiler.get(lang, f"// New {lang} snippet initialized.")
    conn = get_db()
    conn.execute('INSERT INTO snippets (user_id, title, language, code) VALUES (?, ?, ?, ?)', (session['user_id'], title, lang, code))
    conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/update/<int:id>', methods=['POST'])
def update_snippet(id):
    code, tags = request.form.get('code'), request.form.get('tags')
    conn = get_db()
    conn.execute('UPDATE snippets SET code=?, tags=? WHERE id=?', (code, tags, id))
    conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/soft_delete/<int:id>', methods=['POST'])
def soft_delete(id):
    conn = get_db()
    conn.execute('UPDATE snippets SET is_deleted = 1 WHERE id=?', (id,))
    conn.commit()
    flash('Moved to Trash.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/restore/<int:id>', methods=['POST'])
def restore(id):
    conn = get_db()
    conn.execute('UPDATE snippets SET is_deleted = 0 WHERE id=?', (id,))
    conn.commit()
    flash('Snippet Restored.', 'success')
    return redirect(url_for('dashboard'))

# --- NEW PERMANENT DELETE ROUTE ---
@app.route('/permanent_delete/<int:id>', methods=['POST'])
def permanent_delete(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    # Security: Only delete if it belongs to user AND is already in trash
    conn.execute('DELETE FROM snippets WHERE id=? AND user_id=? AND is_deleted=1', (id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Code permanently purged.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)