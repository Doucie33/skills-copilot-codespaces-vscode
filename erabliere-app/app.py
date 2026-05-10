import os
import sys
import uuid
import json
import csv
import io
import threading
import webbrowser
from datetime import datetime, date
from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, send_file, flash
)
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import sqlite3

# ── Chemins portables ─────────────────────────────────────────────────────────
# Sur clé USB : app.py est dans  {USB}/Erabliere/app/
#               données dans     {USB}/Erabliere/data/  (partagées Win+Linux)
# En développement : app.py est directement dans erabliere-app/
APP_DIR  = os.path.dirname(os.path.abspath(__file__))
# Détecte si on est dans un sous-dossier "app" (mode clé USB)
if os.path.basename(APP_DIR).lower() == 'app':
    BASE_DIR = os.path.dirname(APP_DIR)      # remonte dans Erabliere/
else:
    BASE_DIR = APP_DIR                        # mode développement
DATA_DIR   = os.path.join(BASE_DIR, 'data')
DB_PATH    = os.path.join(DATA_DIR, 'erabliere.db')
PDF_DIR    = os.path.join(DATA_DIR, 'pdfs')
UPLOAD_DIR = os.path.join(APP_DIR, 'static', 'uploads')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, template_folder=os.path.join(APP_DIR, 'templates'),
            static_folder=os.path.join(APP_DIR, 'static'))
app.secret_key = 'erabliere-maple-secret-2024'
app.jinja_env.globals.update(enumerate=enumerate, now=datetime.now)
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

TPS_RATE = 0.05
TVQ_RATE = 0.09975

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def gen_id(prefix):
    return f"{prefix}-{str(uuid.uuid4())[:8].upper()}"


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS company_settings (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL DEFAULT 'Mon Érablière',
        address TEXT DEFAULT '',
        city TEXT DEFAULT '',
        province TEXT DEFAULT 'QC',
        postal_code TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        website TEXT DEFAULT '',
        logo_path TEXT DEFAULT '',
        tps_number TEXT DEFAULT '',
        tvq_number TEXT DEFAULT '',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('SELECT COUNT(*) FROM company_settings')
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO company_settings (name) VALUES ('Mon Érablière')")

    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subscription_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        price REAL DEFAULT 0,
        duration_days INTEGER DEFAULT 365,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        price REAL NOT NULL DEFAULT 0,
        category TEXT DEFAULT '',
        tax_type TEXT DEFAULT 'tps_tvq',
        description TEXT DEFAULT '',
        unit TEXT DEFAULT 'unité',
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        address TEXT DEFAULT '',
        city TEXT DEFAULT '',
        province TEXT DEFAULT 'QC',
        postal_code TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        subscription_id TEXT DEFAULT '',
        subscription_start DATE,
        subscription_end DATE,
        notes TEXT DEFAULT '',
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        customer_id TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        date DATE NOT NULL,
        subtotal REAL NOT NULL DEFAULT 0,
        tps_amount REAL NOT NULL DEFAULT 0,
        tvq_amount REAL NOT NULL DEFAULT 0,
        total REAL NOT NULL DEFAULT 0,
        status TEXT DEFAULT 'payée',
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT NOT NULL,
        product_id TEXT NOT NULL,
        product_name TEXT NOT NULL,
        quantity REAL NOT NULL DEFAULT 1,
        unit_price REAL NOT NULL DEFAULT 0,
        tax_type TEXT DEFAULT 'tps_tvq',
        tps_amount REAL DEFAULT 0,
        tvq_amount REAL DEFAULT 0,
        line_total REAL NOT NULL DEFAULT 0,
        FOREIGN KEY (invoice_number) REFERENCES invoices(invoice_number)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS accounting_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_number TEXT UNIQUE NOT NULL,
        supplier TEXT NOT NULL,
        description TEXT DEFAULT '',
        date DATE NOT NULL,
        subtotal REAL NOT NULL DEFAULT 0,
        tps_amount REAL DEFAULT 0,
        tvq_amount REAL DEFAULT 0,
        total REAL NOT NULL DEFAULT 0,
        category TEXT DEFAULT 'Fournitures',
        pdf_path TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()


# ─── HELPERS ────────────────────────────────────────────────────────────────

def calc_taxes(price, qty, tax_type):
    subtotal = round(price * qty, 2)
    tps = tvq = 0
    if tax_type in ('tps_tvq', 'tps_only'):
        tps = round(subtotal * TPS_RATE, 2)
    if tax_type in ('tps_tvq', 'tvq_only'):
        tvq = round(subtotal * TVQ_RATE, 2)
    return subtotal, tps, tvq


def row_to_dict(row):
    return dict(row) if row else None


def rows_to_list(rows):
    return [dict(r) for r in rows]


# ─── DASHBOARD ──────────────────────────────────────────────────────────────

@app.route('/')
def dashboard():
    conn = get_db()
    c = conn.cursor()

    today = date.today().isoformat()
    month_start = date.today().replace(day=1).isoformat()
    year_start = date.today().replace(month=1, day=1).isoformat()

    stats = {}

    c.execute('SELECT COUNT(*) FROM customers WHERE active=1')
    stats['total_customers'] = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM products WHERE active=1')
    stats['total_products'] = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM invoices WHERE date=?', (today,))
    stats['invoices_today'] = c.fetchone()[0]

    c.execute('SELECT COALESCE(SUM(total),0) FROM invoices WHERE date=?', (today,))
    stats['sales_today'] = round(c.fetchone()[0], 2)

    c.execute('SELECT COALESCE(SUM(total),0) FROM invoices WHERE date>=?', (month_start,))
    stats['sales_month'] = round(c.fetchone()[0], 2)

    c.execute('SELECT COALESCE(SUM(total),0) FROM invoices WHERE date>=?', (year_start,))
    stats['sales_year'] = round(c.fetchone()[0], 2)

    c.execute('''SELECT ii.product_name, SUM(ii.quantity) as qty
                 FROM invoice_items ii
                 JOIN invoices inv ON inv.invoice_number=ii.invoice_number
                 WHERE inv.date>=?
                 GROUP BY ii.product_id
                 ORDER BY qty DESC LIMIT 5''', (month_start,))
    stats['top_products'] = rows_to_list(c.fetchall())

    c.execute('''SELECT date, SUM(total) as total
                 FROM invoices
                 WHERE date >= date('now','-29 days')
                 GROUP BY date ORDER BY date''')
    chart_data = rows_to_list(c.fetchall())

    c.execute('''SELECT inv.invoice_number, inv.customer_name, inv.date, inv.total, inv.status
                 FROM invoices inv ORDER BY inv.created_at DESC LIMIT 8''')
    recent_invoices = rows_to_list(c.fetchall())

    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()

    return render_template('dashboard.html',
                           stats=stats,
                           chart_data=json.dumps(chart_data),
                           recent_invoices=recent_invoices,
                           company=company)


# ─── SETTINGS ───────────────────────────────────────────────────────────────

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    conn = get_db()
    if request.method == 'POST':
        fields = ['name', 'address', 'city', 'province', 'postal_code',
                  'phone', 'email', 'website', 'tps_number', 'tvq_number']
        data = {f: request.form.get(f, '') for f in fields}

        logo_path = conn.execute('SELECT logo_path FROM company_settings WHERE id=1').fetchone()['logo_path']

        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"logo_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                logo_path = f"uploads/{filename}"

        conn.execute('''UPDATE company_settings SET
            name=?, address=?, city=?, province=?, postal_code=?,
            phone=?, email=?, website=?, tps_number=?, tvq_number=?,
            logo_path=?, updated_at=CURRENT_TIMESTAMP WHERE id=1''',
                     (data['name'], data['address'], data['city'], data['province'],
                      data['postal_code'], data['phone'], data['email'],
                      data['website'], data['tps_number'], data['tvq_number'], logo_path))
        conn.commit()
        flash('Paramètres sauvegardés avec succès.', 'success')
        conn.close()
        return redirect(url_for('settings'))

    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()
    return render_template('settings.html', company=company)


# ─── PRODUCTS ───────────────────────────────────────────────────────────────

@app.route('/products')
def products():
    conn = get_db()
    prods = rows_to_list(conn.execute(
        'SELECT * FROM products ORDER BY category, name').fetchall())
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()
    return render_template('products.html', products=prods, company=company)


@app.route('/api/products', methods=['GET'])
def api_products():
    conn = get_db()
    prods = rows_to_list(conn.execute(
        'SELECT * FROM products WHERE active=1 ORDER BY name').fetchall())
    conn.close()
    return jsonify(prods)


@app.route('/api/products', methods=['POST'])
def api_create_product():
    data = request.json
    conn = get_db()
    pid = gen_id('PRD')
    try:
        conn.execute('''INSERT INTO products
            (product_id, name, price, category, tax_type, description, unit)
            VALUES (?,?,?,?,?,?,?)''',
                     (pid, data['name'], float(data['price']),
                      data.get('category', ''), data.get('tax_type', 'tps_tvq'),
                      data.get('description', ''), data.get('unit', 'unité')))
        conn.commit()
        product = row_to_dict(conn.execute('SELECT * FROM products WHERE product_id=?', (pid,)).fetchone())
        conn.close()
        return jsonify({'success': True, 'product': product})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/products/<product_id>', methods=['PUT'])
def api_update_product(product_id):
    data = request.json
    conn = get_db()
    try:
        conn.execute('''UPDATE products SET
            name=?, price=?, category=?, tax_type=?, description=?, unit=?, active=?
            WHERE product_id=?''',
                     (data['name'], float(data['price']), data.get('category', ''),
                      data.get('tax_type', 'tps_tvq'), data.get('description', ''),
                      data.get('unit', 'unité'), int(data.get('active', 1)), product_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/products/<product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    conn = get_db()
    conn.execute('UPDATE products SET active=0 WHERE product_id=?', (product_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# ─── CUSTOMERS ──────────────────────────────────────────────────────────────

@app.route('/customers')
def customers():
    conn = get_db()
    custs = rows_to_list(conn.execute('''
        SELECT c.*, s.name as subscription_name
        FROM customers c
        LEFT JOIN subscriptions s ON s.subscription_id=c.subscription_id
        ORDER BY c.last_name, c.first_name''').fetchall())
    subs = rows_to_list(conn.execute('SELECT * FROM subscriptions WHERE active=1').fetchall())
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()
    return render_template('customers.html', customers=custs, subscriptions=subs, company=company)


@app.route('/api/customers', methods=['GET'])
def api_customers():
    conn = get_db()
    custs = rows_to_list(conn.execute(
        'SELECT * FROM customers WHERE active=1 ORDER BY last_name, first_name').fetchall())
    conn.close()
    return jsonify(custs)


@app.route('/api/customers', methods=['POST'])
def api_create_customer():
    data = request.json
    conn = get_db()
    cid = gen_id('CLI')
    try:
        conn.execute('''INSERT INTO customers
            (customer_id, first_name, last_name, address, city, province,
             postal_code, phone, email, subscription_id,
             subscription_start, subscription_end, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                     (cid, data['first_name'], data['last_name'],
                      data.get('address', ''), data.get('city', ''),
                      data.get('province', 'QC'), data.get('postal_code', ''),
                      data.get('phone', ''), data.get('email', ''),
                      data.get('subscription_id', ''),
                      data.get('subscription_start') or None,
                      data.get('subscription_end') or None,
                      data.get('notes', '')))
        conn.commit()
        customer = row_to_dict(conn.execute('SELECT * FROM customers WHERE customer_id=?', (cid,)).fetchone())
        conn.close()
        return jsonify({'success': True, 'customer': customer})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/customers/<customer_id>', methods=['PUT'])
def api_update_customer(customer_id):
    data = request.json
    conn = get_db()
    try:
        conn.execute('''UPDATE customers SET
            first_name=?, last_name=?, address=?, city=?, province=?,
            postal_code=?, phone=?, email=?, subscription_id=?,
            subscription_start=?, subscription_end=?, notes=?, active=?
            WHERE customer_id=?''',
                     (data['first_name'], data['last_name'],
                      data.get('address', ''), data.get('city', ''),
                      data.get('province', 'QC'), data.get('postal_code', ''),
                      data.get('phone', ''), data.get('email', ''),
                      data.get('subscription_id', ''),
                      data.get('subscription_start') or None,
                      data.get('subscription_end') or None,
                      data.get('notes', ''), int(data.get('active', 1)),
                      customer_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/customers/<customer_id>', methods=['DELETE'])
def api_delete_customer(customer_id):
    conn = get_db()
    conn.execute('UPDATE customers SET active=0 WHERE customer_id=?', (customer_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/customers/<customer_id>/history')
def customer_history(customer_id):
    conn = get_db()
    customer = row_to_dict(conn.execute(
        'SELECT * FROM customers WHERE customer_id=?', (customer_id,)).fetchone())
    if not customer:
        conn.close()
        return redirect(url_for('customers'))

    invoices = rows_to_list(conn.execute('''
        SELECT * FROM invoices WHERE customer_id=?
        ORDER BY date DESC''', (customer_id,)).fetchall())

    for inv in invoices:
        inv['items'] = rows_to_list(conn.execute(
            'SELECT * FROM invoice_items WHERE invoice_number=?',
            (inv['invoice_number'],)).fetchall())

    c = conn.cursor()
    c.execute('''SELECT ii.product_name, SUM(ii.quantity) as total_qty,
                        SUM(ii.line_total) as total_spent
                 FROM invoice_items ii
                 JOIN invoices inv ON inv.invoice_number=ii.invoice_number
                 WHERE inv.customer_id=?
                 GROUP BY ii.product_id ORDER BY total_qty DESC''', (customer_id,))
    top_products = rows_to_list(c.fetchall())

    sub = None
    if customer.get('subscription_id'):
        sub = row_to_dict(conn.execute(
            'SELECT * FROM subscriptions WHERE subscription_id=?',
            (customer['subscription_id'],)).fetchone())

    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()

    total_spent = sum(inv['total'] for inv in invoices)
    return render_template('customer_history.html',
                           customer=customer, invoices=invoices,
                           top_products=top_products, sub=sub,
                           total_spent=total_spent, company=company)


# ─── SUBSCRIPTIONS ──────────────────────────────────────────────────────────

@app.route('/subscriptions')
def subscriptions():
    conn = get_db()
    subs = rows_to_list(conn.execute('SELECT * FROM subscriptions ORDER BY name').fetchall())
    for s in subs:
        s['customer_count'] = conn.execute(
            'SELECT COUNT(*) FROM customers WHERE subscription_id=? AND active=1',
            (s['subscription_id'],)).fetchone()[0]
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()
    return render_template('subscriptions.html', subscriptions=subs, company=company)


@app.route('/api/subscriptions', methods=['POST'])
def api_create_subscription():
    data = request.json
    conn = get_db()
    sid = gen_id('ABN')
    try:
        conn.execute('''INSERT INTO subscriptions
            (subscription_id, name, description, price, duration_days)
            VALUES (?,?,?,?,?)''',
                     (sid, data['name'], data.get('description', ''),
                      float(data.get('price', 0)), int(data.get('duration_days', 365))))
        conn.commit()
        sub = row_to_dict(conn.execute('SELECT * FROM subscriptions WHERE subscription_id=?', (sid,)).fetchone())
        conn.close()
        return jsonify({'success': True, 'subscription': sub})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/subscriptions/<sub_id>', methods=['PUT'])
def api_update_subscription(sub_id):
    data = request.json
    conn = get_db()
    try:
        conn.execute('''UPDATE subscriptions SET
            name=?, description=?, price=?, duration_days=?, active=?
            WHERE subscription_id=?''',
                     (data['name'], data.get('description', ''),
                      float(data.get('price', 0)), int(data.get('duration_days', 365)),
                      int(data.get('active', 1)), sub_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/subscriptions/<sub_id>', methods=['DELETE'])
def api_delete_subscription(sub_id):
    conn = get_db()
    conn.execute('UPDATE subscriptions SET active=0 WHERE subscription_id=?', (sub_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# ─── INVOICES ───────────────────────────────────────────────────────────────

@app.route('/invoices')
def invoices():
    conn = get_db()
    invs = rows_to_list(conn.execute(
        'SELECT * FROM invoices ORDER BY date DESC, created_at DESC').fetchall())
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()
    return render_template('invoices.html', invoices=invs, company=company)


@app.route('/invoices/create')
def create_invoice():
    conn = get_db()
    customers_list = rows_to_list(conn.execute(
        'SELECT * FROM customers WHERE active=1 ORDER BY last_name, first_name').fetchall())
    products_list = rows_to_list(conn.execute(
        'SELECT * FROM products WHERE active=1 ORDER BY name').fetchall())
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()

    inv_num = f"FAC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
    today = date.today().isoformat()

    return render_template('create_invoice.html',
                           customers=customers_list,
                           products=products_list,
                           company=company,
                           inv_num=inv_num,
                           today=today,
                           tps_rate=TPS_RATE,
                           tvq_rate=TVQ_RATE)


@app.route('/api/invoices', methods=['POST'])
def api_save_invoice():
    data = request.json
    conn = get_db()
    try:
        inv_num = data['invoice_number']
        customer_id = data['customer_id']
        cust = conn.execute('SELECT * FROM customers WHERE customer_id=?', (customer_id,)).fetchone()
        customer_name = f"{cust['first_name']} {cust['last_name']}" if cust else data.get('customer_name', '')

        subtotal = tps_total = tvq_total = 0
        items = data.get('items', [])

        for item in items:
            qty = float(item['quantity'])
            price = float(item['unit_price'])
            sub, tps, tvq = calc_taxes(price, qty, item.get('tax_type', 'tps_tvq'))
            item['_subtotal'] = sub
            item['_tps'] = tps
            item['_tvq'] = tvq
            item['_total'] = round(sub + tps + tvq, 2)
            subtotal += sub
            tps_total += tps
            tvq_total += tvq

        total = round(subtotal + tps_total + tvq_total, 2)
        subtotal = round(subtotal, 2)
        tps_total = round(tps_total, 2)
        tvq_total = round(tvq_total, 2)

        conn.execute('''INSERT INTO invoices
            (invoice_number, customer_id, customer_name, date,
             subtotal, tps_amount, tvq_amount, total, status, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
                     (inv_num, customer_id, customer_name,
                      data.get('date', date.today().isoformat()),
                      subtotal, tps_total, tvq_total, total,
                      data.get('status', 'payée'), data.get('notes', '')))

        for item in items:
            conn.execute('''INSERT INTO invoice_items
                (invoice_number, product_id, product_name, quantity,
                 unit_price, tax_type, tps_amount, tvq_amount, line_total)
                VALUES (?,?,?,?,?,?,?,?,?)''',
                         (inv_num, item['product_id'], item['product_name'],
                          float(item['quantity']), float(item['unit_price']),
                          item.get('tax_type', 'tps_tvq'),
                          item['_tps'], item['_tvq'], item['_total']))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'invoice_number': inv_num})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/invoices/<invoice_number>/view')
def view_invoice(invoice_number):
    conn = get_db()
    inv = row_to_dict(conn.execute(
        'SELECT * FROM invoices WHERE invoice_number=?', (invoice_number,)).fetchone())
    if not inv:
        conn.close()
        return redirect(url_for('invoices'))
    items = rows_to_list(conn.execute(
        'SELECT * FROM invoice_items WHERE invoice_number=?', (invoice_number,)).fetchall())
    customer = row_to_dict(conn.execute(
        'SELECT * FROM customers WHERE customer_id=?', (inv['customer_id'],)).fetchone())
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()
    return render_template('view_invoice.html',
                           invoice=inv, items=items,
                           customer=customer, company=company,
                           tps_rate=TPS_RATE, tvq_rate=TVQ_RATE)


@app.route('/invoices/<invoice_number>/pdf')
def invoice_pdf(invoice_number):
    conn = get_db()
    inv = row_to_dict(conn.execute(
        'SELECT * FROM invoices WHERE invoice_number=?', (invoice_number,)).fetchone())
    items = rows_to_list(conn.execute(
        'SELECT * FROM invoice_items WHERE invoice_number=?', (invoice_number,)).fetchall())
    customer = row_to_dict(conn.execute(
        'SELECT * FROM customers WHERE customer_id=?', (inv['customer_id'],)).fetchone())
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()

    buffer = io.BytesIO()
    _generate_invoice_pdf(buffer, inv, items, customer, company)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True,
                     download_name=f"{invoice_number}.pdf",
                     mimetype='application/pdf')


def _generate_invoice_pdf(buffer, inv, items, customer, company):
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Normal'],
                                  fontSize=18, fontName='Helvetica-Bold',
                                  textColor=colors.HexColor('#2d6a4f'),
                                  spaceAfter=4)
    normal = styles['Normal']
    small = ParagraphStyle('Small', parent=normal, fontSize=8)
    bold = ParagraphStyle('Bold', parent=normal, fontName='Helvetica-Bold')
    right = ParagraphStyle('Right', parent=normal, alignment=TA_RIGHT)
    center = ParagraphStyle('Center', parent=normal, alignment=TA_CENTER)

    header_data = [[
        Paragraph(f"<b>{company.get('name','')}</b><br/>"
                  f"{company.get('address','')} {company.get('city','')}<br/>"
                  f"Tél: {company.get('phone','')} | {company.get('email','')}<br/>"
                  f"TPS: {company.get('tps_number','')} | TVQ: {company.get('tvq_number','')}", small),
        Paragraph(f"<b>FACTURE</b><br/>"
                  f"<font size='9'>N°: {inv['invoice_number']}<br/>"
                  f"Date: {inv['date']}<br/>"
                  f"Statut: {inv['status']}</font>", right)
    ]]

    header_table = Table(header_data, colWidths=[10*cm, 8*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#2d6a4f')),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.4*cm))

    if customer:
        cust_text = (f"<b>Facturer à:</b><br/>"
                     f"{customer.get('first_name','')} {customer.get('last_name','')}<br/>"
                     f"{customer.get('address','')} {customer.get('city','')}<br/>"
                     f"Tél: {customer.get('phone','')}")
        story.append(Paragraph(cust_text, small))
        story.append(Spacer(1, 0.4*cm))

    col_headers = [
        Paragraph('<b>ID</b>', small),
        Paragraph('<b>Désignation</b>', small),
        Paragraph('<b>P.U.</b>', small),
        Paragraph('<b>Qté</b>', small),
        Paragraph('<b>Prix</b>', small),
        Paragraph('<b>Taxe</b>', small),
        Paragraph('<b>Total</b>', small),
    ]
    table_data = [col_headers]
    for item in items:
        tax_label = {'tps_tvq': 'TPS+TVQ', 'tps_only': 'TPS', 'tvq_only': 'TVQ', 'none': 'Aucune'}.get(item['tax_type'], '')
        tax_amt = round(item['tps_amount'] + item['tvq_amount'], 2)
        table_data.append([
            Paragraph(item['product_id'], small),
            Paragraph(item['product_name'], small),
            Paragraph(f"{item['unit_price']:.2f} $", small),
            Paragraph(f"{item['quantity']}", small),
            Paragraph(f"{item['unit_price']*item['quantity']:.2f} $", small),
            Paragraph(f"{tax_amt:.2f} $\n({tax_label})", small),
            Paragraph(f"{item['line_total']:.2f} $", small),
        ])

    items_table = Table(table_data, colWidths=[2.5*cm, 5.5*cm, 2*cm, 1.5*cm, 2*cm, 2.5*cm, 2*cm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d6a4f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f7f4')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.4*cm))

    totals = [
        ['Sous-total:', f"{inv['subtotal']:.2f} $"],
        ['TPS (5%):', f"{inv['tps_amount']:.2f} $"],
        ['TVQ (9.975%):', f"{inv['tvq_amount']:.2f} $"],
        ['TOTAL:', f"{inv['total']:.2f} $"],
    ]
    totals_table = Table(totals, colWidths=[4*cm, 3*cm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 3), (-1, 3), 11),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#2d6a4f')),
        ('TEXTCOLOR', (0, 3), (-1, 3), colors.white),
        ('LINEABOVE', (0, 3), (-1, 3), 1, colors.HexColor('#2d6a4f')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    totals_wrapper = Table([[Paragraph(''), totals_table]], colWidths=[11*cm, 7*cm])
    story.append(totals_wrapper)

    if inv.get('notes'):
        story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph(f"<b>Notes:</b> {inv['notes']}", small))

    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Merci pour votre confiance!", center))

    doc.build(story)


@app.route('/api/invoices/<invoice_number>', methods=['DELETE'])
def api_delete_invoice(invoice_number):
    conn = get_db()
    conn.execute('DELETE FROM invoice_items WHERE invoice_number=?', (invoice_number,))
    conn.execute('DELETE FROM invoices WHERE invoice_number=?', (invoice_number,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/invoices/export/csv')
def export_invoices_csv():
    period = request.args.get('period', 'all')
    year = request.args.get('year', '')
    month = request.args.get('month', '')
    day = request.args.get('day', '')

    conn = get_db()
    query = 'SELECT * FROM invoices WHERE 1=1'
    params = []

    if period == 'day' and day:
        query += ' AND date=?'
        params.append(day)
    elif period == 'month' and year and month:
        query += " AND strftime('%Y-%m', date)=?"
        params.append(f"{year}-{month.zfill(2)}")
    elif period == 'year' and year:
        query += " AND strftime('%Y', date)=?"
        params.append(year)

    query += ' ORDER BY date DESC'
    invs = rows_to_list(conn.execute(query, params).fetchall())
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['N° Facture', 'Client', 'Date', 'Sous-total', 'TPS', 'TVQ', 'Total', 'Statut'])
    for inv in invs:
        writer.writerow([inv['invoice_number'], inv['customer_name'], inv['date'],
                         inv['subtotal'], inv['tps_amount'], inv['tvq_amount'],
                         inv['total'], inv['status']])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='factures.csv')


# ─── SALES HISTORY ──────────────────────────────────────────────────────────

@app.route('/sales')
def sales_history():
    conn = get_db()
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())

    years = rows_to_list(conn.execute(
        "SELECT DISTINCT strftime('%Y', date) as year FROM invoices ORDER BY year DESC").fetchall())
    months = ['01','02','03','04','05','06','07','08','09','10','11','12']

    conn.close()
    return render_template('sales_history.html', company=company,
                           years=years, months=months,
                           current_year=date.today().year,
                           current_month=f"{date.today().month:02d}",
                           current_day=date.today().isoformat())


@app.route('/api/sales/summary')
def api_sales_summary():
    period = request.args.get('period', 'month')
    year = request.args.get('year', str(date.today().year))
    month = request.args.get('month', f"{date.today().month:02d}")
    day = request.args.get('day', date.today().isoformat())

    conn = get_db()
    c = conn.cursor()

    if period == 'day':
        c.execute('''SELECT date, COUNT(*) as count,
                    SUM(subtotal) as subtotal, SUM(tps_amount) as tps,
                    SUM(tvq_amount) as tvq, SUM(total) as total
                    FROM invoices WHERE date=? GROUP BY date''', (day,))
        summary = row_to_dict(c.fetchone())

        c.execute('''SELECT ii.product_name, SUM(ii.quantity) as qty, SUM(ii.line_total) as total
                     FROM invoice_items ii JOIN invoices inv ON inv.invoice_number=ii.invoice_number
                     WHERE inv.date=? GROUP BY ii.product_id ORDER BY qty DESC''', (day,))
        products = rows_to_list(c.fetchall())

        c.execute('SELECT * FROM invoices WHERE date=? ORDER BY created_at DESC', (day,))
        invoices = rows_to_list(c.fetchall())

    elif period == 'month':
        ym = f"{year}-{month}"
        c.execute('''SELECT COUNT(*) as count,
                    SUM(subtotal) as subtotal, SUM(tps_amount) as tps,
                    SUM(tvq_amount) as tvq, SUM(total) as total
                    FROM invoices WHERE strftime('%Y-%m', date)=?''', (ym,))
        summary = row_to_dict(c.fetchone())

        c.execute('''SELECT date, COUNT(*) as count, SUM(total) as total
                     FROM invoices WHERE strftime('%Y-%m', date)=?
                     GROUP BY date ORDER BY date''', (ym,))
        daily_breakdown = rows_to_list(c.fetchall())

        c.execute('''SELECT ii.product_name, SUM(ii.quantity) as qty, SUM(ii.line_total) as total
                     FROM invoice_items ii JOIN invoices inv ON inv.invoice_number=ii.invoice_number
                     WHERE strftime('%Y-%m', inv.date)=? GROUP BY ii.product_id ORDER BY qty DESC''', (ym,))
        products = rows_to_list(c.fetchall())

        c.execute('''SELECT * FROM invoices WHERE strftime('%Y-%m', date)=?
                     ORDER BY date DESC''', (ym,))
        invoices = rows_to_list(c.fetchall())

        conn.close()
        return jsonify({'summary': summary, 'daily_breakdown': daily_breakdown,
                        'products': products, 'invoices': invoices})

    else:  # year
        c.execute('''SELECT COUNT(*) as count,
                    SUM(subtotal) as subtotal, SUM(tps_amount) as tps,
                    SUM(tvq_amount) as tvq, SUM(total) as total
                    FROM invoices WHERE strftime('%Y', date)=?''', (year,))
        summary = row_to_dict(c.fetchone())

        c.execute('''SELECT strftime('%m', date) as month, COUNT(*) as count, SUM(total) as total
                     FROM invoices WHERE strftime('%Y', date)=?
                     GROUP BY month ORDER BY month''', (year,))
        monthly_breakdown = rows_to_list(c.fetchall())

        c.execute('''SELECT ii.product_name, SUM(ii.quantity) as qty, SUM(ii.line_total) as total
                     FROM invoice_items ii JOIN invoices inv ON inv.invoice_number=ii.invoice_number
                     WHERE strftime('%Y', inv.date)=? GROUP BY ii.product_id ORDER BY qty DESC LIMIT 10''', (year,))
        products = rows_to_list(c.fetchall())

        conn.close()
        return jsonify({'summary': summary, 'monthly_breakdown': monthly_breakdown,
                        'products': products})

    conn.close()
    return jsonify({'summary': summary, 'products': products, 'invoices': invoices})


# ─── ACCOUNTING ─────────────────────────────────────────────────────────────

@app.route('/accounting')
def accounting():
    conn = get_db()
    entries = rows_to_list(conn.execute(
        'SELECT * FROM accounting_entries ORDER BY date DESC').fetchall())
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()
    return render_template('accounting.html', entries=entries, company=company)


@app.route('/api/accounting', methods=['POST'])
def api_create_accounting():
    data = request.json
    conn = get_db()
    entry_num = f"ENT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
    try:
        conn.execute('''INSERT INTO accounting_entries
            (entry_number, supplier, description, date, subtotal,
             tps_amount, tvq_amount, total, category)
            VALUES (?,?,?,?,?,?,?,?,?)''',
                     (entry_num, data['supplier'], data.get('description', ''),
                      data['date'], float(data.get('subtotal', 0)),
                      float(data.get('tps_amount', 0)), float(data.get('tvq_amount', 0)),
                      float(data['total']), data.get('category', 'Fournitures')))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'entry_number': entry_num})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/accounting/<entry_id>', methods=['DELETE'])
def api_delete_accounting(entry_id):
    conn = get_db()
    conn.execute('DELETE FROM accounting_entries WHERE id=?', (entry_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/accounting/export/csv')
def export_accounting_csv():
    conn = get_db()
    entries = rows_to_list(conn.execute('SELECT * FROM accounting_entries ORDER BY date DESC').fetchall())
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['N°', 'Fournisseur', 'Description', 'Date', 'Sous-total', 'TPS', 'TVQ', 'Total', 'Catégorie'])
    for e in entries:
        writer.writerow([e['entry_number'], e['supplier'], e['description'],
                         e['date'], e['subtotal'], e['tps_amount'], e['tvq_amount'],
                         e['total'], e['category']])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')),
                     mimetype='text/csv', as_attachment=True,
                     download_name='comptabilite.csv')


# ─── TAX REPORT ─────────────────────────────────────────────────────────────

@app.route('/taxes')
def tax_report():
    conn = get_db()
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    years = rows_to_list(conn.execute(
        "SELECT DISTINCT strftime('%Y', date) as year FROM invoices ORDER BY year DESC").fetchall())
    conn.close()
    return render_template('tax_report.html', company=company, years=years,
                           current_year=date.today().year,
                           current_month=f"{date.today().month:02d}")


@app.route('/api/taxes/report')
def api_tax_report():
    period = request.args.get('period', 'quarter')
    year = request.args.get('year', str(date.today().year))
    month = request.args.get('month', f"{date.today().month:02d}")

    conn = get_db()
    c = conn.cursor()

    if period == 'month':
        ym = f"{year}-{month}"
        where = f"strftime('%Y-%m', date)='{ym}'"
    elif period == 'quarter':
        q_month = int(month)
        q_start = ((q_month - 1) // 3) * 3 + 1
        q_end = q_start + 2
        where = f"strftime('%Y', date)='{year}' AND CAST(strftime('%m', date) AS INTEGER) BETWEEN {q_start} AND {q_end}"
    else:
        where = f"strftime('%Y', date)='{year}'"

    c.execute(f'''SELECT COUNT(*) as invoice_count,
                 SUM(subtotal) as subtotal, SUM(tps_amount) as tps_collected,
                 SUM(tvq_amount) as tvq_collected, SUM(total) as total
                 FROM invoices WHERE {where}''')
    sales = row_to_dict(c.fetchone())

    c.execute(f'''SELECT COUNT(*) as entry_count,
                 SUM(subtotal) as subtotal, SUM(tps_amount) as tps_paid,
                 SUM(tvq_amount) as tvq_paid, SUM(total) as total
                 FROM accounting_entries WHERE {where}''')
    expenses = row_to_dict(c.fetchone())

    conn.close()

    tps_net = round((sales.get('tps_collected') or 0) - (expenses.get('tps_paid') or 0), 2)
    tvq_net = round((sales.get('tvq_collected') or 0) - (expenses.get('tvq_paid') or 0), 2)

    return jsonify({
        'sales': sales,
        'expenses': expenses,
        'tps_net': tps_net,
        'tvq_net': tvq_net,
        'total_net': round(tps_net + tvq_net, 2)
    })


# ─── BEST SELLERS ────────────────────────────────────────────────────────────

@app.route('/api/products/bestsellers')
def api_bestsellers():
    period = request.args.get('period', 'all')
    year = request.args.get('year', str(date.today().year))

    conn = get_db()
    if period == 'year':
        rows = rows_to_list(conn.execute('''
            SELECT ii.product_id, ii.product_name,
                   SUM(ii.quantity) as total_qty, SUM(ii.line_total) as total_revenue
            FROM invoice_items ii
            JOIN invoices inv ON inv.invoice_number=ii.invoice_number
            WHERE strftime('%Y', inv.date)=?
            GROUP BY ii.product_id ORDER BY total_qty DESC LIMIT 10''', (year,)).fetchall())
    else:
        rows = rows_to_list(conn.execute('''
            SELECT ii.product_id, ii.product_name,
                   SUM(ii.quantity) as total_qty, SUM(ii.line_total) as total_revenue
            FROM invoice_items ii
            GROUP BY ii.product_id ORDER BY total_qty DESC LIMIT 10''').fetchall())
    conn.close()
    return jsonify(rows)


def open_browser():
    """Ouvre le navigateur automatiquement après démarrage du serveur."""
    import time
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    init_db()
    # En mode portable (USB), on ouvre le navigateur automatiquement
    if not os.environ.get('ERABLIERE_NO_BROWSER'):
        t = threading.Thread(target=open_browser, daemon=True)
        t.start()
    print("\n" + "="*50)
    print("  ÉRABLIÈRE — Logiciel de gestion")
    print("="*50)
    print(f"  Adresse : http://localhost:5000")
    print(f"  Données : {DATA_DIR}")
    print("  Appuyez sur Ctrl+C pour quitter.")
    print("="*50 + "\n")
    app.run(debug=False, host='127.0.0.1', port=5000)
