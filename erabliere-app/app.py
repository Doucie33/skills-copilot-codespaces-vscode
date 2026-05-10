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
# lancer.py définit ERABLIERE_DATA_DIR pour pointer vers la clé USB.
# En développement direct, les données restent dans erabliere-app/data/.
APP_DIR  = os.path.dirname(os.path.abspath(__file__))
if os.environ.get('ERABLIERE_DATA_DIR'):
    DATA_DIR = os.environ['ERABLIERE_DATA_DIR']
elif os.path.basename(APP_DIR).lower() == 'app':
    DATA_DIR = os.path.join(os.path.dirname(APP_DIR), 'data')
else:
    DATA_DIR = os.path.join(APP_DIR, 'data')
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


def gen_sequential_id(conn, counter_name, prefix, padding=4):
    """Génère un ID séquentiel : PRD-0001, FAC-20260510-0001, etc."""
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO id_counters (name, value) VALUES (?,0)", (counter_name,))
    c.execute("UPDATE id_counters SET value=value+1 WHERE name=?", (counter_name,))
    val = c.execute("SELECT value FROM id_counters WHERE name=?", (counter_name,)).fetchone()[0]
    return f"{prefix}-{val:0{padding}d}"

def gen_product_id(conn):
    return gen_sequential_id(conn, 'product', 'PRD')

def gen_customer_id(conn):
    return gen_sequential_id(conn, 'customer', 'CLI')

def gen_subscription_id(conn):
    return gen_sequential_id(conn, 'subscription', 'ABN')

def gen_invoice_id(conn):
    today = date.today().strftime('%Y%m%d')
    return gen_sequential_id(conn, f'invoice_{today}', f'FAC-{today}')

def gen_accounting_id(conn):
    return gen_sequential_id(conn, 'accounting', 'ENT')

def gen_supplier_id(conn):
    return gen_sequential_id(conn, 'supplier', 'FRN')


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS id_counters (
        name TEXT PRIMARY KEY,
        value INTEGER DEFAULT 0
    )''')

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
        discount_type TEXT DEFAULT 'none',
        discount_value REAL DEFAULT 0,
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
        discount_label TEXT DEFAULT '',
        discount_amount REAL DEFAULT 0,
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

    c.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        contact_name TEXT DEFAULT '',
        address TEXT DEFAULT '',
        city TEXT DEFAULT '',
        province TEXT DEFAULT 'QC',
        postal_code TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS accounting_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_number TEXT UNIQUE NOT NULL,
        supplier_id TEXT DEFAULT '',
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

    c.execute('''CREATE TABLE IF NOT EXISTS production_seasons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        season_id TEXT UNIQUE NOT NULL,
        year INTEGER NOT NULL,
        start_date DATE,
        end_date DATE,
        total_sap_liters REAL DEFAULT 0,
        total_syrup_liters REAL DEFAULT 0,
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS production_batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id TEXT UNIQUE NOT NULL,
        season_id TEXT NOT NULL,
        date DATE NOT NULL,
        sap_liters REAL NOT NULL DEFAULT 0,
        syrup_liters REAL NOT NULL DEFAULT 0,
        ratio REAL DEFAULT 0,
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    _migrate_db(conn)
    conn.close()


def _migrate_db(conn):
    """Ajoute les nouvelles tables et colonnes aux bases existantes."""
    c = conn.cursor()
    table_migrations = [
        "CREATE TABLE IF NOT EXISTS id_counters (name TEXT PRIMARY KEY, value INTEGER DEFAULT 0)",
        """CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            contact_name TEXT DEFAULT '',
            address TEXT DEFAULT '',
            city TEXT DEFAULT '',
            province TEXT DEFAULT 'QC',
            postal_code TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]
    col_migrations = [
        ("subscriptions", "discount_type", "TEXT DEFAULT 'none'"),
        ("subscriptions", "discount_value", "REAL DEFAULT 0"),
        ("invoices", "discount_label", "TEXT DEFAULT ''"),
        ("invoices", "discount_amount", "REAL DEFAULT 0"),
        ("invoices", "payment_date", "DATE DEFAULT NULL"),
        ("invoices", "payment_method", "TEXT DEFAULT ''"),
        ("accounting_entries", "supplier_id", "TEXT DEFAULT ''"),
        ("products", "stock_quantity", "REAL DEFAULT 0"),
        ("products", "stock_alert_threshold", "REAL DEFAULT 0"),
    ]
    table_migrations_extra = [
        """CREATE TABLE IF NOT EXISTS production_seasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_id TEXT UNIQUE NOT NULL,
            year INTEGER NOT NULL,
            start_date DATE,
            end_date DATE,
            total_sap_liters REAL DEFAULT 0,
            total_syrup_liters REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS production_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT UNIQUE NOT NULL,
            season_id TEXT NOT NULL,
            date DATE NOT NULL,
            sap_liters REAL NOT NULL DEFAULT 0,
            syrup_liters REAL NOT NULL DEFAULT 0,
            ratio REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]
    for sql in table_migrations_extra:
        try:
            c.execute(sql)
        except Exception:
            pass
    for sql in table_migrations:
        try:
            c.execute(sql)
        except Exception:
            pass
    for table, col, typ in col_migrations:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        except Exception:
            pass
    conn.commit()


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

    c.execute('''SELECT product_id, name, stock_quantity, stock_alert_threshold, unit
                 FROM products
                 WHERE active=1 AND stock_alert_threshold > 0 AND stock_quantity <= stock_alert_threshold
                 ORDER BY stock_quantity ASC''')
    stock_alerts = rows_to_list(c.fetchall())

    c.execute("SELECT COUNT(*) FROM invoices WHERE status='en attente'")
    stats['pending_invoices'] = c.fetchone()[0]

    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()

    return render_template('dashboard.html',
                           stats=stats,
                           chart_data=json.dumps(chart_data),
                           recent_invoices=recent_invoices,
                           stock_alerts=stock_alerts,
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
    pid = gen_product_id(conn)
    try:
        conn.execute('''INSERT INTO products
            (product_id, name, price, category, tax_type, description, unit, stock_quantity, stock_alert_threshold)
            VALUES (?,?,?,?,?,?,?,?,?)''',
                     (pid, data['name'], float(data['price']),
                      data.get('category', ''), data.get('tax_type', 'tps_tvq'),
                      data.get('description', ''), data.get('unit', 'unité'),
                      float(data.get('stock_quantity', 0)),
                      float(data.get('stock_alert_threshold', 0))))
        conn.commit()
        product = row_to_dict(conn.execute('SELECT * FROM products WHERE product_id=?', (pid,)).fetchone())
        conn.close()
        return jsonify({'success': True, 'product': product})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/products/bulk-price-update', methods=['POST'])
def api_bulk_price_update():
    """Mise à jour groupée des prix en $ ou en %."""
    data = request.json
    conn = get_db()
    try:
        ids = data.get('product_ids', [])
        update_type = data.get('update_type', 'percent')  # 'percent' or 'fixed'
        value = float(data.get('value', 0))

        if ids == 'all':
            products = rows_to_list(conn.execute('SELECT * FROM products WHERE active=1').fetchall())
        else:
            products = rows_to_list(conn.execute(
                f"SELECT * FROM products WHERE product_id IN ({','.join(['?']*len(ids))})", ids).fetchall())

        updated = []
        for p in products:
            old_price = p['price']
            if update_type == 'percent':
                new_price = round(old_price * (1 + value / 100), 2)
            else:
                new_price = round(old_price + value, 2)
            new_price = max(0, new_price)
            conn.execute('UPDATE products SET price=? WHERE product_id=?', (new_price, p['product_id']))
            updated.append({'product_id': p['product_id'], 'name': p['name'],
                            'old_price': old_price, 'new_price': new_price})

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'updated': updated, 'count': len(updated)})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/products/<product_id>', methods=['PUT'])
def api_update_product(product_id):
    data = request.json
    conn = get_db()
    try:
        conn.execute('''UPDATE products SET
            name=?, price=?, category=?, tax_type=?, description=?, unit=?, active=?,
            stock_quantity=?, stock_alert_threshold=?
            WHERE product_id=?''',
                     (data['name'], float(data['price']), data.get('category', ''),
                      data.get('tax_type', 'tps_tvq'), data.get('description', ''),
                      data.get('unit', 'unité'), int(data.get('active', 1)),
                      float(data.get('stock_quantity', 0)),
                      float(data.get('stock_alert_threshold', 0)),
                      product_id))
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


@app.route('/api/customers/<customer_id>/subscription', methods=['GET'])
def api_customer_subscription(customer_id):
    """Retourne les infos d'abonnement d'un client pour la facturation."""
    conn = get_db()
    cust = row_to_dict(conn.execute('SELECT * FROM customers WHERE customer_id=?', (customer_id,)).fetchone())
    if not cust or not cust.get('subscription_id'):
        conn.close()
        return jsonify({'has_subscription': False})
    sub = row_to_dict(conn.execute('SELECT * FROM subscriptions WHERE subscription_id=?',
                                   (cust['subscription_id'],)).fetchone())
    conn.close()
    if sub and sub.get('discount_type', 'none') != 'none':
        return jsonify({'has_subscription': True, 'subscription': sub})
    return jsonify({'has_subscription': False, 'subscription': sub})


@app.route('/api/customers', methods=['POST'])
def api_create_customer():
    data = request.json
    conn = get_db()
    cid = gen_customer_id(conn)
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
    try:
        conn = get_db()
        customer = row_to_dict(conn.execute(
            'SELECT * FROM customers WHERE customer_id=?', (customer_id,)).fetchone())
        if not customer:
            conn.close()
            return redirect(url_for('customers'))

        invoices = rows_to_list(conn.execute(
            'SELECT * FROM invoices WHERE customer_id=? ORDER BY date DESC',
            (customer_id,)).fetchall())

        for inv in invoices:
            inv['items'] = rows_to_list(conn.execute(
                'SELECT * FROM invoice_items WHERE invoice_number=?',
                (inv['invoice_number'],)).fetchall())
            inv.setdefault('discount_amount', 0)
            inv.setdefault('discount_label', '')

        top_products = rows_to_list(conn.execute('''
            SELECT ii.product_name,
                   SUM(ii.quantity) as total_qty,
                   SUM(ii.line_total) as total_spent
            FROM invoice_items ii
            JOIN invoices inv ON inv.invoice_number=ii.invoice_number
            WHERE inv.customer_id=?
            GROUP BY ii.product_id, ii.product_name
            ORDER BY total_qty DESC
        ''', (customer_id,)).fetchall())

        sub = None
        if customer.get('subscription_id'):
            sub = row_to_dict(conn.execute(
                'SELECT * FROM subscriptions WHERE subscription_id=?',
                (customer['subscription_id'],)).fetchone())

        company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
        conn.close()

        total_spent = sum(float(inv.get('total', 0)) for inv in invoices)
        return render_template('customer_history.html',
                               customer=customer, invoices=invoices,
                               top_products=top_products, sub=sub,
                               total_spent=total_spent, company=company)
    except Exception as e:
        app.logger.error(f"customer_history error: {e}")
        return f"<h2>Erreur serveur</h2><pre>{e}</pre><a href='/customers'>Retour</a>", 500


# ─── SUPPLIERS ───────────────────────────────────────────────────────────────

@app.route('/suppliers')
def suppliers():
    conn = get_db()
    sups = rows_to_list(conn.execute('SELECT * FROM suppliers WHERE active=1 ORDER BY name').fetchall())
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()
    return render_template('suppliers.html', suppliers=sups, company=company)

@app.route('/api/suppliers', methods=['GET'])
def api_suppliers():
    conn = get_db()
    sups = rows_to_list(conn.execute('SELECT * FROM suppliers WHERE active=1 ORDER BY name').fetchall())
    conn.close()
    return jsonify(sups)

@app.route('/api/suppliers', methods=['POST'])
def api_create_supplier():
    data = request.json
    conn = get_db()
    try:
        sid = gen_supplier_id(conn)
        conn.execute('''INSERT INTO suppliers
            (supplier_id, name, contact_name, address, city, province,
             postal_code, phone, email, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
                     (sid, data['name'], data.get('contact_name', ''),
                      data.get('address', ''), data.get('city', ''),
                      data.get('province', 'QC'), data.get('postal_code', ''),
                      data.get('phone', ''), data.get('email', ''),
                      data.get('notes', '')))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'supplier_id': sid})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/suppliers/<sup_id>', methods=['PUT'])
def api_update_supplier(sup_id):
    data = request.json
    conn = get_db()
    try:
        conn.execute('''UPDATE suppliers SET
            name=?, contact_name=?, address=?, city=?, province=?,
            postal_code=?, phone=?, email=?, notes=?, active=?
            WHERE supplier_id=?''',
                     (data['name'], data.get('contact_name', ''),
                      data.get('address', ''), data.get('city', ''),
                      data.get('province', 'QC'), data.get('postal_code', ''),
                      data.get('phone', ''), data.get('email', ''),
                      data.get('notes', ''), int(data.get('active', 1)), sup_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/suppliers/<sup_id>', methods=['DELETE'])
def api_delete_supplier(sup_id):
    conn = get_db()
    conn.execute('UPDATE suppliers SET active=0 WHERE supplier_id=?', (sup_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

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
    sid = gen_subscription_id(conn)
    try:
        conn.execute('''INSERT INTO subscriptions
            (subscription_id, name, description, price, duration_days, discount_type, discount_value)
            VALUES (?,?,?,?,?,?,?)''',
                     (sid, data['name'], data.get('description', ''),
                      float(data.get('price', 0)), int(data.get('duration_days', 365)),
                      data.get('discount_type', 'none'), float(data.get('discount_value', 0))))
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
            name=?, description=?, price=?, duration_days=?,
            discount_type=?, discount_value=?, active=?
            WHERE subscription_id=?''',
                     (data['name'], data.get('description', ''),
                      float(data.get('price', 0)), int(data.get('duration_days', 365)),
                      data.get('discount_type', 'none'), float(data.get('discount_value', 0)),
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
    subscriptions_map = {s['subscription_id']: s for s in rows_to_list(
        conn.execute('SELECT * FROM subscriptions WHERE active=1').fetchall())}
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    inv_num = gen_invoice_id(conn)
    conn.commit()
    conn.close()
    today = date.today().isoformat()
    return render_template('create_invoice.html',
                           customers=customers_list,
                           products=products_list,
                           subscriptions_map=subscriptions_map,
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

        subtotal = round(subtotal, 2)

        # Rabais d'abonnement (appliqué avant les taxes)
        discount_label = data.get('discount_label', '')
        discount_amount = round(float(data.get('discount_amount', 0)), 2)

        if discount_amount > 0:
            # Recalculer les taxes sur le montant net
            net = subtotal - discount_amount
            ratio = net / subtotal if subtotal > 0 else 1
            tps_total = round(tps_total * ratio, 2)
            tvq_total = round(tvq_total * ratio, 2)

        tps_total = round(tps_total, 2)
        tvq_total = round(tvq_total, 2)
        total = round(subtotal - discount_amount + tps_total + tvq_total, 2)

        inv_status = data.get('status', 'payée')
        payment_date = data.get('payment_date', '') or None
        payment_method = data.get('payment_method', '')
        if inv_status == 'payée' and not payment_date:
            payment_date = data.get('date', date.today().isoformat())

        conn.execute('''INSERT INTO invoices
            (invoice_number, customer_id, customer_name, date,
             subtotal, discount_label, discount_amount,
             tps_amount, tvq_amount, total, status, notes, payment_date, payment_method)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                     (inv_num, customer_id, customer_name,
                      data.get('date', date.today().isoformat()),
                      subtotal, discount_label, discount_amount,
                      tps_total, tvq_total, total,
                      inv_status, data.get('notes', ''),
                      payment_date, payment_method))

        for item in items:
            conn.execute('''INSERT INTO invoice_items
                (invoice_number, product_id, product_name, quantity,
                 unit_price, tax_type, tps_amount, tvq_amount, line_total)
                VALUES (?,?,?,?,?,?,?,?,?)''',
                         (inv_num, item['product_id'], item['product_name'],
                          float(item['quantity']), float(item['unit_price']),
                          item.get('tax_type', 'tps_tvq'),
                          item['_tps'], item['_tvq'], item['_total']))
            # Déduire du stock
            conn.execute('''UPDATE products
                SET stock_quantity = MAX(0, stock_quantity - ?)
                WHERE product_id=?''',
                         (float(item['quantity']), item['product_id']))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'invoice_number': inv_num})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/invoices/<invoice_number>/edit')
def edit_invoice(invoice_number):
    conn = get_db()
    inv = row_to_dict(conn.execute(
        'SELECT * FROM invoices WHERE invoice_number=?', (invoice_number,)).fetchone())
    if not inv:
        conn.close()
        return redirect(url_for('invoices'))
    items = rows_to_list(conn.execute(
        'SELECT * FROM invoice_items WHERE invoice_number=?', (invoice_number,)).fetchall())
    customers = rows_to_list(conn.execute(
        'SELECT * FROM customers WHERE active=1 ORDER BY last_name, first_name').fetchall())
    products = rows_to_list(conn.execute(
        'SELECT * FROM products WHERE active=1 ORDER BY name').fetchall())
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()
    return render_template('edit_invoice.html',
                           invoice=inv, items=items,
                           customers=customers, products=products,
                           company=company, tps_rate=TPS_RATE, tvq_rate=TVQ_RATE)

@app.route('/api/invoices/<invoice_number>', methods=['PUT'])
def api_update_invoice(invoice_number):
    data = request.json
    conn = get_db()
    try:
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

        subtotal = round(subtotal, 2)
        discount_label = data.get('discount_label', '')
        discount_amount = round(float(data.get('discount_amount', 0)), 2)

        if discount_amount > 0 and subtotal > 0:
            ratio = (subtotal - discount_amount) / subtotal
            tps_total = round(tps_total * ratio, 2)
            tvq_total = round(tvq_total * ratio, 2)

        tps_total = round(tps_total, 2)
        tvq_total = round(tvq_total, 2)
        total = round(subtotal - discount_amount + tps_total + tvq_total, 2)

        inv_status = data.get('status', 'en attente')
        payment_date = data.get('payment_date', '') or None
        payment_method = data.get('payment_method', '')
        if inv_status == 'payée' and not payment_date:
            payment_date = data.get('date', date.today().isoformat())

        conn.execute('''UPDATE invoices SET
            customer_id=?, customer_name=?, date=?,
            subtotal=?, discount_label=?, discount_amount=?,
            tps_amount=?, tvq_amount=?, total=?, status=?, notes=?,
            payment_date=?, payment_method=?
            WHERE invoice_number=?''',
                     (customer_id, customer_name, data.get('date'),
                      subtotal, discount_label, discount_amount,
                      tps_total, tvq_total, total,
                      inv_status, data.get('notes', ''),
                      payment_date, payment_method,
                      invoice_number))

        conn.execute('DELETE FROM invoice_items WHERE invoice_number=?', (invoice_number,))
        for item in items:
            conn.execute('''INSERT INTO invoice_items
                (invoice_number, product_id, product_name, quantity,
                 unit_price, tax_type, tps_amount, tvq_amount, line_total)
                VALUES (?,?,?,?,?,?,?,?,?)''',
                         (invoice_number, item['product_id'], item['product_name'],
                          float(item['quantity']), float(item['unit_price']),
                          item.get('tax_type', 'tps_tvq'),
                          item['_tps'], item['_tvq'], item['_total']))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'invoice_number': invoice_number})
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
    GREEN      = colors.HexColor('#2d6a4f')
    GREEN_DARK = colors.HexColor('#1b4332')
    GREEN_PALE = colors.HexColor('#f0f7f4')
    GREY_LINE  = colors.HexColor('#e2e8f0')
    WHITE      = colors.white

    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story  = []

    def S(size=8, bold=False, align=TA_LEFT, color=colors.black):
        return ParagraphStyle('s', parent=styles['Normal'], fontSize=size,
                              fontName='Helvetica-Bold' if bold else 'Helvetica',
                              alignment=align, textColor=color, leading=size+3)

    # ── En-tête ──────────────────────────────────────────────────────────────
    logo_cell = ''
    if company.get('logo_path'):
        logo_path = os.path.join(APP_DIR, 'static', company['logo_path'])
        if os.path.exists(logo_path):
            try: logo_cell = RLImage(logo_path, width=3.5*cm, height=1.5*cm, kind='proportional')
            except: pass

    company_text = (f"<b>{company.get('name','')}</b><br/>"
                    f"{company.get('address','')} {company.get('city','')} {company.get('province','')}<br/>"
                    f"Tél : {company.get('phone','')}  |  {company.get('email','')}<br/>"
                    f"TPS : {company.get('tps_number','—')}  |  TVQ : {company.get('tvq_number','—')}")

    inv_box_text = (f"<b>FACTURE</b><br/>"
                    f"<font size='8'>N° : {inv['invoice_number']}<br/>"
                    f"Date : {inv['date']}<br/>"
                    f"Statut : {inv['status']}</font>")

    header = Table([[
        [logo_cell if logo_cell else '', Paragraph(company_text, S(8))],
        Paragraph(inv_box_text, S(14, bold=True, align=TA_RIGHT, color=WHITE)),
    ]], colWidths=[10*cm, 7.5*cm])

    # Redesign simple : deux colonnes côte à côte
    hdr_data = [[
        Paragraph(company_text, S(8)),
        Paragraph(inv_box_text, S(9, align=TA_RIGHT)),
    ]]
    hdr_table = Table(hdr_data, colWidths=[10*cm, 7.5*cm])
    hdr_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (1,0), (1,0), GREEN),
        ('TEXTCOLOR', (1,0), (1,0), WHITE),
        ('LEFTPADDING', (1,0), (1,0), 10),
        ('RIGHTPADDING', (1,0), (1,0), 10),
        ('TOPPADDING', (1,0), (1,0), 8),
        ('BOTTOMPADDING', (1,0), (1,0), 8),
        ('ROUNDEDCORNERS', [8]),
        ('LINEBELOW', (0,0), (0,0), 1, GREEN),
        ('BOTTOMPADDING', (0,0), (0,0), 8),
    ]))
    story.append(hdr_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Adresse client ───────────────────────────────────────────────────────
    if customer:
        cust_lines = [f"<b>FACTURER À :</b>",
                      f"<b>{customer.get('first_name','')} {customer.get('last_name','')}</b>"]
        if customer.get('address'): cust_lines.append(customer['address'])
        if customer.get('city'):    cust_lines.append(f"{customer['city']} {customer.get('province','')}")
        if customer.get('phone'):   cust_lines.append(f"Tél : {customer['phone']}")
        if customer.get('email'):   cust_lines.append(customer['email'])
        cust_data = [[Paragraph('<br/>'.join(cust_lines), S(8)), '']]
        cust_table = Table(cust_data, colWidths=[9*cm, 8.5*cm])
        cust_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), GREEN_PALE),
            ('LEFTPADDING', (0,0), (0,0), 10),
            ('TOPPADDING', (0,0), (0,0), 8),
            ('BOTTOMPADDING', (0,0), (0,0), 8),
            ('LINEAFTER', (0,0), (0,0), 3, GREEN),
        ]))
        story.append(cust_table)
        story.append(Spacer(1, 0.4*cm))

    # ── Tableau des produits ─────────────────────────────────────────────────
    tax_labels = {'tps_tvq':'TPS+TVQ','tps_only':'TPS','tvq_only':'TVQ','none':'—'}
    th = S(8, bold=True, color=WHITE)
    td = S(8)
    tdr = S(8, align=TA_RIGHT)

    rows = [[Paragraph(h, th) for h in ['ID', 'Désignation', 'P.U.', 'Qté', 'Prix', 'Taxe', 'Total']]]
    for item in items:
        tax_amt = round((item.get('tps_amount') or 0) + (item.get('tvq_amount') or 0), 2)
        prix    = round((item['unit_price'] or 0) * (item['quantity'] or 0), 2)
        rows.append([
            Paragraph(item['product_id'], td),
            Paragraph(item['product_name'], td),
            Paragraph(f"{item['unit_price']:.2f} $", tdr),
            Paragraph(str(item['quantity']), S(8, align=TA_CENTER)),
            Paragraph(f"{prix:.2f} $", tdr),
            Paragraph(f"{tax_amt:.2f} $<br/><font size='7'>{tax_labels.get(item['tax_type'],'')}</font>", tdr),
            Paragraph(f"<b>{item['line_total']:.2f} $</b>", tdr),
        ])

    col_w = [2.2*cm, 5.8*cm, 1.9*cm, 1.3*cm, 1.9*cm, 2.2*cm, 2.2*cm]
    items_table = Table(rows, colWidths=col_w, repeatRows=1)
    row_bgs = [WHITE, GREEN_PALE] * (len(rows) + 1)
    items_table.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,0), GREEN),
        ('TEXTCOLOR',   (0,0), (-1,0), WHITE),
        ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, GREEN_PALE]),
        ('GRID',        (0,0), (-1,-1), 0.3, GREY_LINE),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('ALIGN',       (2,0), (-1,-1), 'RIGHT'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Totaux ───────────────────────────────────────────────────────────────
    totals_rows = [['Sous-total :', f"{inv['subtotal']:.2f} $"]]
    discount_amount = inv.get('discount_amount') or 0
    if discount_amount > 0:
        lbl = inv.get('discount_label') or 'Rabais'
        totals_rows.append([lbl + ' :', f"-{discount_amount:.2f} $"])
    totals_rows.append(['TPS (5 %) :', f"{inv['tps_amount']:.2f} $"])
    totals_rows.append(['TVQ (9,975 %) :', f"{inv['tvq_amount']:.2f} $"])
    totals_rows.append(['TOTAL :', f"{inv['total']:.2f} $"])
    total_row_idx = len(totals_rows) - 1

    tot_table = Table([[Paragraph(k, S(8, align=TA_RIGHT)), Paragraph(v, S(8, align=TA_RIGHT))]
                       for k,v in totals_rows], colWidths=[4.5*cm, 3*cm])
    style_cmds = [
        ('ALIGN',         (0,0), (-1,-1), 'RIGHT'),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LINEABOVE',     (0, total_row_idx), (-1, total_row_idx), 1, GREEN),
        ('BACKGROUND',    (0, total_row_idx), (-1, total_row_idx), GREEN_DARK),
        ('TEXTCOLOR',     (0, total_row_idx), (-1, total_row_idx), WHITE),
        ('FONTNAME',      (0, total_row_idx), (-1, total_row_idx), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, total_row_idx), (-1, total_row_idx), 10),
    ]
    if discount_amount > 0:
        style_cmds.append(('TEXTCOLOR', (0,1), (-1,1), colors.HexColor('#dc2626')))
    tot_table.setStyle(TableStyle(style_cmds))

    wrap = Table([[Paragraph('', S(8)), tot_table]], colWidths=[10*cm, 7.5*cm])
    story.append(wrap)

    if inv.get('notes'):
        story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph(f"<b>Notes :</b> {inv['notes']}", S(8)))

    story.append(Spacer(1, 1.2*cm))
    story.append(Paragraph("— Merci pour votre confiance ! —", S(9, align=TA_CENTER, color=GREEN)))
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
    sups = rows_to_list(conn.execute(
        'SELECT * FROM suppliers WHERE active=1 ORDER BY name').fetchall())
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()
    return render_template('accounting.html', entries=entries, suppliers=sups, company=company)


@app.route('/api/accounting', methods=['POST'])
def api_create_accounting():
    data = request.json
    conn = get_db()
    entry_num = gen_accounting_id(conn)
    try:
        supplier_id = data.get('supplier_id', '')
        supplier_name = data.get('supplier', '')
        if supplier_id:
            sup = conn.execute('SELECT name FROM suppliers WHERE supplier_id=?', (supplier_id,)).fetchone()
            if sup:
                supplier_name = sup['name']
        conn.execute('''INSERT INTO accounting_entries
            (entry_number, supplier_id, supplier, description, date, subtotal,
             tps_amount, tvq_amount, total, category)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
                     (entry_num, supplier_id, supplier_name, data.get('description', ''),
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


# ─── PRODUCTION ──────────────────────────────────────────────────────────────

def gen_season_id(conn):
    return gen_sequential_id(conn, 'season', 'SAI')

def gen_batch_id(conn):
    return gen_sequential_id(conn, 'batch', 'LOT')


@app.route('/production')
def production():
    conn = get_db()
    seasons = rows_to_list(conn.execute(
        'SELECT * FROM production_seasons ORDER BY year DESC, start_date DESC').fetchall())
    for s in seasons:
        s['batches'] = rows_to_list(conn.execute(
            'SELECT * FROM production_batches WHERE season_id=? ORDER BY date', (s['season_id'],)).fetchall())
    company = row_to_dict(conn.execute('SELECT * FROM company_settings WHERE id=1').fetchone())
    conn.close()
    return render_template('production.html', seasons=seasons, company=company,
                           current_year=date.today().year)


@app.route('/api/production/seasons', methods=['GET'])
def api_production_seasons():
    conn = get_db()
    rows = rows_to_list(conn.execute(
        'SELECT * FROM production_seasons ORDER BY year DESC').fetchall())
    conn.close()
    return jsonify(rows)


@app.route('/api/production/seasons', methods=['POST'])
def api_create_season():
    data = request.json
    conn = get_db()
    sid = gen_season_id(conn)
    try:
        conn.execute('''INSERT INTO production_seasons
            (season_id, year, start_date, end_date, notes)
            VALUES (?,?,?,?,?)''',
                     (sid, int(data.get('year', date.today().year)),
                      data.get('start_date') or None,
                      data.get('end_date') or None,
                      data.get('notes', '')))
        conn.commit()
        season = row_to_dict(conn.execute(
            'SELECT * FROM production_seasons WHERE season_id=?', (sid,)).fetchone())
        conn.close()
        return jsonify({'success': True, 'season': season})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/production/seasons/<season_id>', methods=['DELETE'])
def api_delete_season(season_id):
    conn = get_db()
    conn.execute('DELETE FROM production_batches WHERE season_id=?', (season_id,))
    conn.execute('DELETE FROM production_seasons WHERE season_id=?', (season_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/production/batches', methods=['POST'])
def api_create_batch():
    data = request.json
    conn = get_db()
    bid = gen_batch_id(conn)
    try:
        sap = float(data.get('sap_liters', 0))
        syrup = float(data.get('syrup_liters', 0))
        ratio = round(sap / syrup, 1) if syrup > 0 else 0
        season_id = data['season_id']
        conn.execute('''INSERT INTO production_batches
            (batch_id, season_id, date, sap_liters, syrup_liters, ratio, notes)
            VALUES (?,?,?,?,?,?,?)''',
                     (bid, season_id, data['date'], sap, syrup, ratio,
                      data.get('notes', '')))
        conn.execute('''UPDATE production_seasons SET
            total_sap_liters = (SELECT COALESCE(SUM(sap_liters),0) FROM production_batches WHERE season_id=?),
            total_syrup_liters = (SELECT COALESCE(SUM(syrup_liters),0) FROM production_batches WHERE season_id=?)
            WHERE season_id=?''', (season_id, season_id, season_id))
        conn.commit()
        batch = row_to_dict(conn.execute(
            'SELECT * FROM production_batches WHERE batch_id=?', (bid,)).fetchone())
        conn.close()
        return jsonify({'success': True, 'batch': batch})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/production/batches/<batch_id>', methods=['DELETE'])
def api_delete_batch(batch_id):
    conn = get_db()
    batch = row_to_dict(conn.execute(
        'SELECT * FROM production_batches WHERE batch_id=?', (batch_id,)).fetchone())
    if batch:
        conn.execute('DELETE FROM production_batches WHERE batch_id=?', (batch_id,))
        sid = batch['season_id']
        conn.execute('''UPDATE production_seasons SET
            total_sap_liters = (SELECT COALESCE(SUM(sap_liters),0) FROM production_batches WHERE season_id=?),
            total_syrup_liters = (SELECT COALESCE(SUM(syrup_liters),0) FROM production_batches WHERE season_id=?)
            WHERE season_id=?''', (sid, sid, sid))
        conn.commit()
    conn.close()
    return jsonify({'success': True})


# ─── IMPORT CSV ──────────────────────────────────────────────────────────────

@app.route('/api/products/import-csv', methods=['POST'])
def api_import_products_csv():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier'}), 400
    f = request.files['file']
    if not f.filename.endswith('.csv'):
        return jsonify({'success': False, 'error': 'Format CSV requis'}), 400
    stream = io.StringIO(f.read().decode('utf-8-sig'))
    reader = csv.DictReader(stream)
    conn = get_db()
    imported = errors = 0
    for row in reader:
        try:
            name = row.get('nom') or row.get('name') or ''
            price = row.get('prix') or row.get('price') or '0'
            if not name:
                errors += 1
                continue
            pid = gen_product_id(conn)
            conn.execute('''INSERT INTO products
                (product_id, name, price, category, tax_type, description, unit, stock_quantity, stock_alert_threshold)
                VALUES (?,?,?,?,?,?,?,?,?)''',
                         (pid, name.strip(), float(str(price).replace(',', '.')),
                          (row.get('categorie') or row.get('category') or '').strip(),
                          (row.get('taxe') or row.get('tax_type') or 'tps_tvq').strip(),
                          (row.get('description') or '').strip(),
                          (row.get('unite') or row.get('unit') or 'unité').strip(),
                          float(str(row.get('stock') or row.get('stock_quantity') or '0').replace(',', '.')),
                          float(str(row.get('alerte') or row.get('stock_alert_threshold') or '0').replace(',', '.'))))
            imported += 1
        except Exception:
            errors += 1
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'imported': imported, 'errors': errors})


@app.route('/api/customers/import-csv', methods=['POST'])
def api_import_customers_csv():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier'}), 400
    f = request.files['file']
    if not f.filename.endswith('.csv'):
        return jsonify({'success': False, 'error': 'Format CSV requis'}), 400
    stream = io.StringIO(f.read().decode('utf-8-sig'))
    reader = csv.DictReader(stream)
    conn = get_db()
    imported = errors = 0
    for row in reader:
        try:
            first = (row.get('prenom') or row.get('first_name') or '').strip()
            last = (row.get('nom') or row.get('last_name') or '').strip()
            if not first or not last:
                errors += 1
                continue
            cid = gen_customer_id(conn)
            conn.execute('''INSERT INTO customers
                (customer_id, first_name, last_name, address, city, province,
                 postal_code, phone, email, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?)''',
                         (cid, first, last,
                          (row.get('adresse') or row.get('address') or '').strip(),
                          (row.get('ville') or row.get('city') or '').strip(),
                          (row.get('province') or 'QC').strip(),
                          (row.get('code_postal') or row.get('postal_code') or '').strip(),
                          (row.get('telephone') or row.get('phone') or '').strip(),
                          (row.get('courriel') or row.get('email') or '').strip(),
                          (row.get('notes') or '').strip()))
            imported += 1
        except Exception:
            errors += 1
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'imported': imported, 'errors': errors})


@app.route('/api/products/stock-adjust', methods=['POST'])
def api_stock_adjust():
    """Ajustement manuel du stock d'un produit."""
    data = request.json
    conn = get_db()
    try:
        conn.execute('UPDATE products SET stock_quantity=? WHERE product_id=?',
                     (float(data['stock_quantity']), data['product_id']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400


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
