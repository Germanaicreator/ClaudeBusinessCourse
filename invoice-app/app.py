"""
AI Experts — Invoice Dashboard
Flask application for invoice management.
"""

import os
import csv
import io
import hmac
import hashlib
import time
import smtplib
from datetime import datetime, date
from functools import wraps
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage

from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, send_file, flash)
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

# ─── APP SETUP ────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INVOICE_DIR = os.path.join(BASE_DIR, 'invoices')
os.makedirs(INVOICE_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'invoice-secret-key-please-change')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'invoices.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

STARTING_INVOICE_NUMBER = int(os.environ.get('STARTING_INVOICE_NUMBER', 2026001))
DASHBOARD_PASSWORD = os.environ.get('DASHBOARD_PASSWORD', 'changeme123')
CC_SSO_SECRET      = os.environ.get('CC_SSO_SECRET', '')

db = SQLAlchemy(app)


# ─── MODELS ───────────────────────────────────────────────────────────────────

class Client(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    customer_number = db.Column(db.String(50), unique=True, nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    email        = db.Column(db.String(200), nullable=False)
    address      = db.Column(db.Text, nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    invoices     = db.relationship('Invoice', backref='client', lazy=True,
                                   cascade='all, delete-orphan')

    @property
    def total_revenue(self):
        return sum(inv.total_amount for inv in self.invoices
                   if inv.status in ('sent', 'paid'))

    @property
    def open_invoices(self):
        return [inv for inv in self.invoices if inv.status == 'sent']

    @property
    def last_invoice_sent(self):
        sent = [inv for inv in self.invoices if inv.sent_at]
        return max(sent, key=lambda i: i.sent_at).sent_at if sent else None


class Product(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    price       = db.Column(db.Float, nullable=False)
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


class Invoice(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), nullable=False)
    client_id      = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    invoice_date   = db.Column(db.Date, nullable=False, default=date.today)
    delivery_date  = db.Column(db.Date, nullable=True)
    status         = db.Column(db.String(20), default='draft')  # draft | sent | paid
    pdf_path       = db.Column(db.String(500))
    sent_at        = db.Column(db.DateTime)
    paid_at        = db.Column(db.DateTime)
    email_subject  = db.Column(db.Text, default='')
    email_body     = db.Column(db.Text, default='')
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    items          = db.relationship('InvoiceItem', backref='invoice', lazy=True,
                                     cascade='all, delete-orphan')

    @property
    def total_amount(self):
        return sum(item.line_total for item in self.items)

    @property
    def vat_amount(self):
        t = self.total_amount
        return t - (t / 1.19)

    @property
    def net_amount(self):
        return self.total_amount / 1.19

    @property
    def has_pdf(self):
        return bool(self.pdf_path and os.path.exists(self.pdf_path))


class InvoiceItem(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    invoice_id  = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount      = db.Column(db.Float, default=1.0)
    price       = db.Column(db.Float, nullable=False)
    discount    = db.Column(db.Float, default=0.0)

    @property
    def line_total(self):
        base = self.amount * self.price
        if self.discount:
            base = base * (1 - self.discount / 100)
        return base

    @property
    def vat_amount(self):
        lt = self.line_total
        return lt - (lt / 1.19)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def fmt(amount):
    """Format number as German currency string: 2.500,00 €"""
    s = f"{float(amount or 0):,.2f}"
    return s.replace(',', 'X').replace('.', ',').replace('X', '.') + ' €'


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def get_next_invoice_number():
    """Return next sequential invoice number after the last SENT or PAID invoice."""
    sent_invoices = Invoice.query.filter(
        Invoice.status.in_(['sent', 'paid'])
    ).all()
    max_num = None
    for inv in sent_invoices:
        try:
            n = int(inv.invoice_number)
            if max_num is None or n > max_num:
                max_num = n
        except (ValueError, TypeError):
            pass
    return str((max_num + 1) if max_num is not None else STARTING_INVOICE_NUMBER)


def is_invoice_number_sent(number, exclude_id=None):
    """Check if invoice number has already been used in a SENT/PAID invoice."""
    q = Invoice.query.filter(
        Invoice.invoice_number == str(number),
        Invoice.status.in_(['sent', 'paid'])
    )
    if exclude_id:
        q = q.filter(Invoice.id != exclude_id)
    return q.first() is not None


def _build_email_html(invoice):
    """Build HTML email body. Logo is referenced via CID — attached separately in invoice_send."""
    date_str   = invoice.invoice_date.strftime('%d.%m.%Y')
    amount_str = fmt(invoice.total_amount)
    company    = invoice.client.company_name
    inv_num    = invoice.invoice_number
    email_addr = os.environ.get('COMPANY_EMAIL', 'Dominik@limitless-ai-solutions.com')
    website    = os.environ.get('COMPANY_WEBSITE', 'https://rosalia-yachts.com')

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:40px 0;background:#f4f4f4;font-family:Arial,Helvetica,sans-serif;">
  <table cellpadding="0" cellspacing="0" width="100%" style="max-width:600px;margin:0 auto;">
    <tr><td style="background:#ffffff;border-radius:8px;padding:48px 48px 40px;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

      <p style="margin:0 0 16px;font-size:15px;color:#1a1a1a;">Dear {company},</p>

      <p style="margin:0 0 16px;font-size:15px;color:#333;">
        Please find attached your invoice {inv_num} dated {date_str}.
      </p>

      <p style="margin:0 0 16px;font-size:15px;color:#1a1a1a;">
        <strong>Invoice Amount: {amount_str}</strong>
      </p>

      <p style="margin:0 0 16px;font-size:15px;color:#333;">
        Please transfer the invoice amount to the bank account stated on the invoice.
        Payment is due upon receipt.
      </p>

      <p style="margin:0 0 28px;font-size:15px;color:#333;">
        Thank you for your trust. If you have any questions, please don&#39;t hesitate to reach out.
      </p>

      <p style="margin:0 0 20px;font-size:15px;color:#1a1a1a;">
        Best regards,<br><strong>Team AI Experts</strong>
      </p>

      <!-- Logo via CID inline attachment (Gmail-compatible) -->
      <img src="cid:company_logo" alt="AI Experts"
           style="height:52px;display:block;margin-bottom:24px;">

      <hr style="border:none;border-top:1px solid #e0e0e0;margin:0 0 20px;">

      <p style="margin:0;font-size:12px;color:#999;">
        {email_addr}<br>{website}
      </p>

    </td></tr>
  </table>
</body>
</html>"""
    return html


def get_default_email(invoice):
    """Legacy helper — returns (subject, plain_text) for backwards compat."""
    subject = f"Invoice {invoice.invoice_number} — AI Experts"
    body = (
        f"Dear {invoice.client.company_name},\n\n"
        f"Please find attached your invoice {invoice.invoice_number} "
        f"dated {invoice.invoice_date.strftime('%d.%m.%Y')}.\n\n"
        f"Invoice Amount: {fmt(invoice.total_amount)}\n\n"
        f"Please transfer the invoice amount to the bank account stated on the invoice. "
        f"Payment is due upon receipt.\n\n"
        f"Thank you for your trust. If you have any questions, please don't hesitate to reach out.\n\n"
        f"Best regards,\nAI Experts\n\n---\n"
        f"{os.environ.get('COMPANY_EMAIL', 'germanaicreator@gmail.com')}\n"
        f"{os.environ.get('COMPANY_WEBSITE', 'https://rosalia-yachts.com')}"
    )
    return subject, body


def company_info():
    return {
        'name':        os.environ.get('COMPANY_NAME', 'AI Experts'),
        'address':     os.environ.get('COMPANY_ADDRESS', 'Musterstraße 1 · 10115 Berlin · Germany'),
        'tax_number':  os.environ.get('COMPANY_TAX_NUMBER', '00/000/00000'),
        'vat_id':      os.environ.get('COMPANY_VAT_ID', 'DE000000000'),
        'email':       os.environ.get('COMPANY_EMAIL', 'germanaicreator@gmail.com'),
        'phone':       os.environ.get('COMPANY_PHONE', '+49 000 000 0000'),
        'iban':        os.environ.get('COMPANY_IBAN', 'DE13 1001 0000 0628 1929 21'),
        'bic':         os.environ.get('COMPANY_BIC', 'FINOM DE82'),
        'bank':        os.environ.get('COMPANY_BANK', 'FINOM PAYMENTS'),
        'website':     os.environ.get('COMPANY_WEBSITE', 'https://rosalia-yachts.com'),
    }


@app.context_processor
def inject_globals():
    return {'COMPANY': company_info(), 'fmt': fmt, 'now_utc': datetime.utcnow()}


# ─── AUTH ──────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        if request.form.get('password', '') == DASHBOARD_PASSWORD:
            session['logged_in'] = True
            session.permanent = True
            return redirect(url_for('dashboard'))
        error = 'Incorrect password. Please try again.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/cc-auth')
def cc_auth():
    """SSO entry-point called by the Business Command Center.
    Validates a short-lived HMAC token, logs the user in, then redirects
    to the requested page (or the dashboard).  Falls back to normal login
    if the token is missing / expired / invalid.
    """
    token = request.args.get('token', '')
    nxt   = request.args.get('next', '/')

    # Only allow relative paths in `next` to prevent open redirect
    if not nxt.startswith('/'):
        nxt = '/'

    if CC_SSO_SECRET and token:
        try:
            ts, sig = token.split('.', 1)
            expected = hmac.new(CC_SSO_SECRET.encode(), ts.encode(), hashlib.sha256).hexdigest()
            valid_sig = hmac.compare_digest(sig, expected)
            valid_age = (int(time.time()) - int(ts)) <= 90
            if valid_sig and valid_age:
                session['logged_in'] = True
                session.permanent    = True
                return redirect(nxt)
        except Exception:
            pass

    # Token invalid — fall through to normal login
    return redirect(url_for('login'))


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    revenue_invoices = Invoice.query.filter(Invoice.status.in_(['sent', 'paid'])).all()
    total_revenue = sum(i.total_amount for i in revenue_invoices)
    year = datetime.now().year
    year_revenue = sum(i.total_amount for i in revenue_invoices
                       if i.invoice_date and i.invoice_date.year == year)
    open_invoices = (Invoice.query.filter_by(status='sent')
                     .order_by(Invoice.sent_at.desc()).all())
    draft_count = Invoice.query.filter_by(status='draft').count()
    recent_paid = (Invoice.query.filter_by(status='paid')
                   .order_by(Invoice.paid_at.desc()).limit(5).all())
    return render_template('dashboard.html',
        total_revenue=total_revenue,
        year_revenue=year_revenue,
        open_invoices=open_invoices,
        draft_count=draft_count,
        recent_paid=recent_paid,
        current_year=year)


@app.route('/invoices/<int:invoice_id>/mark-paid', methods=['POST'])
@login_required
def mark_paid(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    inv.status = 'paid'
    inv.paid_at = datetime.utcnow()
    db.session.commit()
    flash(f'Invoice #{inv.invoice_number} marked as paid.', 'success')
    return redirect(request.referrer or url_for('dashboard'))


# ─── CLIENTS ──────────────────────────────────────────────────────────────────

@app.route('/clients')
@login_required
def clients():
    all_clients = Client.query.order_by(Client.customer_number).all()
    return render_template('clients.html', clients=all_clients)


@app.route('/clients/add', methods=['POST'])
@login_required
def client_add():
    cn  = request.form.get('customer_number', '').strip()
    co  = request.form.get('company_name', '').strip()
    em  = request.form.get('email', '').strip()
    adr = request.form.get('address', '').strip()
    if not all([cn, co, em, adr]):
        flash('All fields are required.', 'error')
        return redirect(url_for('clients'))
    if Client.query.filter_by(customer_number=cn).first():
        flash(f'Customer number {cn} already exists.', 'error')
        return redirect(url_for('clients'))
    db.session.add(Client(customer_number=cn, company_name=co, email=em, address=adr))
    db.session.commit()
    flash(f'Client "{co}" added.', 'success')
    return redirect(url_for('clients'))


@app.route('/clients/<int:client_id>/edit', methods=['POST'])
@login_required
def client_edit(client_id):
    c = Client.query.get_or_404(client_id)
    c.company_name = request.form.get('company_name', c.company_name).strip()
    c.email        = request.form.get('email', c.email).strip()
    c.address      = request.form.get('address', c.address).strip()
    db.session.commit()
    flash(f'Client "{c.company_name}" updated.', 'success')
    return redirect(url_for('clients'))


@app.route('/clients/<int:client_id>/delete', methods=['POST'])
@login_required
def client_delete(client_id):
    c = Client.query.get_or_404(client_id)
    name = c.company_name
    db.session.delete(c)
    db.session.commit()
    flash(f'Client "{name}" deleted.', 'success')
    return redirect(url_for('clients'))


@app.route('/clients/import', methods=['POST'])
@login_required
def client_import():
    f = request.files.get('file')
    if not f or not f.filename.endswith('.csv'):
        flash('Please upload a valid .csv file.', 'error')
        return redirect(url_for('clients'))
    try:
        stream = io.StringIO(f.stream.read().decode('utf-8-sig'))
        reader = csv.DictReader(stream)
        added = skipped = 0
        for row in reader:
            cn  = (row.get('customer_number') or row.get('Customer Number') or '').strip()
            co  = (row.get('company_name') or row.get('Company Name') or '').strip()
            em  = (row.get('email') or row.get('Email') or '').strip()
            adr = (row.get('address') or row.get('Address') or '').strip()
            if not all([cn, co, em, adr]):
                skipped += 1
                continue
            if Client.query.filter_by(customer_number=cn).first():
                skipped += 1
                continue
            db.session.add(Client(customer_number=cn, company_name=co, email=em, address=adr))
            added += 1
        db.session.commit()
        flash(f'Import complete: {added} added, {skipped} skipped.', 'success')
    except Exception as e:
        flash(f'Import error: {e}', 'error')
    return redirect(url_for('clients'))


# ─── PRODUCTS ──────────────────────────────────────────────────────────────────

@app.route('/products')
@login_required
def products():
    all_products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    return render_template('products.html', products=all_products)


@app.route('/products/add', methods=['POST'])
@login_required
def product_add():
    name = request.form.get('name', '').strip()
    desc = request.form.get('description', '').strip()
    price_raw = request.form.get('price', '').strip().replace(',', '.')
    if not name or not price_raw:
        flash('Name and price are required.', 'error')
        return redirect(url_for('products'))
    try:
        price = float(price_raw)
    except ValueError:
        flash('Invalid price.', 'error')
        return redirect(url_for('products'))
    db.session.add(Product(name=name, description=desc, price=price))
    db.session.commit()
    flash(f'Product "{name}" added.', 'success')
    return redirect(url_for('products'))


@app.route('/products/<int:pid>/edit', methods=['POST'])
@login_required
def product_edit(pid):
    p = Product.query.get_or_404(pid)
    p.name = request.form.get('name', p.name).strip()
    p.description = request.form.get('description', p.description or '').strip()
    try:
        p.price = float(request.form.get('price', p.price).replace(',', '.'))
    except (ValueError, AttributeError):
        pass
    db.session.commit()
    flash(f'Product "{p.name}" updated.', 'success')
    return redirect(url_for('products'))


@app.route('/products/<int:pid>/delete', methods=['POST'])
@login_required
def product_delete(pid):
    p = Product.query.get_or_404(pid)
    p.is_active = False
    db.session.commit()
    flash(f'Product "{p.name}" removed.', 'success')
    return redirect(url_for('products'))


# ─── INVOICES ──────────────────────────────────────────────────────────────────

@app.route('/invoices')
@login_required
def invoices():
    status = request.args.get('status', 'all')
    q = Invoice.query
    if status in ('draft', 'sent', 'paid'):
        q = q.filter_by(status=status)
    all_inv = q.order_by(Invoice.created_at.desc()).all()
    return render_template('invoices.html', invoices=all_inv, status_filter=status)


@app.route('/invoices/new', methods=['GET', 'POST'])
@login_required
def invoice_new():
    if request.method == 'GET':
        return render_template('invoice_create.html',
            invoice=None,
            clients=Client.query.order_by(Client.company_name).all(),
            products=Product.query.filter_by(is_active=True).order_by(Product.name).all(),
            next_number=get_next_invoice_number(),
            today=date.today().isoformat(),
            preselect_client=request.args.get('client_id'))

    # action comes from the URL ?finalize=1 (formaction button) or defaults to draft
    action = 'finalize' if request.args.get('finalize') == '1' else 'draft'
    return _save_invoice(invoice=None, action=action)


@app.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
def invoice_edit(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    if inv.status != 'draft':
        flash('Only draft invoices can be edited.', 'error')
        return redirect(url_for('invoice_view', invoice_id=invoice_id))

    if request.method == 'GET':
        suggested = get_next_invoice_number()
        return render_template('invoice_create.html',
            invoice=inv,
            clients=Client.query.order_by(Client.company_name).all(),
            products=Product.query.filter_by(is_active=True).order_by(Product.name).all(),
            next_number=suggested,
            today=date.today().isoformat(),
            preselect_client=None)

    action = 'finalize' if request.args.get('finalize') == '1' else 'draft'
    return _save_invoice(invoice=inv, action=action)


def _save_invoice(invoice=None, action='draft'):
    """Shared handler for create (invoice=None) and edit (invoice=existing).
    action is passed explicitly from the route (derived from ?finalize=1 URL param).
    """
    client_id     = request.form.get('client_id', '').strip()
    inv_number    = request.form.get('invoice_number', '').strip()
    inv_date_str  = request.form.get('invoice_date', '')
    del_date_str  = request.form.get('delivery_date', '')
    email_subj    = request.form.get('email_subject', '').strip()
    email_body    = request.form.get('email_body', '').strip()

    descriptions = request.form.getlist('item_description[]')
    amounts      = request.form.getlist('item_amount[]')
    prices       = request.form.getlist('item_price[]')
    discounts    = request.form.getlist('item_discount[]')

    # Basic validation
    if not client_id or not inv_number or not inv_date_str:
        flash('Client, invoice number, and date are required.', 'error')
        return redirect(request.referrer or url_for('invoice_new'))

    valid_items = [(d, a, p, dis) for d, a, p, dis
                   in zip(descriptions, amounts, prices, discounts) if d.strip()]
    if not valid_items:
        flash('At least one invoice item is required.', 'error')
        return redirect(request.referrer or url_for('invoice_new'))

    try:
        inv_date = datetime.strptime(inv_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid invoice date.', 'error')
        return redirect(request.referrer or url_for('invoice_new'))

    del_date = None
    if del_date_str:
        try:
            del_date = datetime.strptime(del_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    # Create or update invoice record
    if invoice is None:
        invoice = Invoice()
        db.session.add(invoice)

    invoice.invoice_number = inv_number
    invoice.client_id      = int(client_id)
    invoice.invoice_date   = inv_date
    invoice.delivery_date  = del_date
    invoice.email_subject  = email_subj
    invoice.email_body     = email_body
    invoice.status         = 'draft'

    # Clear + re-add items
    for item in list(invoice.items):
        db.session.delete(item)
    db.session.flush()

    for desc, amt_s, price_s, disc_s in valid_items:
        try:
            amt   = float(amt_s.replace(',', '.'))  if amt_s  else 1.0
            price = float(price_s.replace(',', '.')) if price_s else 0.0
            disc  = float(disc_s.replace(',', '.'))  if disc_s  else 0.0
        except ValueError:
            continue
        db.session.add(InvoiceItem(
            invoice_id=invoice.id if invoice.id else None,
            description=desc.strip(), amount=amt, price=price, discount=disc
        ))

    db.session.commit()

    # Flush again so items are associated
    for item in invoice.items:
        if item.invoice_id is None:
            item.invoice_id = invoice.id
    db.session.commit()

    if action == 'finalize':
        return _generate_pdf_and_redirect(invoice)

    flash('Invoice saved as draft.', 'success')
    return redirect(url_for('invoices', status='draft'))


def _generate_pdf_and_redirect(invoice):
    """Generate PDF using ReportLab — exact layout, canvas footer at fixed Y coordinates."""
    try:
        ci = company_info()

        PAGE_W, PAGE_H = A4
        M_L   = 20 * mm
        M_R   = 20 * mm
        M_TOP = 15 * mm
        M_BOT = 30 * mm
        CW    = PAGE_W - M_L - M_R   # usable content width

        MID_GRAY  = colors.HexColor('#CCCCCC')
        LIGHT_GRAY = colors.HexColor('#F5F5F5')

        def sty(name, **kw):
            return ParagraphStyle(name, **kw)

        normal       = sty('n',   fontName='Helvetica',      fontSize=9,  leading=13)
        normal_bold  = sty('nb',  fontName='Helvetica-Bold', fontSize=9,  leading=13)
        sender_small = sty('ss',  fontName='Helvetica',      fontSize=7.5, leading=11,
                           textColor=colors.HexColor('#555555'))
        heading      = sty('h',   fontName='Helvetica-Bold', fontSize=22, leading=28)
        r_label      = sty('rl',  fontName='Helvetica',      fontSize=9,  leading=13, alignment=TA_RIGHT)
        r_value      = sty('rv',  fontName='Helvetica-Bold', fontSize=9,  leading=13, alignment=TA_RIGHT)
        th           = sty('th',  fontName='Helvetica-Bold', fontSize=9,  leading=12)
        th_r         = sty('thr', fontName='Helvetica-Bold', fontSize=9,  leading=12, alignment=TA_RIGHT)
        td           = sty('td',  fontName='Helvetica',      fontSize=9,  leading=12)
        td_r         = sty('tdr', fontName='Helvetica',      fontSize=9,  leading=12, alignment=TA_RIGHT)

        story = []

        # ── LOGO ──────────────────────────────────────────────────────────────
        logo_path = os.path.join(BASE_DIR, 'static', 'logo.png')
        if os.path.exists(logo_path):
            img = RLImage(logo_path, width=84*mm, height=33.6*mm, kind='proportional')
            img.hAlign = 'CENTER'
            story.append(img)
        else:
            story.append(Spacer(1, 28*mm))
        story.append(Spacer(1, 8*mm))

        # ── ADDRESS BLOCK (left) + INVOICE META (right) ───────────────────────
        addr = [
            Paragraph(f"{ci['name']} · {ci['address']}", sender_small),
            Paragraph(f"<b>{invoice.client.company_name}</b>", normal_bold),
        ]
        for line in invoice.client.address.split('\n'):
            if line.strip():
                addr.append(Paragraph(line.strip(), normal))

        inv_date = invoice.invoice_date.strftime('%d.%m.%Y')
        del_date = invoice.delivery_date.strftime('%d.%m.%Y') if invoice.delivery_date else inv_date

        meta_tbl = Table([
            [Paragraph('Invoice No.:',    r_label), Paragraph(invoice.invoice_number, r_value)],
            [Paragraph('Invoice Date:',   r_label), Paragraph(inv_date,               r_value)],
            [Paragraph('Delivery Date:',  r_label), Paragraph(del_date,               r_value)],
        ], colWidths=[40*mm, 35*mm])
        meta_tbl.setStyle(TableStyle([
            ('ALIGN',         (0,0), (-1,-1), 'RIGHT'),
            ('VALIGN',        (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING',   (0,0), (-1,-1), 0),
            ('RIGHTPADDING',  (0,0), (-1,-1), 0),
            ('TOPPADDING',    (0,0), (-1,-1), 1),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ]))

        two_col = Table([[addr, meta_tbl]], colWidths=[CW*0.55, CW*0.45])
        two_col.setStyle(TableStyle([
            ('VALIGN',        (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING',   (0,0), (-1,-1), 0),
            ('RIGHTPADDING',  (0,0), (-1,-1), 0),
            ('TOPPADDING',    (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(two_col)
        story.append(Spacer(1, 10*mm))

        # ── HEADING ───────────────────────────────────────────────────────────
        story.append(Paragraph('Invoice', heading))
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(
            'Thank you for your order. We invoice you for the following service:', normal))
        story.append(Spacer(1, 5*mm))

        # ── ITEMS TABLE ───────────────────────────────────────────────────────
        col_w = [CW*0.44, CW*0.12, CW*0.10, CW*0.17, CW*0.17]
        rows = [[
            Paragraph('Description', th),
            Paragraph('Amount', th),
            Paragraph('VAT', th_r),
            Paragraph('Price', th_r),
            Paragraph('Total', th_r),
        ]]
        for item in invoice.items:
            rows.append([
                Paragraph(item.description, td),
                Paragraph(f'{item.amount:.2f}', td),
                Paragraph('19%', td_r),
                Paragraph(fmt(item.price), td_r),
                Paragraph(fmt(item.line_total), td_r),
            ])
        items_tbl = Table(rows, colWidths=col_w)
        items_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), LIGHT_GRAY),
            ('LINEBELOW',     (0,0), (-1,0), 1, MID_GRAY),
            ('TOPPADDING',    (0,0), (-1,0), 5),
            ('BOTTOMPADDING', (0,0), (-1,0), 5),
            ('LEFTPADDING',   (0,0), (-1,-1), 4),
            ('RIGHTPADDING',  (0,0), (-1,-1), 4),
            ('TOPPADDING',    (0,1), (-1,-1), 4),
            ('BOTTOMPADDING', (0,1), (-1,-1), 4),
            ('LINEBELOW',     (0,1), (-1,-1), 0.5, MID_GRAY),
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(items_tbl)
        story.append(Spacer(1, 5*mm))

        # ── TOTALS ────────────────────────────────────────────────────────────
        sum_tbl = Table([
            [Paragraph('Total',          normal_bold), Paragraph(fmt(invoice.total_amount), r_value)],
            [Paragraph('Incl. VAT 19%',  normal),      Paragraph(fmt(invoice.vat_amount),   td_r)],
        ], colWidths=[50*mm, 30*mm])
        sum_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,-1), LIGHT_GRAY),
            ('LINEABOVE',     (0,0), (-1,0),  1, MID_GRAY),
            ('LEFTPADDING',   (0,0), (-1,-1), 6),
            ('RIGHTPADDING',  (0,0), (-1,-1), 6),
            ('TOPPADDING',    (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('ALIGN',         (1,0), (1,-1),  'RIGHT'),
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ]))
        wrapper = Table([[Paragraph('', normal), sum_tbl]],
                        colWidths=[CW - 80*mm, 80*mm])
        wrapper.setStyle(TableStyle([
            ('VALIGN',        (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING',   (0,0), (-1,-1), 0),
            ('RIGHTPADDING',  (0,0), (-1,-1), 0),
            ('TOPPADDING',    (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(wrapper)
        story.append(Spacer(1, 6*mm))

        # ── CLOSING ───────────────────────────────────────────────────────────
        story.append(Paragraph('Due upon receipt of invoice.', normal_bold))
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(
            'Thank you for your order and we look forward to continued cooperation.', normal))

        # ── FOOTER — drawn at exact Y coords, always at physical page bottom ──
        def _draw_footer(canv, _doc):
            canv.saveState()
            y_hr = M_BOT - 5*mm
            canv.setStrokeColor(MID_GRAY)
            canv.setLineWidth(0.5)
            canv.line(M_L, y_hr, PAGE_W - M_R, y_hr)

            LH   = 10          # points between lines
            y0   = y_hr - 5*mm
            col_w_third = CW / 3
            x1 = M_L
            x2 = M_L + col_w_third + col_w_third / 2   # centre of middle column
            x3 = PAGE_W - M_R

            canv.setFillColor(colors.HexColor('#666666'))

            # Col 1 — company
            canv.setFont('Helvetica-Bold', 7.5)
            canv.drawString(x1, y0, ci['name'])
            canv.setFont('Helvetica', 7.5)
            canv.drawString(x1, y0 - LH,   ci['address'])
            canv.drawString(x1, y0 - 2*LH, f"Steuernr.: {ci['tax_number']}")
            if ci.get('vat_id'):
                canv.drawString(x1, y0 - 3*LH, f"USt-IdNr.: {ci['vat_id']}")

            # Col 2 — contact (centred)
            canv.setFont('Helvetica', 7.5)
            canv.drawCentredString(x2, y0,        f"Tel.: {ci['phone']}")
            canv.drawCentredString(x2, y0 - LH,   f"E-Mail: {ci['email']}")
            canv.drawCentredString(x2, y0 - 2*LH, ci['website'])

            # Col 3 — bank (right-aligned)
            canv.setFont('Helvetica-Bold', 7.5)
            canv.drawRightString(x3, y0, ci['bank'])
            canv.setFont('Helvetica', 7.5)
            canv.drawRightString(x3, y0 - LH,   f"IBAN: {ci['iban']}")
            canv.drawRightString(x3, y0 - 2*LH, f"BIC/Swift: {ci['bic']}")

            canv.restoreState()

        # ── BUILD ─────────────────────────────────────────────────────────────
        pdf_filename = f'Invoice_{invoice.invoice_number}.pdf'
        pdf_path     = os.path.join(INVOICE_DIR, pdf_filename)

        doc = SimpleDocTemplate(
            pdf_path, pagesize=A4,
            leftMargin=M_L, rightMargin=M_R,
            topMargin=M_TOP, bottomMargin=M_BOT,
        )
        doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)

        invoice.pdf_path = pdf_path
        db.session.commit()
        flash(f'PDF generated: {pdf_filename}', 'success')
    except Exception as e:
        flash(f'PDF generation failed: {e}', 'error')

    return redirect(url_for('invoice_view', invoice_id=invoice.id))


@app.route('/invoices/<int:invoice_id>')
@login_required
def invoice_view(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    return render_template('invoice_view.html', invoice=inv)


@app.route('/invoices/<int:invoice_id>/regenerate-pdf', methods=['POST'])
@login_required
def invoice_regenerate_pdf(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    return _generate_pdf_and_redirect(inv)


@app.route('/invoices/<int:invoice_id>/send', methods=['POST'])
@login_required
def invoice_send(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)

    if not inv.has_pdf:
        flash('Please finalize the invoice first to generate the PDF.', 'error')
        return redirect(url_for('invoice_view', invoice_id=invoice_id))

    subject    = f"Invoice {inv.invoice_number} — AI Experts"
    html_body  = _build_email_html(inv)

    smtp_host  = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port  = int(os.environ.get('SMTP_PORT', 587))
    smtp_user  = os.environ.get('SMTP_USER', '')
    smtp_pass  = os.environ.get('SMTP_PASSWORD', '')
    from_email = os.environ.get('FROM_EMAIL', smtp_user)

    if not smtp_user or not smtp_pass:
        flash('Email not configured. Set SMTP_USER and SMTP_PASSWORD in .env on the server.', 'error')
        return redirect(url_for('invoice_view', invoice_id=invoice_id))

    try:
        # Structure: mixed → related (html + inline logo) + pdf attachment
        msg = MIMEMultipart('mixed')
        msg['From']    = from_email
        msg['To']      = inv.client.email
        msg['Subject'] = subject

        # related part holds the HTML + inline logo image (CID)
        related = MIMEMultipart('related')

        related.attach(MIMEText(html_body, 'html', 'utf-8'))

        # Attach logo as CID inline image (Gmail-compatible)
        logo_path = os.path.join(BASE_DIR, 'static', 'logo.png')
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                logo_img = MIMEImage(f.read(), _subtype='png')
            logo_img.add_header('Content-ID', '<company_logo>')
            logo_img.add_header('Content-Disposition', 'inline', filename='logo.png')
            related.attach(logo_img)

        msg.attach(related)

        # PDF attachment
        with open(inv.pdf_path, 'rb') as fp:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(fp.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition',
                        f'attachment; filename="Invoice_{inv.invoice_number}.pdf"')
        msg.attach(part)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, inv.client.email, msg.as_string())

        inv.status    = 'sent'
        inv.sent_at   = datetime.utcnow()
        inv.email_subject = subject
        db.session.commit()
        flash(f'Invoice #{inv.invoice_number} sent to {inv.client.email}', 'success')

    except Exception as e:
        flash(f'Email error: {e}', 'error')

    return redirect(url_for('invoice_view', invoice_id=invoice_id))


@app.route('/invoices/<int:invoice_id>/download')
@login_required
def invoice_download(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    if not inv.has_pdf:
        flash('PDF not yet generated.', 'error')
        return redirect(url_for('invoice_view', invoice_id=invoice_id))
    return send_file(inv.pdf_path, as_attachment=True,
                     download_name=f"Invoice_{inv.invoice_number}.pdf")


@app.route('/invoices/<int:invoice_id>/delete', methods=['POST'])
@login_required
def invoice_delete(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    if inv.status != 'draft':
        flash('Only draft invoices can be deleted.', 'error')
        return redirect(url_for('invoice_view', invoice_id=invoice_id))
    if inv.pdf_path and os.path.exists(inv.pdf_path):
        os.remove(inv.pdf_path)
    db.session.delete(inv)
    db.session.commit()
    flash('Draft deleted.', 'success')
    return redirect(url_for('invoices', status='draft'))


# ─── API ──────────────────────────────────────────────────────────────────────

@app.route('/api/next-invoice-number')
@login_required
def api_next_number():
    return jsonify({'number': get_next_invoice_number()})


@app.route('/api/check-invoice-number')
@login_required
def api_check_number():
    number     = request.args.get('number', '')
    exclude_id = request.args.get('exclude_id')
    used = is_invoice_number_sent(number,
           exclude_id=int(exclude_id) if exclude_id else None)
    return jsonify({'used': used})


@app.route('/api/products')
@login_required
def api_products():
    prods = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    return jsonify([{
        'id': p.id, 'name': p.name,
        'description': p.description or p.name,
        'price': p.price
    } for p in prods])


@app.route('/api/default-email/<int:invoice_id>')
@login_required
def api_default_email(invoice_id):
    inv = Invoice.query.get_or_404(invoice_id)
    subj, body = get_default_email(inv)
    return jsonify({'subject': subj, 'body': body})


# ─── INIT ──────────────────────────────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        if Product.query.count() == 0:
            seeds = [
                ('AI Assessment for recruiting agencies',
                 'AI Assessment for recruiting agencies', 2500.0),
                ('AI Assessment for coaches',
                 'AI Assessment for coaches', 2000.0),
                ('Process Automation customer support',
                 'Process Automation customer support', 2500.0),
            ]
            for name, desc, price in seeds:
                db.session.add(Product(name=name, description=desc, price=price))
            db.session.commit()


if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0', port=5001)
