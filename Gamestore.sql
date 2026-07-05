-- create database gamestore;
use gamestore;
/*
CREATE TABLE customers (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(255),
    shipping_address VARCHAR(255)
);

CREATE TABLE categories (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(255)
);

CREATE TABLE publishers (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    contact_info VARCHAR(255)
);

CREATE TABLE products (
    id VARCHAR(255) PRIMARY KEY,
    category_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(255),
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    stock_quantity INT NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    publisher_id VARCHAR(255) NOT NULL,
    
    CONSTRAINT fk_product_category 
        FOREIGN KEY (category_id) REFERENCES categories(id) 
        ON UPDATE CASCADE ON DELETE RESTRICT,
        
    CONSTRAINT fk_product_publisher 
        FOREIGN KEY (publisher_id) REFERENCES publishers(id) 
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE orders (
    id VARCHAR(255) PRIMARY KEY,
    customer_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(255) NOT NULL,
    
    CONSTRAINT fk_order_customer 
        FOREIGN KEY (customer_id) REFERENCES customers(id) 
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE order_products (
    id VARCHAR(255) PRIMARY KEY,
    quantity INT NOT NULL CHECK (quantity > 0),
    product_id VARCHAR(255) NOT NULL,
    order_id VARCHAR(255) NOT NULL,
    
    CONSTRAINT fk_op_product 
        FOREIGN KEY (product_id) REFERENCES products(id) 
        ON UPDATE CASCADE ON DELETE RESTRICT,
        
    CONSTRAINT fk_op_order 
        FOREIGN KEY (order_id) REFERENCES orders(id) 
        ON UPDATE CASCADE ON DELETE CASCADE
);


-- Dodawanie klientów (pasjonatów gier)
INSERT INTO customers (id, name, email, phone, shipping_address) VALUES 
('c1', 'Jan Kowalski', 'jan.kowalski@example.com', '+48 501 234 567', 'ul. Marszałkowska 10/2, 00-001 Warszawa'),
('c2', 'Anna Nowak', 'anna.nowak@example.com', '+48 602 345 678', 'ul. Piotrkowska 45, 90-004 Łódź'),
('c3', 'Piotr Wiśniewski', 'p.wisniewski@example.com', '+48 703 456 789', 'ul. Floriańska 12/4, 31-021 Kraków'),
('c4', 'Maria Wójcik', 'maria.wojcik@example.com', NULL, 'ul. Długa 5, 80-827 Gdańsk');

-- Dodawanie kategorii specyficznych dla hobby
INSERT INTO categories (id, name, description) VALUES 
('cat1', 'Gry Planszowe Stratgiczne', 'Zaawansowane planszówki euro, strategiczne oraz typu area control'),
('cat2', 'Gry Figurowe i Bitewne', 'Systemy bitewne, makiety oraz zestawy figurek do sklejania i malowania'),
('cat3', 'Gry Karciane', 'Kolekcjonerskie gry karciane (CCG), żyjące gry karciane (LCG) oraz karcianki imprezowe'),
('cat4', 'Akcesoria modelarskie i kości', 'Kości RPG, koszulki na karty, pędzle, farbki oraz pianki na figurki');

-- Dodawanie znanych wydawców gier i akcesoriów
INSERT INTO publishers (id, name, contact_info) VALUES 
('pub1', 'Rebel', 'hurt@rebel.pl, Gdańsk - Wydawca m.in. Dixit, Nemesis'),
('pub2', 'Games Workshop', 'uk-sales@gwplc.com, Nottingham UK - Twórcy Warhammera'),
('pub3', 'Portal Games', 'portal@portalgames.pl, Gliwice - Wydawca gier strategicznych'),
('pub4', 'Galakta', 'galakta@galakta.pl, Kraków - Wydawca gier karcianych LCG i planszowych');

CREATE VIEW v_katalog_produktow AS
SELECT 
    p.id AS produkt_id,
    p.name AS nazwa_gry,
    p.price AS cena,
    p.stock_quantity AS stan_magazynowy,
    c.name AS kategoria,
    pub.name AS wydawca
FROM products p
JOIN categories c ON p.category_id = c.id
JOIN publishers pub ON p.publisher_id = pub.id;

CREATE VIEW v_podsumowanie_zamowien AS
SELECT 
    o.id AS zamowienie_id,
    c.name AS klient,
    c.email AS kontakt_email,
    o.created_at AS data_zalozenia,
    o.status,
    SUM(op.quantity * p.price) AS wartosc_calkowita,
    SUM(op.quantity) AS liczba_przedmiotow
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN order_products op ON o.id = op.order_id
JOIN products p ON op.product_id = p.id
GROUP BY o.id, c.name, c.email, o.created_at, o.status;

CREATE VIEW v_szczegoly_zamowienia AS
SELECT 
    op.order_id AS zamowienie_id,
    p.name AS nazwa_produktu,
    op.quantity AS ilosc,
    p.price AS cena_jednostkowa,
    (op.quantity * p.price) AS wartosc_pozycji
FROM order_products op
JOIN products p ON op.product_id = p.id;

CREATE VIEW v_braki_magazynowe AS
SELECT 
    p.id AS produkt_id,
    p.name AS nazwa_produktu,
    pub.name AS wydawca,
    p.stock_quantity AS pozostale_sztuki
FROM products p
JOIN publishers pub ON p.publisher_id = pub.id
WHERE p.stock_quantity < 10;

DELIMITER //

CREATE FUNCTION f_etykieta_dostepnosci(ilosc_sztuk INT)
RETURNS VARCHAR(50)
DETERMINISTIC
BEGIN
    IF ilosc_sztuk >= 10 THEN
        RETURN 'Dostępny od ręki';
    ELSEIF ilosc_sztuk > 0 AND ilosc_sztuk < 10 THEN
        RETURN 'Ostatnie sztuki! Pospiesz się!';
    ELSE
        RETURN 'Brak w magazynie';
    END IF;
END //

DELIMITER ;

DELIMITER //

CREATE TRIGGER trg_zmniejsz_magazyn
AFTER INSERT ON order_products
FOR EACH ROW
BEGIN
    -- NEW oznacza nowo dodawany wiersz w tabeli order_products
    UPDATE products 
    SET stock_quantity = stock_quantity - NEW.quantity
    WHERE id = NEW.product_id;
END //

DELIMITER ;

DELIMITER //

CREATE PROCEDURE p_utworz_szybkie_zamowienie(
    IN p_customer_id VARCHAR(255),
    IN p_product_id VARCHAR(255),
    IN p_quantity INT
)
BEGIN
    -- Deklaracja zmiennej na wygenerowane ID zamówienia i ID pozycji
    DECLARE v_nowe_zamowienie_id VARCHAR(255);
    DECLARE v_nowa_pozycja_id VARCHAR(255);
    
    -- Obsługa błędów - jeśli cokolwiek pójdzie nie tak, wycofaj wszystkie zmiany
    DECLARE EXIT HANDLER FOR SQLEXCEPTION 
    BEGIN
        ROLLBACK;
    END;

    -- Uruchamiamy transakcję
    START TRANSACTION;

    -- Generujemy unikalne ID (np. za pomocą wbudowanej funkcji UUID)
    SET v_nowe_zamowienie_id = UUID();
    SET v_nowa_pozycja_id = UUID();

    -- Krok 1: Tworzymy nagłówek zamówienia
    INSERT INTO orders (id, customer_id, created_at, status) 
    VALUES (v_nowe_zamowienie_id, p_customer_id, NOW(), 'Nowe');

    -- Krok 2: Dodajemy produkt do koszyka (to z kolei uruchomi nasz Trigger zdejmujący ze stanu!)
    INSERT INTO order_products (id, quantity, product_id, order_id) 
    VALUES (v_nowa_pozycja_id, p_quantity, p_product_id, v_nowe_zamowienie_id);

    -- Jeśli doszliśmy tutaj bez błędu, zatwierdzamy zmiany na stałe
    COMMIT;
END //

DELIMITER ;

-- Dodawanie produktów (gier, figurek i akcesoriów)
INSERT INTO products (id, category_id, name, description, price, stock_quantity, publisher_id) VALUES 
('p1', 'cat1', 'Nemesis (Wersja Polska)', 'Semi-kooperacyjna gra planszowa w klimacie sci-fi horroru.', 549.00, 15, 'pub1'),
('p2', 'cat2', 'Warhammer 40,000: Ultimate Starter Set', 'Zestaw startowy do gry bitewnej zawierający figurki Space Marines oraz Tyranidów.', 619.99, 8, 'pub2'),
('p3', 'cat1', 'Terraformacja Marsa', 'Klasyczna gra ekonomiczno-strategiczna o kolonizacji Czerwonej Planety.', 179.50, 45, 'pub1'),
('p4', 'cat3', 'Horror w Arkham LCG: Zestaw Podstawowy', 'Kooperacyjna żyjąca gra karciana osadzona w mitologii Cthulhu.', 159.00, 22, 'pub4'),
('p5', 'cat4', 'Zestaw Farb Citadel: Base', 'Komplet 11 podstawowych farb akrylowych do malowania figurek plastikowych i metalowych.', 145.00, 30, 'pub2'),
('p6', 'cat3', 'Eksplodujące Kotki', 'Szybka, imprezowa gra karciana pełna negatywnej interakcji.', 79.90, 60, 'pub1');

-- Dodawanie nagłówków zamówień
INSERT INTO orders (id, customer_id, created_at, status) VALUES 
('o1', 'c1', '2026-06-15 10:30:00', 'Wysłane'),
('o2', 'c2', '2026-06-16 14:15:00', 'W trakcie realizacji'),
('o3', 'c3', '2026-06-17 09:00:00', 'Dostarczone'),
('o4', 'c1', '2026-06-18 18:45:00', 'Nowe');

-- Dodawanie konkretnych gier do koszyków zamówień
INSERT INTO order_products (id, quantity, product_id, order_id) VALUES 
('op1', 1, 'p1', 'o1'), -- Jan Kowalski kupił 'Nemesis'
('op2', 1, 'p6', 'o1'), -- Jan Kowalski dorzucił do tego samego zamówienia imprezowe 'Eksplodujące Kotki'
('op3', 1, 'p2', 'o2'), -- Anna Nowak zamówiła duży zestaw startowy do 'Warhammera 40k'
('op4', 2, 'p5', 'o2'), -- Anna Nowak dokupiła od razu 2 zestawy farbek do pomalowania tych figurek
('op5', 1, 'p3', 'o3'), -- Piotr Wiśniewski zamówił 'Terraformację Marsa'
('op6', 1, 'p4', 'o3'), -- Piotr Wiśniewski dołożył 'Horror w Arkham LCG'
('op7', 3, 'p6', 'o4'); -- Jan Kowalski złożył nowe zamówienie na 3 sztuki 'Eksplodujących Kotków' (np. na prezenty)

ALTER TABLE customers 
ADD COLUMN password_hash VARCHAR(255) NOT NULL AFTER email,
ADD COLUMN role VARCHAR(50) DEFAULT 'user' AFTER password_hash;


UPDATE customers SET role = 'admin' WHERE email = 'm.ciezka@hobbstoys.com';
*/
SELECT * FROM orders;