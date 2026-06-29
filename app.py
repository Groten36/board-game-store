from flask import Flask, render_template, jsonify
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

@app.route('/rejestracja')
def register_page():
    """Wyświetla stronę rejestracji (register.html)."""
    return render_template('register.html')
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
    # Skoro przeszedł przez @token_required, to wiemy kim jest
    return jsonify({'message': f'Zwracam zamówienia dla usera o ID: {current_user_id}'})


@app.route('/api/admin/dashboard', methods=['GET'])
@token_required
def admin_dashboard(current_user_id, current_user_role):
    if current_user_role != 'admin':
        return jsonify({'message': 'Odmowa dostępu. Wymagane uprawnienia administratora.'}), 403

    return jsonify({'message': 'Witaj w tajnym panelu administratora!'})
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
