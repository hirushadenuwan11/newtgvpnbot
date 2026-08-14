import sqlite3
import random
import string
from datetime import datetime


DB_FILE = "v2ray_store.db"


# =========================================================
# CONNECTION
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_order_id():
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    rand = "".join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=5
        )
    )
    return f"VP-{stamp}-{rand}"


def generate_referral_code(user_id):
    return f"VP{int(user_id)}"


# =========================================================
# INIT
# =========================================================

def init_database():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            referral_code TEXT UNIQUE,
            referred_by TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS packages (
            package_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            duration INTEGER NOT NULL,
            price REAL NOT NULL,
            active INTEGER DEFAULT 1,
            inbound_id INTEGER NOT NULL,
            traffic_gb REAL DEFAULT 0,
            sni TEXT NOT NULL,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            package_id INTEGER NOT NULL,
            package_name TEXT NOT NULL,
            duration INTEGER NOT NULL,
            price REAL NOT NULL,
            status TEXT DEFAULT 'PENDING',
            inbound_id INTEGER NOT NULL,
            traffic_gb REAL DEFAULT 0,
            sni TEXT,
            payment_proof TEXT,
            config TEXT,
            expiry TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            config TEXT NOT NULL,
            expiry TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS referral_earnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_user_id INTEGER NOT NULL,
            order_id TEXT,
            amount REAL DEFAULT 0,
            status TEXT DEFAULT 'PENDING',
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# USERS
# =========================================================

def save_user(
    user_id,
    username=None,
    first_name=None,
    referral_code=None
):

    user_id = int(user_id)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user_id,)
    )

    exists = cur.fetchone()

    if exists:

        cur.execute("""
            UPDATE users
            SET username = ?,
                first_name = ?,
                updated_at = ?
            WHERE user_id = ?
        """, (
            username,
            first_name,
            now(),
            user_id
        ))

    else:

        my_code = generate_referral_code(user_id)

        referred_by = None

        if referral_code:

            referral_code = str(
                referral_code
            ).strip().upper()

            if referral_code != my_code:

                referred_by = referral_code

        cur.execute("""
            INSERT INTO users (
                user_id,
                username,
                first_name,
                referral_code,
                referred_by,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            username,
            first_name,
            my_code,
            referred_by,
            now(),
            now()
        ))

    conn.commit()
    conn.close()


def get_user(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            user_id,
            username,
            first_name,
            referral_code,
            referred_by,
            created_at,
            updated_at
        FROM users
        WHERE user_id = ?
        LIMIT 1
    """, (int(user_id),))

    row = cur.fetchone()

    conn.close()

    return row


def get_user_count():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM users"
    )

    value = cur.fetchone()[0]

    conn.close()

    return value


# =========================================================
# PACKAGES
# =========================================================

def get_packages(active_only=True):

    conn = get_connection()
    cur = conn.cursor()

    if active_only:

        cur.execute("""
            SELECT
                package_id,
                name,
                duration,
                price,
                active,
                inbound_id,
                traffic_gb,
                sni
            FROM packages
            WHERE active = 1
            ORDER BY package_id ASC
        """)

    else:

        cur.execute("""
            SELECT
                package_id,
                name,
                duration,
                price,
                active,
                inbound_id,
                traffic_gb,
                sni
            FROM packages
            ORDER BY package_id ASC
        """)

    rows = cur.fetchall()

    conn.close()

    return rows


def get_package(package_id):

    try:
        package_id = int(package_id)
    except Exception:
        return None

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT
                package_id,
                name,
                duration,
                price,
                active,
                inbound_id,
                traffic_gb,
                sni
            FROM packages
            WHERE package_id = ?
            LIMIT 1
        """, (package_id,))

        return cur.fetchone()

    finally:

        conn.close()


def add_package(
    name,
    duration,
    price,
    inbound_id,
    traffic_gb,
    sni
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO packages (
            name,
            duration,
            price,
            active,
            inbound_id,
            traffic_gb,
            sni,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
    """, (
        str(name),
        int(duration),
        float(price),
        int(inbound_id),
        float(traffic_gb),
        str(sni),
        now(),
        now()
    ))

    package_id = cur.lastrowid

    conn.commit()
    conn.close()

    return package_id


def update_package(
    package_id,
    name,
    duration,
    price,
    inbound_id,
    traffic_gb,
    sni
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE packages
        SET
            name = ?,
            duration = ?,
            price = ?,
            inbound_id = ?,
            traffic_gb = ?,
            sni = ?,
            updated_at = ?
        WHERE package_id = ?
    """, (
        str(name),
        int(duration),
        float(price),
        int(inbound_id),
        float(traffic_gb),
        str(sni),
        now(),
        int(package_id)
    ))

    changed = cur.rowcount

    conn.commit()
    conn.close()

    return changed > 0


def set_package_status(
    package_id,
    status
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE packages
        SET
            active = ?,
            updated_at = ?
        WHERE package_id = ?
    """, (
        int(status),
        now(),
        int(package_id)
    ))

    changed = cur.rowcount

    conn.commit()
    conn.close()

    return changed > 0


# =========================================================
# ORDERS
# =========================================================

def create_order(
    user_id,
    package_id
):

    package = get_package(package_id)

    if not package:
        return None

    (
        pid,
        name,
        duration,
        price,
        active,
        inbound_id,
        traffic_gb,
        sni
    ) = package

    if not active:
        return None

    order_id = generate_order_id()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO orders (
            order_id,
            user_id,
            package_id,
            package_name,
            duration,
            price,
            status,
            inbound_id,
            traffic_gb,
            sni,
            payment_proof,
            config,
            expiry,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
    """, (
        order_id,
        int(user_id),
        int(package_id),
        name,
        int(duration),
        float(price),
        "PENDING",
        int(inbound_id),
        float(traffic_gb),
        sni,
        now(),
        now()
    ))

    conn.commit()
    conn.close()

    return {
        "order_id": order_id,
        "user_id": int(user_id),
        "package_id": int(package_id),
        "package_name": name,
        "duration": int(duration),
        "price": float(price),
        "status": "PENDING",
        "inbound_id": int(inbound_id),
        "traffic_gb": float(traffic_gb),
        "sni": sni
    }


def get_order(order_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            order_id,
            user_id,
            package_id,
            package_name,
            duration,
            price,
            status,
            inbound_id,
            traffic_gb,
            sni,
            payment_proof,
            config,
            expiry,
            created_at,
            updated_at
        FROM orders
        WHERE order_id = ?
        LIMIT 1
    """, (str(order_id),))

    row = cur.fetchone()

    conn.close()

    return row


# =========================================================
# IMPORTANT:
# EXACTLY 7 COLUMNS
#
# This fixes:
# ValueError: expected 7, got 6
# =========================================================

def get_pending_orders():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            order_id,
            user_id,
            package_id,
            package_name,
            price,
            status,
            created_at
        FROM orders
        WHERE status IN (
            'PENDING',
            'PAYMENT_SUBMITTED',
            'APPROVED'
        )
        ORDER BY created_at ASC
    """)

    rows = cur.fetchall()

    conn.close()

    return rows


def get_user_orders(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            order_id,
            package_name,
            duration,
            price,
            status
        FROM orders
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (int(user_id),))

    rows = cur.fetchall()

    conn.close()

    return rows


def update_order_status(
    order_id,
    status
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE orders
        SET
            status = ?,
            updated_at = ?
        WHERE order_id = ?
    """, (
        str(status),
        now(),
        str(order_id)
    ))

    changed = cur.rowcount

    conn.commit()
    conn.close()

    return changed > 0


def get_order_count():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM orders"
    )

    result = cur.fetchone()[0]

    conn.close()

    return result


def get_pending_count():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE status IN (
            'PENDING',
            'PAYMENT_SUBMITTED',
            'APPROVED'
        )
    """)

    result = cur.fetchone()[0]

    conn.close()

    return result


def get_total_sales():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(
            SUM(price),
            0
        )
        FROM orders
        WHERE status = 'COMPLETED'
    """)

    result = cur.fetchone()[0]

    conn.close()

    return float(result or 0)


# =========================================================
# PAYMENT
# =========================================================

def save_payment_proof(
    order_id,
    proof
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE orders
        SET
            payment_proof = ?,
            updated_at = ?
        WHERE order_id = ?
    """, (
        str(proof),
        now(),
        str(order_id)
    ))

    changed = cur.rowcount

    conn.commit()
    conn.close()

    return changed > 0


def get_payment_proof(order_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT payment_proof
        FROM orders
        WHERE order_id = ?
        LIMIT 1
    """, (str(order_id),))

    row = cur.fetchone()

    conn.close()

    return row[0] if row else None


# =========================================================
# CONFIGS
# =========================================================

def save_config(
    order_id,
    config,
    expiry
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE orders
        SET
            config = ?,
            expiry = ?,
            updated_at = ?
        WHERE order_id = ?
    """, (
        str(config),
        str(expiry),
        now(),
        str(order_id)
    ))

    cur.execute("""
        SELECT id
        FROM configs
        WHERE order_id = ?
        LIMIT 1
    """, (str(order_id),))

    exists = cur.fetchone()

    if exists:

        cur.execute("""
            UPDATE configs
            SET
                config = ?,
                expiry = ?
            WHERE order_id = ?
        """, (
            str(config),
            str(expiry),
            str(order_id)
        ))

    else:

        cur.execute("""
            INSERT INTO configs (
                order_id,
                config,
                expiry,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            str(order_id),
            str(config),
            str(expiry),
            now()
        ))

    conn.commit()
    conn.close()

    return True


def get_user_configs(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            o.order_id,
            c.config,
            c.created_at,
            c.expiry
        FROM configs c
        INNER JOIN orders o
            ON o.order_id = c.order_id
        WHERE o.user_id = ?
        ORDER BY c.created_at DESC
    """, (int(user_id),))

    rows = cur.fetchall()

    conn.close()

    return rows


# =========================================================
# REFERRALS
# =========================================================

def get_referral_stats(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT referral_code
        FROM users
        WHERE user_id = ?
        LIMIT 1
    """, (int(user_id),))

    row = cur.fetchone()

    if not row:

        conn.close()
        return 0, 0, 0.0

    code = row[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE referred_by = ?
    """, (code,))

    total = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM referral_earnings
        WHERE referrer_id = ?
        AND status = 'PAID'
    """, (int(user_id),))

    paid = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(
            SUM(amount),
            0
        )
        FROM referral_earnings
        WHERE referrer_id = ?
    """, (int(user_id),))

    earned = cur.fetchone()[0]

    conn.close()

    return (
        int(total or 0),
        int(paid or 0),
        float(earned or 0)
    )


def create_referral_earning(
    referred_user_id,
    order_id,
    percentage=5
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT referred_by
        FROM users
        WHERE user_id = ?
        LIMIT 1
    """, (int(referred_user_id),))

    row = cur.fetchone()

    if not row or not row[0]:

        conn.close()
        return False

    referral_code = row[0]

    cur.execute("""
        SELECT user_id
        FROM users
        WHERE referral_code = ?
        LIMIT 1
    """, (referral_code,))

    referrer = cur.fetchone()

    if not referrer:

        conn.close()
        return False

    referrer_id = int(referrer[0])

    cur.execute("""
        SELECT price
        FROM orders
        WHERE order_id = ?
        LIMIT 1
    """, (str(order_id),))

    order = cur.fetchone()

    if not order:

        conn.close()
        return False

    amount = (
        float(order[0])
        * float(percentage)
        / 100
    )

    cur.execute("""
        INSERT INTO referral_earnings (
            referrer_id,
            referred_user_id,
            order_id,
            amount,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, 'PENDING', ?)
    """, (
        referrer_id,
        int(referred_user_id),
        str(order_id),
        amount,
        now()
    ))

    conn.commit()
    conn.close()

    return True


def mark_referral_paid(order_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE referral_earnings
        SET status = 'PAID'
        WHERE order_id = ?
    """, (str(order_id),))

    changed = cur.rowcount

    conn.commit()
    conn.close()

    return changed > 0


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    init_database()

    print("Database initialized successfully.")
    print("DB:", DB_FILE)