from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
from database import get_db_connection, init_db
from werkzeug.utils import secure_filename
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mail_config

app = Flask(__name__)
app.secret_key = 'super_secret_lost_and_found_key'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
ITEMS_PER_PAGE = 9

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ── Gmail email helper ──
def send_gmail_notification(to_email, subject, html_body):
    """Send a Gmail notification. Silently skips if MAIL_ENABLED is False."""
    if not mail_config.MAIL_ENABLED:
        return
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = mail_config.MAIL_SENDER
        msg['To']      = to_email
        msg.attach(MIMEText(html_body, 'html'))
        with smtplib.SMTP(mail_config.MAIL_HOST, mail_config.MAIL_PORT) as server:
            server.ehlo()
            server.starttls()
            # SendGrid uses literal 'apikey' as username; Gmail uses the sender email
            smtp_user = 'apikey' if 'sendgrid' in mail_config.MAIL_HOST else mail_config.MAIL_SENDER
            server.login(smtp_user, mail_config.MAIL_PASSWORD)
            server.sendmail(mail_config.MAIL_SENDER, to_email, msg.as_string())
    except Exception as e:
        print(f'[Gmail] Failed to send email: {e}')

# ── Context processor: unread notification count for navbar bell ──
@app.context_processor
def inject_unread_count():
    if session.get('user_id'):
        conn = get_db_connection()
        count = conn.execute(
            'SELECT COUNT(*) FROM messages WHERE to_user_id = ? AND is_read = 0',
            (session['user_id'],)
        ).fetchone()[0]
        conn.close()
        return {'unread_count': count}
    return {'unread_count': 0}

# ── Ban check: redirect banned users on login ──
def check_banned(user):
    return user and user['is_banned']

@app.route('/')
def index():
    conn = get_db_connection()
    total_items    = conn.execute('SELECT COUNT(*) FROM items').fetchone()[0]
    found_count    = conn.execute("SELECT COUNT(*) FROM items WHERE type='found'").fetchone()[0]
    resolved_count = conn.execute("SELECT COUNT(*) FROM items WHERE status='resolved'").fetchone()[0]
    total_users    = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    conn.close()
    return render_template('index.html',
                           total_items=total_items,
                           found_count=found_count,
                           resolved_count=resolved_count,
                           total_users=total_users)

# ─────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                         (name, email, hashed_password))
            conn.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists.', 'danger')
        finally:
            conn.close()
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            if check_banned(user):
                flash('Your account has been suspended. Please contact the admin.', 'danger')
                return redirect(url_for('login'))
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['is_admin'] = user['is_admin']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

# ─────────────────────────────────────────
#  DASHBOARD (pagination + sort + filter)
# ─────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()

    query = 'SELECT * FROM items WHERE 1=1'
    params = []

    search_q   = request.args.get('q', '')
    filter_type = request.args.get('type', '')
    sort_by    = request.args.get('sort', 'newest')
    page       = max(1, request.args.get('page', 1, type=int))

    if search_q:
        query += ' AND (title LIKE ? OR description LIKE ?)'
        params.extend(['%' + search_q + '%', '%' + search_q + '%'])

    if filter_type in ['lost', 'found']:
        query += ' AND type = ?'
        params.append(filter_type)

    # Sort
    if sort_by == 'oldest':
        query += ' ORDER BY date_reported ASC'
    elif sort_by == 'category':
        query += ' ORDER BY category ASC'
    else:
        query += ' ORDER BY date_reported DESC'

    # Count total for pagination
    count_query = query.replace('SELECT *', 'SELECT COUNT(*)', 1)
    total = conn.execute(count_query, tuple(params)).fetchone()[0]
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = min(page, total_pages)

    offset = (page - 1) * ITEMS_PER_PAGE
    query += f' LIMIT {ITEMS_PER_PAGE} OFFSET {offset}'

    items = conn.execute(query, tuple(params)).fetchall()
    conn.close()

    return render_template('dashboard.html',
                           items=items,
                           page=page,
                           total_pages=total_pages,
                           total=total,
                           q=search_q,
                           filter_type=filter_type,
                           sort_by=sort_by)

# ─────────────────────────────────────────
#  REPORT / EDIT ITEM
# ─────────────────────────────────────────
@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'user_id' not in session:
        flash('Please log in to report an item.', 'warning')
        return redirect(url_for('login'))
    if request.method == 'POST':
        item_type   = request.form['type']
        title       = request.form['title']
        description = request.form['description']
        category    = request.form['category']
        location    = request.form['location']
        date_reported = request.form['date_reported']
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = url_for('static', filename='uploads/' + filename)
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO items (type, title, description, category, location, date_reported, image_filename, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (item_type, title, description, category, location, date_reported, image_url, session['user_id']))
        conn.commit()
        conn.close()
        flash('Item reported successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('report.html')

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    if not item or item['user_id'] != session['user_id']:
        conn.close()
        flash('Unauthorized to edit this item.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        item_type   = request.form['type']
        title       = request.form['title']
        description = request.form['description']
        category    = request.form['category']
        location    = request.form['location']
        date_reported = request.form['date_reported']
        image_url = item['image_filename']
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = url_for('static', filename='uploads/' + filename)
        conn.execute('''
            UPDATE items
            SET type=?, title=?, description=?, category=?, location=?, date_reported=?, image_filename=?
            WHERE id=?
        ''', (item_type, title, description, category, location, date_reported, image_url, item_id))
        conn.commit()
        conn.close()
        flash('Item updated successfully!', 'success')
        return redirect(url_for('item_detail', item_id=item_id))
    conn.close()
    return render_template('report.html', item=item)

# ─────────────────────────────────────────
#  ITEM DETAIL
# ─────────────────────────────────────────
@app.route('/item/<int:item_id>')
def item_detail(item_id):
    conn = get_db_connection()
    item = conn.execute('''
        SELECT items.*, users.name as reporter_name, users.email as reporter_email
        FROM items JOIN users ON items.user_id = users.id
        WHERE items.id = ?
    ''', (item_id,)).fetchone()
    if item is None:
        conn.close()
        flash('Item not found.', 'danger')
        return redirect(url_for('dashboard'))
    opposite_type = 'found' if item['type'] == 'lost' else 'lost'
    matches = conn.execute('''
        SELECT id, title, type, date_reported FROM items
        WHERE type = ? AND category = ? AND status = 'open' AND id != ?
        ORDER BY date_reported DESC LIMIT 3
    ''', (opposite_type, item['category'], item_id)).fetchall()
    conn.close()
    return render_template('item.html', item=item, matches=matches)

# ─────────────────────────────────────────
#  RESOLVE / DELETE
# ─────────────────────────────────────────
@app.route('/resolve/<int:item_id>')
def resolve_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    if item and (item['user_id'] == session['user_id'] or session.get('is_admin')):
        conn.execute('UPDATE items SET status = ? WHERE id = ?', ('resolved', item_id))
        conn.commit()
        flash('Item marked as resolved.', 'success')
    conn.close()
    return redirect(request.referrer or url_for('profile'))

@app.route('/delete/<int:item_id>')
def delete_item(item_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    if item and (item['user_id'] == session['user_id'] or session.get('is_admin')):
        conn.execute('DELETE FROM items WHERE id = ?', (item_id,))
        conn.commit()
        flash('Item removed.', 'success')
    conn.close()
    return redirect(request.referrer or url_for('profile'))

# ─────────────────────────────────────────
#  IN-APP NOTIFICATIONS (Contact Poster)
# ─────────────────────────────────────────
@app.route('/contact/<int:item_id>', methods=['POST'])
def contact_poster(item_id):
    if 'user_id' not in session:
        flash('Please log in to contact the poster.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()

    if not item:
        conn.close()
        flash('Item not found.', 'danger')
        return redirect(url_for('dashboard'))

    if item['user_id'] == session['user_id']:
        conn.close()
        flash('You cannot contact yourself.', 'warning')
        return redirect(url_for('item_detail', item_id=item_id))

    message_text = request.form.get('message', '').strip()
    if not message_text:
        conn.close()
        flash('Message cannot be empty.', 'warning')
        return redirect(url_for('item_detail', item_id=item_id))

    conn.execute('''
        INSERT INTO messages (from_user_id, to_user_id, item_id, message)
        VALUES (?, ?, ?, ?)
    ''', (session['user_id'], item['user_id'], item_id, message_text))
    conn.commit()

    # Also send Gmail notification to the poster
    poster = conn.execute('SELECT email, name FROM users WHERE id = ?', (item['user_id'],)).fetchone()
    sender_name = session.get('user_name', 'Someone')
    if poster:
        subject = f"[Lost & Found] New message about your item: {item['title']}"
        html_body = f"""
        <div style="font-family:Inter,sans-serif;max-width:560px;margin:auto;background:#111118;color:#fff;border-radius:12px;overflow:hidden;">
          <div style="background:#8b5cf6;padding:24px 28px;">
            <h2 style="margin:0;font-size:1.3rem;">Lost &amp; Found Portal</h2>
            <p style="margin:6px 0 0;font-size:.9rem;opacity:.85;">New message notification</p>
          </div>
          <div style="padding:28px;">
            <p style="font-size:1rem;margin-bottom:12px;">Hi <strong>{poster['name']}</strong>,</p>
            <p style="color:#c4c4d0;"><strong style="color:#fff;">{sender_name}</strong> sent you a message about your item: <strong style="color:#a78bfa;">{item['title']}</strong>.</p>
            <div style="background:#0a0a10;border-left:4px solid #8b5cf6;border-radius:4px;padding:16px 18px;margin:20px 0;">
              <p style="margin:0;color:#c4c4d0;line-height:1.7;">{message_text}</p>
            </div>
            <p style="color:#c4c4d0;font-size:.88rem;">Log in to the portal to view and respond to this message.</p>
            <a href="http://127.0.0.1:5000/item/{item_id}" style="display:inline-block;background:#8b5cf6;color:#fff;padding:12px 24px;border-radius:50px;text-decoration:none;font-weight:600;margin-top:8px;">View Item →</a>
          </div>
          <div style="padding:16px 28px;border-top:1px solid rgba(255,255,255,0.08);font-size:.78rem;color:#666;">
            Lost &amp; Found Portal — This is an automated notification.
          </div>
        </div>
        """
        send_gmail_notification(poster['email'], subject, html_body)

    conn.close()
    flash('Your message has been sent to the poster!', 'success')
    return redirect(url_for('item_detail', item_id=item_id))

@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    msgs = conn.execute('''
        SELECT messages.*, 
               users.name as sender_name,
               items.title as item_title,
               items.type  as item_type
        FROM messages
        JOIN users ON messages.from_user_id = users.id
        JOIN items ON messages.item_id = items.id
        WHERE messages.to_user_id = ?
        ORDER BY messages.created_at DESC
    ''', (session['user_id'],)).fetchall()
    # Mark all as read
    conn.execute('UPDATE messages SET is_read = 1 WHERE to_user_id = ?', (session['user_id'],))
    conn.commit()
    conn.close()
    return render_template('notifications.html', messages=msgs)

# ─────────────────────────────────────────
#  PROFILE + EDIT PROFILE + CHANGE PASSWORD
# ─────────────────────────────────────────
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    my_items = conn.execute(
        'SELECT * FROM items WHERE user_id = ? ORDER BY date_reported DESC',
        (session['user_id'],)
    ).fetchall()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('profile.html', items=my_items, user=user)

@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    new_name = request.form.get('name', '').strip()
    if not new_name or len(new_name) < 2:
        flash('Name must be at least 2 characters.', 'danger')
        return redirect(url_for('profile'))
    conn = get_db_connection()
    conn.execute('UPDATE users SET name = ? WHERE id = ?', (new_name, session['user_id']))
    conn.commit()
    conn.close()
    session['user_name'] = new_name
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    current_pw  = request.form.get('current_password', '')
    new_pw      = request.form.get('new_password', '')
    confirm_pw  = request.form.get('confirm_password', '')

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if not check_password_hash(user['password'], current_pw):
        conn.close()
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('profile'))

    if len(new_pw) < 6:
        conn.close()
        flash('New password must be at least 6 characters.', 'danger')
        return redirect(url_for('profile'))

    if new_pw != confirm_pw:
        conn.close()
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('profile'))

    conn.execute('UPDATE users SET password = ? WHERE id = ?',
                 (generate_password_hash(new_pw), session['user_id']))
    conn.commit()
    conn.close()
    flash('Password changed successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if 'avatar' not in request.files:
        flash('No file selected.', 'warning')
        return redirect(url_for('profile'))
    file = request.files['avatar']
    if file.filename == '':
        flash('No file selected.', 'warning')
        return redirect(url_for('profile'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        avatar_url = url_for('static', filename='uploads/' + filename)
        conn = get_db_connection()
        conn.execute('UPDATE users SET avatar_filename = ? WHERE id = ?',
                     (avatar_url, session['user_id']))
        conn.commit()
        conn.close()
        flash('Profile photo updated!', 'success')
    else:
        flash('Only PNG, JPG, JPEG, GIF files are allowed.', 'danger')
    return redirect(url_for('profile'))


# ─────────────────────────────────────────
#  ADMIN PANEL
# ─────────────────────────────────────────
@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY id DESC').fetchall()
    items = conn.execute('SELECT * FROM items ORDER BY date_reported DESC').fetchall()

    # Analytics
    total_users    = len(users)
    total_items    = len(items)
    lost_count     = sum(1 for i in items if i['type'] == 'lost')
    found_count    = sum(1 for i in items if i['type'] == 'found')
    resolved_count = sum(1 for i in items if i['status'] == 'resolved')
    open_count     = total_items - resolved_count

    # Category breakdown
    cat_counts = {}
    for item in items:
        cat = item['category']
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    cat_counts = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)

    conn.close()
    return render_template('admin.html',
                           users=users, items=items,
                           total_users=total_users, total_items=total_items,
                           lost_count=lost_count, found_count=found_count,
                           resolved_count=resolved_count, open_count=open_count,
                           cat_counts=cat_counts)

@app.route('/admin/delete_user/<int:user_id>')
def admin_delete_user(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    if user_id == session.get('user_id'):
        flash('You cannot delete your own admin account.', 'warning')
        return redirect(url_for('admin_dashboard'))
    conn = get_db_connection()
    conn.execute('DELETE FROM messages WHERE from_user_id = ? OR to_user_id = ?', (user_id, user_id))
    conn.execute('DELETE FROM items WHERE user_id = ?', (user_id,))
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    flash('User and their items deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_item/<int:item_id>')
def admin_delete_item(item_id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    conn = get_db_connection()
    conn.execute('DELETE FROM items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
    flash('Item deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/promote/<int:user_id>')
def admin_promote(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    if user_id == session.get('user_id'):
        flash('You already have admin rights.', 'info')
        return redirect(url_for('admin_dashboard'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        new_role = 0 if user['is_admin'] else 1
        conn.execute('UPDATE users SET is_admin = ? WHERE id = ?', (new_role, user_id))
        conn.commit()
        msg = 'User promoted to Admin.' if new_role else 'Admin rights revoked.'
        flash(msg, 'success')
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/ban/<int:user_id>')
def admin_ban(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    if user_id == session.get('user_id'):
        flash('You cannot ban your own account.', 'warning')
        return redirect(url_for('admin_dashboard'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        new_status = 0 if user['is_banned'] else 1
        conn.execute('UPDATE users SET is_banned = ? WHERE id = ?', (new_status, user_id))
        conn.commit()
        msg = 'User banned successfully.' if new_status else 'User unbanned successfully.'
        flash(msg, 'success')
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/resolve/<int:item_id>')
def admin_resolve(item_id):
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    conn = get_db_connection()
    conn.execute('UPDATE items SET status = ? WHERE id = ?', ('resolved', item_id))
    conn.commit()
    conn.close()
    flash('Item marked as resolved by admin.', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    if not os.path.exists('lost_found.db'):
        init_db()
    app.run(debug=True, port=5000)
