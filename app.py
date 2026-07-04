from flask import Flask, render_template, jsonify, request
import mysql.connector
import uuid
from flask_bcrypt import Bcrypt
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
bcrypt = Bcrypt(app)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="qwerty",
        database="gamestore"
    )


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Brak tokena!'}), 401

        try:
            # Usunięcie przedrostka "Bearer "
            token = token.split(" ")[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
            current_user_role = data['role']
        except Exception as e:
            return jsonify({'message': 'Token jest nieważny!', 'error': str(e)}), 401

        # Przekazujemy dane użytkownika do ukrytej funkcji
        return f(current_user_id, current_user_role, *args, **kwargs)

    return decorated


import uuid  # Dodaj to na samej górze pliku, jeśli jeszcze tego nie masz

@app.route('/register_page')
def register_page():
    """Wyświetla stronę rejestracji (register.html)."""
    return render_template('register.html')

@app.route('/login_page')
def login_page():
    """Wyświetla stronę logowania (login.html)."""
    return render_template('login.html')

@app.route('/cart')
def cart_page():
    """Wyświetla koszyk zamówienia (cart.html)."""
    return render_template('cart.html')

@app.route('/account')
def account_page():
    """Wyświetla ekran użytkownika (account.html)."""
    return render_template('account.html')

@app.route('/admin')
def admin_page():
    """Wyświetla panel administratora (admin.html)."""
    return render_template('admin.html')
# ==========================================
# ENDPOINT: Rejestracja nowego użytkownika
# ==========================================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json

    # Podstawowa walidacja danych wejściowych
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'message': 'Brak wymaganych danych (name, email, password)'}), 400

    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Krok 1: Sprawdzamy, czy taki email już istnieje w bazie
        cursor.execute("SELECT id FROM customers WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'message': 'Użytkownik o podanym adresie email już istnieje!'}), 409

        # Krok 2: Haszowanie hasła (BARDZO WAŻNE)
        # Decode('utf-8') zamienia wynik z typu bytes na zwykły string, który MySQL łatwo zapisze
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Krok 3: Generowanie unikalnego ID (ponieważ nasz klucz główny to VARCHAR)
        new_user_id = str(uuid.uuid4())

        # Krok 4: Zapis do bazy (domyślnie przypisujemy rolę 'user')
        insert_query = """
                       INSERT INTO customers (id, name, email, password_hash, role)
                       VALUES (%s, %s, %s, %s, 'user') \
                       """
        cursor.execute(insert_query, (new_user_id, name, email, hashed_password))

        # Zatwierdzenie zmian w bazie (bez tego rekord zniknie po zamknięciu połączenia!)
        conn.commit()

        return jsonify({'message': 'Konto zostało pomyślnie utworzone!'}), 201

    except Exception as e:
        # Jeśli coś pójdzie nie tak (np. awaria bazy), wycofujemy zmiany
        conn.rollback()
        return jsonify({'message': 'Wystąpił błąd podczas rejestracji.', 'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    auth = request.json
    if not auth or not auth.get('email') or not auth.get('password'):
        return jsonify({'message': 'Brak danych logowania'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, email, password_hash, role FROM customers WHERE email = %s", (auth.get('email'),))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    # Weryfikacja e-maila i sprawdzanie zahashowanego hasła
    if user and bcrypt.check_password_hash(user['password_hash'], auth.get('password')):
        # Tworzymy token ważny np. przez 2 godziny
        token = jwt.encode({
            'user_id': user['id'],
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }, app.config['SECRET_KEY'], algorithm="HS256")

        return jsonify({'token': token, 'role': user['role']})

    return jsonify({'message': 'Błędny email lub hasło'}), 401

@app.route('/api/user/orders', methods=['GET'])
@token_required
def get_my_orders(current_user_id, current_user_role):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Zamówienia zalogowanego użytkownika wraz z wartością i liczbą pozycji
        cursor.execute("""
            SELECT o.id, o.created_at, o.status,
                   COALESCE(SUM(op.quantity * p.price), 0) AS wartosc,
                   COALESCE(SUM(op.quantity), 0) AS liczba_przedmiotow
            FROM orders o
            LEFT JOIN order_products op ON o.id = op.order_id
            LEFT JOIN products p ON op.product_id = p.id
            WHERE o.customer_id = %s
            GROUP BY o.id, o.created_at, o.status
            ORDER BY o.created_at DESC
        """, (current_user_id,))
        orders = cursor.fetchall()
        return jsonify(orders)
    except Exception as e:
        return jsonify({'message': 'Błąd pobierania zamówień.', 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/orders', methods=['POST'])
@token_required
def create_order(current_user_id, current_user_role):
    data = request.json
    items = data.get('items') if data else None
    if not items:
        return jsonify({'message': 'Koszyk jest pusty.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()

        # Krok 1: Walidacja stanów magazynowych z blokadą wierszy (FOR UPDATE),
        # żeby dwa równoległe zamówienia nie wykupiły tych samych sztuk
        for item in items:
            quantity = int(item.get('quantity', 0))
            if quantity <= 0:
                conn.rollback()
                return jsonify({'message': 'Nieprawidłowa liczba sztuk.'}), 400

            cursor.execute("SELECT name, stock_quantity FROM products WHERE id = %s FOR UPDATE",
                           (item.get('product_id'),))
            product = cursor.fetchone()
            if not product:
                conn.rollback()
                return jsonify({'message': 'Jeden z produktów w koszyku już nie istnieje.'}), 404

            if quantity > product['stock_quantity']:
                conn.rollback()
                return jsonify({'message': f"Niewystarczający stan magazynowy: {product['name']} "
                                           f"(dostępne: {product['stock_quantity']} szt., zamówiono: {quantity} szt.)"}), 409

        # Krok 2: Zapis zamówienia przypisanego do zalogowanego użytkownika
        order_id = str(uuid.uuid4())
        cursor.execute("INSERT INTO orders (id, customer_id, created_at, status) VALUES (%s, %s, NOW(), 'Nowe')",
                       (order_id, current_user_id))

        # Krok 3: Pozycje zamówienia - stan magazynowy zdejmuje trigger trg_zmniejsz_magazyn
        for item in items:
            cursor.execute("INSERT INTO order_products (id, quantity, product_id, order_id) VALUES (%s, %s, %s, %s)",
                           (str(uuid.uuid4()), int(item['quantity']), item['product_id'], order_id))

        conn.commit()
        return jsonify({'message': 'Zamówienie zostało złożone!'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'message': 'Błąd składania zamówienia.', 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_profile(current_user_id, current_user_role):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT name, email, phone FROM customers WHERE id = %s", (current_user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'message': 'Nie znaleziono użytkownika.'}), 404
        return jsonify(user)
    finally:
        cursor.close()
        conn.close()


@app.route('/api/user/profile', methods=['PUT'])
@token_required
def update_profile(current_user_id, current_user_role):
    data = request.json
    if not data or not data.get('name') or not data.get('email'):
        return jsonify({'message': 'Imię i nazwisko oraz email są wymagane.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Nowy email nie może należeć do innego konta
        cursor.execute("SELECT id FROM customers WHERE email = %s AND id != %s",
                       (data.get('email'), current_user_id))
        if cursor.fetchone():
            return jsonify({'message': 'Ten adres email jest już zajęty!'}), 409

        cursor.execute("UPDATE customers SET name = %s, email = %s, phone = %s WHERE id = %s",
                       (data.get('name'), data.get('email'), data.get('phone'), current_user_id))
        conn.commit()
        return jsonify({'message': 'Dane zostały zaktualizowane!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'message': 'Błąd aktualizacji danych.', 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/dashboard', methods=['GET'])
@token_required
def admin_dashboard(current_user_id, current_user_role):
    if current_user_role != 'admin':
        return jsonify({'message': 'Odmowa dostępu. Wymagane uprawnienia administratora.'}), 403

    return jsonify({'message': 'Witaj w tajnym panelu administratora!'})


def resolve_publisher(cursor, data):
    """Zwraca id wydawcy: wskazanego wprost, istniejącego o podanej nazwie
    lub nowo utworzonego. None, gdy nie podano ani id, ani nazwy."""
    publisher_id = data.get('publisher_id')
    if publisher_id:
        return publisher_id

    publisher_name = (data.get('publisher_name') or '').strip()
    if not publisher_name:
        return None

    cursor.execute("SELECT id FROM publishers WHERE name = %s", (publisher_name,))
    existing = cursor.fetchone()
    if existing:
        return existing['id']

    new_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO publishers (id, name) VALUES (%s, %s)", (new_id, publisher_name))
    return new_id


def admin_only(current_user_role):
    """Zwraca odpowiedź 403, jeśli rola nie jest adminem, w przeciwnym razie None."""
    if current_user_role != 'admin':
        return jsonify({'message': 'Odmowa dostępu. Wymagane uprawnienia administratora.'}), 403
    return None


@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name FROM categories ORDER BY name")
        return jsonify(cursor.fetchall())
    finally:
        cursor.close()
        conn.close()


@app.route('/api/publishers', methods=['GET'])
def get_publishers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name FROM publishers ORDER BY name")
        return jsonify(cursor.fetchall())
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/products', methods=['GET'])
@token_required
def admin_get_products(current_user_id, current_user_role):
    denied = admin_only(current_user_role)
    if denied:
        return denied

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, name, description, price, stock_quantity, category_id, publisher_id
            FROM products ORDER BY name
        """)
        return jsonify(cursor.fetchall())
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/products', methods=['POST'])
@token_required
def admin_add_product(current_user_id, current_user_role):
    denied = admin_only(current_user_role)
    if denied:
        return denied

    data = request.json
    required = ['name', 'price', 'stock_quantity', 'category_id']
    if not data or any(data.get(field) in (None, '') for field in required):
        return jsonify({'message': 'Brak wymaganych danych (name, price, stock_quantity, category_id).'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        publisher_id = resolve_publisher(cursor, data)
        if not publisher_id:
            return jsonify({'message': 'Wybierz wydawcę lub podaj nazwę nowego.'}), 400

        cursor.execute("""
            INSERT INTO products (id, name, description, price, stock_quantity, category_id, publisher_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (str(uuid.uuid4()), data.get('name'), data.get('description'), data.get('price'),
              data.get('stock_quantity'), data.get('category_id'), publisher_id))
        conn.commit()
        return jsonify({'message': 'Produkt został dodany!'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'message': 'Błąd dodawania produktu.', 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/products/<product_id>', methods=['PUT'])
@token_required
def admin_update_product(current_user_id, current_user_role, product_id):
    denied = admin_only(current_user_role)
    if denied:
        return denied

    data = request.json
    required = ['name', 'price', 'stock_quantity', 'category_id']
    if not data or any(data.get(field) in (None, '') for field in required):
        return jsonify({'message': 'Brak wymaganych danych (name, price, stock_quantity, category_id).'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM products WHERE id = %s", (product_id,))
        if not cursor.fetchone():
            return jsonify({'message': 'Nie znaleziono produktu.'}), 404

        publisher_id = resolve_publisher(cursor, data)
        if not publisher_id:
            return jsonify({'message': 'Wybierz wydawcę lub podaj nazwę nowego.'}), 400

        cursor.execute("""
            UPDATE products
            SET name = %s, description = %s, price = %s, stock_quantity = %s,
                category_id = %s, publisher_id = %s
            WHERE id = %s
        """, (data.get('name'), data.get('description'), data.get('price'), data.get('stock_quantity'),
              data.get('category_id'), publisher_id, product_id))
        conn.commit()
        return jsonify({'message': 'Produkt został zaktualizowany!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'message': 'Błąd aktualizacji produktu.', 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/products/<product_id>', methods=['DELETE'])
@token_required
def admin_delete_product(current_user_id, current_user_role, product_id):
    denied = admin_only(current_user_role)
    if denied:
        return denied

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
        if cursor.rowcount == 0:
            return jsonify({'message': 'Nie znaleziono produktu.'}), 404
        conn.commit()
        return jsonify({'message': 'Produkt został usunięty!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'message': 'Błąd usuwania produktu (może być powiązany z zamówieniami).', 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/users', methods=['GET'])
@token_required
def admin_get_users(current_user_id, current_user_role):
    denied = admin_only(current_user_role)
    if denied:
        return denied

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, name, email, phone, role FROM customers ORDER BY name")
        return jsonify(cursor.fetchall())
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/users/<user_id>/role', methods=['PUT'])
@token_required
def admin_update_user_role(current_user_id, current_user_role, user_id):
    denied = admin_only(current_user_role)
    if denied:
        return denied

    if user_id == current_user_id:
        return jsonify({'message': 'Nie możesz zmienić roli własnego konta.'}), 400

    data = request.json
    new_role = data.get('role') if data else None
    if new_role not in ('user', 'admin'):
        return jsonify({'message': "Nieprawidłowa rola (dozwolone: 'user', 'admin')."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM customers WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({'message': 'Nie znaleziono użytkownika.'}), 404

        cursor.execute("UPDATE customers SET role = %s WHERE id = %s", (new_role, user_id))
        conn.commit()
        return jsonify({'message': 'Rola została zmieniona!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'message': 'Błąd zmiany roli.', 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/api/admin/users/<user_id>', methods=['DELETE'])
@token_required
def admin_delete_user(current_user_id, current_user_role, user_id):
    denied = admin_only(current_user_role)
    if denied:
        return denied

    if user_id == current_user_id:
        return jsonify({'message': 'Nie możesz usunąć własnego konta.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM customers WHERE id = %s", (user_id,))
        if cursor.rowcount == 0:
            return jsonify({'message': 'Nie znaleziono użytkownika.'}), 404
        conn.commit()
        return jsonify({'message': 'Użytkownik został usunięty!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'message': 'Błąd usuwania użytkownika (może mieć złożone zamówienia).', 'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/')
def starting_page():  # put application's code here
    return render_template('starting_page.html')


@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        conn = get_db_connection()
        # dictionary=True sprawia, że wyniki wracają jako słowniki (idealne dla formatu JSON)
        cursor = conn.cursor(dictionary=True)

        # Wykorzystujemy nasz widok z poprzednich kroków!
        cursor.execute("SELECT * FROM v_katalog_produktow")
        products = cursor.fetchall()

        cursor.close()
        conn.close()

        # Odsyłamy dane jako JSON na frontend
        return jsonify(products)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
