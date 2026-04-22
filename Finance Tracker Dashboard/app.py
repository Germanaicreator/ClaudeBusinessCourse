import os, io, zipfile, calendar, hmac
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

from flask import (Flask, request, session, jsonify,
                   send_file, redirect, render_template, abort)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import sqlite3

load_dotenv(dotenv_path=Path(__file__).parent / '.env')

app = Flask(__name__)
app.secret_key                        = os.environ['CC_SECRET_KEY']
app.permanent_session_lifetime        = timedelta(hours=8)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE']   = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

CC_USERNAME   = os.environ['CC_USERNAME']
CC_PASSWORD   = os.environ['CC_PASSWORD']
DB_PATH       = os.environ.get('DB_PATH',       '/var/www/control/dashboard.db')
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/var/www/control/uploads')
ALLOWED_EXT   = {'pdf', 'jpg', 'jpeg', 'png'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ── DB ─────────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        date          TEXT    NOT NULL,
        main_category TEXT    NOT NULL,
        sub_category  TEXT    NOT NULL,
        amount        REAL    NOT NULL,
        description   TEXT    DEFAULT '',
        invoice_path  TEXT    DEFAULT '',
        created_at    TEXT    DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        main_category TEXT    NOT NULL,
        name          TEXT    NOT NULL,
        UNIQUE(main_category, name)
    )''')
    defaults = [
        ('Revenue',         'AI Automation'),
        ('Revenue',         'Courses'),
        ('Revenue',         'YT Colab'),
        ('Revenue',         'Other'),
        ('Deposit',         'Bank Transfer'),
        ('Business',        'Software & Tools'),
        ('Business',        'Equipment'),
        ('Business',        'Travel & Transport'),
        ('Business',        'Other'),
        ('Privat Withdraw', 'Accommodation'),
        ('Privat Withdraw', 'Transport'),
        ('Privat Withdraw', 'Food'),
        ('Privat Withdraw', 'Savings'),
        ('Privat Withdraw', 'Other'),
    ]
    for main, name in defaults:
        c.execute('INSERT OR IGNORE INTO categories (main_category, name) VALUES (?,?)', (main, name))
    conn.commit()
    conn.close()


# ── AUTH ────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


# ── PAGES ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect('/')
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        user_ok = hmac.compare_digest(username.encode(), CC_USERNAME.encode())
        pass_ok = hmac.compare_digest(password.encode(), CC_PASSWORD.encode())
        if user_ok and pass_ok:
            session.permanent = True
            session['logged_in'] = True
            return redirect('/')
        error = 'Incorrect username or password.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})


# ── SUMMARY ─────────────────────────────────────────────────────────────────

@app.route('/api/summary')
@login_required
def summary():
    year = request.args.get('year', datetime.now().year, type=int)
    conn = get_db()
    c = conn.cursor()

    monthly = []
    for m in range(1, 13):
        prefix = f'{year}-{m:02d}'
        c.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE date LIKE ? AND main_category IN ('Revenue','Deposit')", (f'{prefix}%',))
        revenue = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE date LIKE ? AND main_category IN ('Business','Privat Withdraw')", (f'{prefix}%',))
        spending = c.fetchone()[0]
        monthly.append({
            'month':      m,
            'month_name': calendar.month_abbr[m],
            'revenue':    revenue,
            'spending':   spending,
            'surplus':    revenue - spending,
        })

    c.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE date LIKE ? AND main_category IN ('Revenue','Deposit')", (f'{year}%',))
    total_revenue = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE date LIKE ? AND main_category IN ('Business','Privat Withdraw')", (f'{year}%',))
    total_spending = c.fetchone()[0]

    c.execute("""SELECT main_category, sub_category, COALESCE(SUM(amount),0) AS total
                 FROM transactions WHERE date LIKE ?
                 GROUP BY main_category, sub_category
                 ORDER BY main_category, total DESC""", (f'{year}%',))
    categories = [dict(r) for r in c.fetchall()]

    conn.close()
    return jsonify({
        'monthly':        monthly,
        'total_revenue':  total_revenue,
        'total_spending': total_spending,
        'total_surplus':  total_revenue - total_spending,
        'categories':     categories,
        'year':           year,
    })


# ── TRANSACTIONS ─────────────────────────────────────────────────────────────

@app.route('/api/transactions')
@login_required
def get_transactions():
    page     = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    year     = request.args.get('year', '')
    month    = request.args.get('month', '')
    cat      = request.args.get('category', '')
    q        = request.args.get('q', '')

    conn = get_db()
    c = conn.cursor()

    where, params = ['1=1'], []
    if year:
        where.append("date LIKE ?"); params.append(f'{year}%')
    if month:
        where.append("date LIKE ?"); params.append(f'%-{int(month):02d}-%')
    if cat:
        where.append("main_category = ?"); params.append(cat)
    if q:
        where.append("(description LIKE ? OR sub_category LIKE ?)"); params += [f'%{q}%', f'%{q}%']

    where_str = ' AND '.join(where)
    c.execute(f'SELECT COUNT(*) FROM transactions WHERE {where_str}', params)
    total = c.fetchone()[0]

    offset = (page - 1) * per_page
    c.execute(f'''SELECT * FROM transactions WHERE {where_str}
                  ORDER BY date DESC, id DESC LIMIT ? OFFSET ?''',
              params + [per_page, offset])
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'transactions': rows, 'total': total, 'page': page, 'per_page': per_page})


@app.route('/api/transactions', methods=['POST'])
@login_required
def add_transaction():
    d = request.get_json() or {}
    required = ('date', 'main_category', 'sub_category', 'amount')
    if not all(k in d for k in required):
        return jsonify({'error': 'Missing fields'}), 400
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO transactions (date, main_category, sub_category, amount, description)
                 VALUES (?,?,?,?,?)''',
              (d['date'], d['main_category'], d['sub_category'],
               float(d['amount']), d.get('description', '')))
    tid = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'id': tid, 'success': True})


@app.route('/api/transactions/<int:tid>', methods=['DELETE'])
@login_required
def delete_transaction(tid):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT invoice_path FROM transactions WHERE id=?', (tid,))
    row = c.fetchone()
    if row and row['invoice_path']:
        fpath = os.path.join(UPLOAD_FOLDER, row['invoice_path'])
        if os.path.exists(fpath):
            os.remove(fpath)
    c.execute('DELETE FROM transactions WHERE id=?', (tid,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# ── INVOICES ─────────────────────────────────────────────────────────────────

@app.route('/api/transactions/<int:tid>/invoice', methods=['POST'])
@login_required
def upload_invoice(tid):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    f = request.files['file']
    if not f or not allowed_file(f.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    ext = f.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f'{tid}_{datetime.now().strftime("%Y%m%d%H%M%S")}.{ext}')
    f.save(os.path.join(UPLOAD_FOLDER, filename))
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE transactions SET invoice_path=? WHERE id=?', (filename, tid))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'filename': filename})


@app.route('/api/invoices/<filename>')
@login_required
def get_invoice(filename):
    path = os.path.join(UPLOAD_FOLDER, secure_filename(filename))
    if not os.path.exists(path):
        abort(404)
    return send_file(path)


@app.route('/api/invoices/download')
@login_required
def download_invoices():
    from_date = request.args.get('from', '')
    to_date   = request.args.get('to', '')
    inv_type  = request.args.get('type', 'all')

    conn = get_db()
    c = conn.cursor()
    where  = ["invoice_path != '' AND invoice_path IS NOT NULL"]
    params = []
    if from_date:
        where.append("date >= ?"); params.append(from_date)
    if to_date:
        where.append("date <= ?"); params.append(to_date)
    if inv_type == 'revenue':
        where.append("main_category IN ('Revenue','Deposit')")
    elif inv_type == 'spending':
        where.append("main_category IN ('Business','Privat Withdraw')")

    c.execute(f"SELECT * FROM transactions WHERE {' AND '.join(where)} ORDER BY date", params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for r in rows:
            fpath = os.path.join(UPLOAD_FOLDER, r['invoice_path'])
            if os.path.exists(fpath):
                ext   = r['invoice_path'].rsplit('.', 1)[-1]
                label = f"{r['date']}_{r['main_category']}_{r['sub_category']}_{r['amount']}"
                label = label.replace(' ', '_').replace('/', '-')
                zf.write(fpath, f'{label}.{ext}')
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name='invoices.zip', mimetype='application/zip')


# ── CATEGORIES ───────────────────────────────────────────────────────────────

@app.route('/api/categories')
@login_required
def get_categories():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM categories ORDER BY main_category, name')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    grouped = {}
    for r in rows:
        grouped.setdefault(r['main_category'], []).append(r['name'])
    return jsonify(grouped)


@app.route('/api/categories', methods=['POST'])
@login_required
def add_category():
    d = request.get_json() or {}
    if not d.get('main_category') or not d.get('name'):
        return jsonify({'error': 'Missing fields'}), 400
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO categories (main_category, name) VALUES (?,?)',
              (d['main_category'], d['name']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# ── REPORT ───────────────────────────────────────────────────────────────────

@app.route('/api/report')
@login_required
def generate_report():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable)

    from_date = request.args.get('from', f'{datetime.now().year}-01-01')
    to_date   = request.args.get('to',   f'{datetime.now().year}-12-31')

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE date >= ? AND date <= ? ORDER BY date",
              (from_date, to_date))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    earn_rows  = [r for r in rows if r['main_category'] in ('Revenue', 'Deposit')]
    spend_rows = [r for r in rows if r['main_category'] in ('Business', 'Privat Withdraw')]
    total_rev  = sum(r['amount'] for r in earn_rows)
    total_sp   = sum(r['amount'] for r in spend_rows)

    GOLD = colors.HexColor('#c9a96e')
    DARK = colors.HexColor('#1a1a2e')
    MID  = colors.HexColor('#444444')
    LITE = colors.HexColor('#f5f4f0')

    def ps(name, **kw):
        return ParagraphStyle(name, **kw)

    title_s  = ps('T',  fontName='Helvetica-Bold', fontSize=26, textColor=DARK, spaceAfter=4)
    sub_s    = ps('S',  fontName='Helvetica',       fontSize=11, textColor=MID,  spaceAfter=18)
    h2_s     = ps('H2', fontName='Helvetica-Bold',  fontSize=13, textColor=DARK, spaceBefore=18, spaceAfter=8)
    normal_s = ps('N',  fontName='Helvetica',       fontSize=9,  textColor=MID,  leading=14)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=22*mm,  bottomMargin=22*mm)
    story = []

    story.append(Paragraph('Financial Report', title_s))
    story.append(Paragraph(f'Period: {from_date} — {to_date}', sub_s))
    story.append(HRFlowable(width='100%', thickness=1.5, color=GOLD, spaceAfter=18))

    summary_data = [
        ['Summary',        'Amount'],
        ['Total Earnings', f'€ {total_rev:,.2f}'],
        ['Total Spending', f'€ {total_sp:,.2f}'],
        ['Net Surplus',    f'€ {total_rev - total_sp:,.2f}'],
    ]
    ts = Table(summary_data, colWidths=[130*mm, 50*mm])
    ts.setStyle(TableStyle([
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, -1), 10),
        ('TEXTCOLOR',      (0, 0), (-1, 0),  GOLD),
        ('BACKGROUND',     (0, 0), (-1, 0),  DARK),
        ('ALIGN',          (1, 0), (1, -1),  'RIGHT'),
        ('FONTNAME',       (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),  [LITE, colors.white]),
        ('LINEBELOW',      (0, -1), (-1, -1), 1, GOLD),
        ('TOPPADDING',     (0, 0), (-1, -1),  6),
        ('BOTTOMPADDING',  (0, 0), (-1, -1),  6),
    ]))
    story.append(ts)
    story.append(Spacer(1, 12))

    def make_table(title_text, txns):
        story.append(Paragraph(title_text, h2_s))
        if not txns:
            story.append(Paragraph('No entries in this period.', normal_s))
            return
        data = [['Date', 'Category', 'Sub-Category', 'Description', 'Amount']]
        for r in txns:
            data.append([
                r['date'], r['main_category'], r['sub_category'],
                (r['description'] or '')[:45],
                f"€ {r['amount']:,.2f}"
            ])
        tbl = Table(data, colWidths=[24*mm, 32*mm, 36*mm, 55*mm, 25*mm])
        tbl.setStyle(TableStyle([
            ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, -1), 8),
            ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
            ('BACKGROUND',    (0, 0), (-1, 0),  DARK),
            ('ALIGN',         (4, 0), (4, -1),  'RIGHT'),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1),  [LITE, colors.white]),
            ('GRID',          (0, 0), (-1, -1),  0.25, colors.HexColor('#dddddd')),
            ('TOPPADDING',    (0, 0), (-1, -1),  4),
            ('BOTTOMPADDING', (0, 0), (-1, -1),  4),
        ]))
        story.append(tbl)

    make_table('Earnings', earn_rows)
    story.append(Spacer(1, 6))
    make_table('Spending', spend_rows)

    doc.build(story)
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f'report_{from_date}_{to_date}.pdf',
                     mimetype='application/pdf')


# ── BOOT ─────────────────────────────────────────────────────────────────────

init_db()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5003, debug=False)
