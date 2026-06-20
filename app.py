from flask import Flask, render_template, jsonify
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="qwerty",
        database="gamestore"
    )
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
