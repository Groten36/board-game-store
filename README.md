# board-game-store
<img width="1379" height="593" alt="image" src="https://github.com/user-attachments/assets/689688ac-b50d-4a1a-a681-31da2efeb615" />

## Opis projektu

HobbToys — sklep internetowy z grami planszowymi, bitewnymi i karcianymi. Aplikacja webowa napisana we Flasku (Python) z bazą danych MySQL. Frontend to szablony HTML z czystym JavaScriptem, komunikujące się z backendem przez API JSON. Uwierzytelnianie oparte o tokeny JWT, hasła hashowane bcryptem.

## Uruchomienie

### Wymagania

- Python 3.x
- Serwer MySQL z bazą `gamestore` (tabele: `customers`, `products`, `categories`, `publishers`, `orders`, `order_products`; widok `v_katalog_produktow`; trigger `trg_zmniejsz_magazyn` zdejmujący stan magazynowy przy dodaniu pozycji zamówienia)

### Kroki

1. (Opcjonalnie) utwórz i aktywuj wirtualne środowisko:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Zainstaluj zależności:
   ```
   pip install -r requirements.txt
   ```
3. Upewnij się, że MySQL działa lokalnie, a dane dostępowe w funkcji `get_db_connection()` w `app.py` (host, użytkownik, hasło, baza) pasują do Twojej konfiguracji.
4. Uruchom aplikację:
   ```
   python app.py
   ```
5. Otwórz w przeglądarce: http://127.0.0.1:5000

## Funkcjonalności

### Sklep (strona główna `/`)

- Katalog produktów pobierany z bazy (widok `v_katalog_produktow`)
- Filtrowanie produktów po kategoriach z górnego paska (Planszówki, Bitewniaki, Karcianki, Akcesoria)
- Wyszukiwanie produktu po nazwie (pole w sekcji hero)
- Dodawanie produktów do koszyka z licznikiem sztuk na przycisku „Koszyk"

### Konta użytkowników

- Rejestracja (`/register_page`) — po sukcesie przekierowanie do logowania
- Logowanie (`/login_page`) — zwraca token JWT (ważny 2 h); zwykły użytkownik trafia na ekran konta, administrator do panelu admina
- Przycisk „Zaloguj się" w pasku zmienia się po zalogowaniu w „Wyloguj", obok pojawia się wejście do panelu („Moje konto" / „Panel admina")

### Ekran użytkownika (`/account`)

- Lista zamówień użytkownika (data, status, liczba przedmiotów, wartość)
- Edycja danych osobowych: imię i nazwisko, e-mail, numer telefonu

### Koszyk i zamówienia (`/cart`)

- Lista produktów w koszyku: cena jednostkowa, liczba sztuk (z możliwością zmiany), wartość pozycji i suma koszyka
- Złożenie zamówienia (wymaga zalogowania) zapisuje je w bazie i zmniejsza stany magazynowe w jednej transakcji
- Gdy zamówiona liczba sztuk przekracza stan magazynowy, zamówienie jest odrzucane z komunikatem, który produkt i ile sztuk jest dostępnych
- Złożone zamówienie widoczne jest na koncie użytkownika

### Panel administratora (`/admin`)

- Dostępny tylko dla roli `admin` (weryfikacja tokena przy każdym żądaniu API)
- Lista wszystkich produktów
- Dodawanie, edycja i usuwanie produktów (nazwa, opis, cena, stan magazynowy, kategoria, wydawca)
- Przy dodawaniu/edycji produktu można podać nowego wydawcę — zostanie automatycznie dodany do bazy (bez duplikatów)
- Lista wszystkich zarejestrowanych użytkowników (imię i nazwisko, email, telefon, rola)
- Zmiana roli użytkownika (user/admin) oraz usuwanie kont — admin nie może zmienić roli ani usunąć własnego konta; użytkownika z zamówieniami chroni klucz obcy

## API

| Metoda | Endpoint | Dostęp | Opis |
|---|---|---|---|
| POST | `/api/register` | publiczny | rejestracja konta |
| POST | `/api/login` | publiczny | logowanie, zwraca token JWT i rolę |
| GET | `/api/products` | publiczny | katalog produktów |
| GET | `/api/categories`, `/api/publishers` | publiczny | słowniki kategorii i wydawców |
| POST | `/api/orders` | zalogowany | złożenie zamówienia z koszyka |
| GET | `/api/user/orders` | zalogowany | zamówienia użytkownika |
| GET/PUT | `/api/user/profile` | zalogowany | odczyt/edycja danych osobowych |
| GET/POST | `/api/admin/products` | admin | lista/dodanie produktu |
| PUT/DELETE | `/api/admin/products/<id>` | admin | edycja/usunięcie produktu |
| GET | `/api/admin/users` | admin | lista wszystkich użytkowników |
| PUT | `/api/admin/users/<id>/role` | admin | zmiana roli użytkownika (user/admin) |
| DELETE | `/api/admin/users/<id>` | admin | usunięcie użytkownika |
