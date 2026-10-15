/* =====================================================================
   PROJECT : Retail Inventory and Sales Intelligence System
   DATABASE: PostgreSQL (Neon compatible)
   SCHEMA  : retail

   ENTITY SETS
   -----------
   1. categories            - product groups
   2. suppliers             - vendors who supply products
   3. products              - items sold (with reorder level/quantity)
   4. stores                - retail branches
   5. inventory             - stock of a product in a store  (M:N products-stores)
   6. employees             - staff working in a store
   7. customers             - buyers (optional on a sale)
   8. sales                 - sale header (invoice)
   9. sale_items            - sale lines                      (M:N sales-products)
  10. purchase_orders       - restock orders sent to suppliers
  11. purchase_order_items  - lines of a purchase order       (M:N PO-products)
  12. stock_movements       - audit log of every stock change

   RELATIONAL MODEL  (PK = primary key, FK = foreign key)
   ------------------------------------------------------
   categories(category_id PK, category_name, description)
   suppliers(supplier_id PK, supplier_name, contact_person, email, phone,
             city, lead_time_days)
   products(product_id PK, sku, product_name, category_id FK, supplier_id FK,
            unit_cost, unit_price, reorder_level, reorder_quantity, is_active)
   stores(store_id PK, store_name, city, address, phone)
   inventory(store_id PK/FK, product_id PK/FK, quantity_on_hand, last_updated)
   employees(employee_id PK, store_id FK, full_name, role, email, hire_date)
   customers(customer_id PK, full_name, email, phone, city, created_at)
   sales(sale_id PK, store_id FK, customer_id FK, employee_id FK, sale_date,
         payment_method, total_amount)
   sale_items(sale_item_id PK, sale_id FK, product_id FK, quantity,
              unit_price, discount, line_total)
   purchase_orders(po_id PK, supplier_id FK, store_id FK, order_date,
                   expected_date, status)
   purchase_order_items(po_item_id PK, po_id FK, product_id FK, quantity,
                        unit_cost, received_qty)
   stock_movements(movement_id PK, store_id FK, product_id FK, movement_type,
                   quantity, reference, created_at)

   RELATIONSHIPS
   -------------
   categories 1---M products          suppliers 1---M products
   stores     1---M employees         stores    1---M sales
   customers  1---M sales             employees 1---M sales
   sales      1---M sale_items        products  1---M sale_items
   stores  M---M products  (via inventory)
   suppliers  1---M purchase_orders   stores 1---M purchase_orders
   purchase_orders 1---M purchase_order_items   products 1---M purchase_order_items
   products/stores 1---M stock_movements

   KEY FEATURES
   ------------
   * Trigger: a sale automatically reduces stock, logs a movement and
     updates the sale total (negative stock is blocked).
   * Function receive_purchase_order(po_id): adds stock when goods arrive.
   * Views: v_stock_status, v_reorder_list, v_inventory_valuation,
            v_daily_sales, v_monthly_revenue, v_product_performance
   ===================================================================== */

DROP SCHEMA IF EXISTS retail CASCADE;
CREATE SCHEMA retail;
SET search_path TO retail;

/* ---------------------------------------------------------------------
   1. TABLES
   --------------------------------------------------------------------- */

CREATE TABLE categories (
    category_id    INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_name  VARCHAR(80)  NOT NULL UNIQUE,
    description    TEXT
);

CREATE TABLE suppliers (
    supplier_id     INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    supplier_name   VARCHAR(120) NOT NULL UNIQUE,
    contact_person  VARCHAR(100),
    email           VARCHAR(120) UNIQUE,
    phone           VARCHAR(30),
    city            VARCHAR(80),
    lead_time_days  INT NOT NULL DEFAULT 3 CHECK (lead_time_days >= 0)
);

CREATE TABLE products (
    product_id        INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku               VARCHAR(30)  NOT NULL UNIQUE,
    product_name      VARCHAR(150) NOT NULL,
    category_id       INT NOT NULL REFERENCES categories(category_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    supplier_id       INT NOT NULL REFERENCES suppliers(supplier_id)  ON UPDATE CASCADE ON DELETE RESTRICT,
    unit_cost         NUMERIC(12,2) NOT NULL CHECK (unit_cost >= 0),
    unit_price        NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    reorder_level     INT NOT NULL DEFAULT 10 CHECK (reorder_level >= 0),
    reorder_quantity  INT NOT NULL DEFAULT 50 CHECK (reorder_quantity > 0),
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (unit_price >= unit_cost)
);

CREATE TABLE stores (
    store_id    INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    store_name  VARCHAR(100) NOT NULL UNIQUE,
    city        VARCHAR(80)  NOT NULL,
    address     TEXT,
    phone       VARCHAR(30)
);

CREATE TABLE inventory (
    store_id          INT NOT NULL REFERENCES stores(store_id)     ON UPDATE CASCADE ON DELETE CASCADE,
    product_id        INT NOT NULL REFERENCES products(product_id) ON UPDATE CASCADE ON DELETE CASCADE,
    quantity_on_hand  INT NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
    last_updated      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (store_id, product_id)
);

CREATE TABLE employees (
    employee_id  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    store_id     INT NOT NULL REFERENCES stores(store_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    full_name    VARCHAR(100) NOT NULL,
    role         VARCHAR(30)  NOT NULL CHECK (role IN ('Manager','Cashier','Stock Clerk')),
    email        VARCHAR(120) UNIQUE,
    hire_date    DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE customers (
    customer_id  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name    VARCHAR(100) NOT NULL,
    email        VARCHAR(120) UNIQUE,
    phone        VARCHAR(30),
    city         VARCHAR(80),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sales (
    sale_id         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    store_id        INT NOT NULL REFERENCES stores(store_id)       ON UPDATE CASCADE ON DELETE RESTRICT,
    customer_id     INT          REFERENCES customers(customer_id) ON UPDATE CASCADE ON DELETE SET NULL,
    employee_id     INT NOT NULL REFERENCES employees(employee_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    sale_date       TIMESTAMPTZ NOT NULL DEFAULT now(),
    payment_method  VARCHAR(20) NOT NULL DEFAULT 'Cash' CHECK (payment_method IN ('Cash','Card','Online')),
    total_amount    NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (total_amount >= 0)
);

CREATE TABLE sale_items (
    sale_item_id  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sale_id       INT NOT NULL REFERENCES sales(sale_id)       ON UPDATE CASCADE ON DELETE CASCADE,
    product_id    INT NOT NULL REFERENCES products(product_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    quantity      INT NOT NULL CHECK (quantity > 0),
    unit_price    NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    discount      NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (discount >= 0),
    line_total    NUMERIC(14,2) GENERATED ALWAYS AS (quantity * unit_price - discount) STORED
);

CREATE TABLE purchase_orders (
    po_id          INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    supplier_id    INT NOT NULL REFERENCES suppliers(supplier_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    store_id       INT NOT NULL REFERENCES stores(store_id)       ON UPDATE CASCADE ON DELETE RESTRICT,
    order_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_date  DATE,
    status         VARCHAR(15) NOT NULL DEFAULT 'Draft'
                   CHECK (status IN ('Draft','Ordered','Received','Cancelled')),
    CHECK (expected_date IS NULL OR expected_date >= order_date)
);

CREATE TABLE purchase_order_items (
    po_item_id    INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    po_id         INT NOT NULL REFERENCES purchase_orders(po_id) ON UPDATE CASCADE ON DELETE CASCADE,
    product_id    INT NOT NULL REFERENCES products(product_id)   ON UPDATE CASCADE ON DELETE RESTRICT,
    quantity      INT NOT NULL CHECK (quantity > 0),
    unit_cost     NUMERIC(12,2) NOT NULL CHECK (unit_cost >= 0),
    received_qty  INT NOT NULL DEFAULT 0 CHECK (received_qty >= 0),
    UNIQUE (po_id, product_id),
    CHECK (received_qty <= quantity)
);

CREATE TABLE stock_movements (
    movement_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    store_id       INT NOT NULL REFERENCES stores(store_id)     ON UPDATE CASCADE ON DELETE CASCADE,
    product_id     INT NOT NULL REFERENCES products(product_id) ON UPDATE CASCADE ON DELETE CASCADE,
    movement_type  VARCHAR(15) NOT NULL CHECK (movement_type IN ('SALE','PURCHASE','ADJUSTMENT','RETURN')),
    quantity       INT NOT NULL CHECK (quantity <> 0),   -- negative = stock out, positive = stock in
    reference      VARCHAR(50),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

/* ---------------------------------------------------------------------
   2. INDEXES
   --------------------------------------------------------------------- */
CREATE INDEX idx_products_category   ON products(category_id);
CREATE INDEX idx_products_supplier   ON products(supplier_id);
CREATE INDEX idx_inventory_product   ON inventory(product_id);
CREATE INDEX idx_employees_store     ON employees(store_id);
CREATE INDEX idx_sales_store         ON sales(store_id);
CREATE INDEX idx_sales_customer      ON sales(customer_id);
CREATE INDEX idx_sales_date          ON sales(sale_date);
CREATE INDEX idx_sale_items_sale     ON sale_items(sale_id);
CREATE INDEX idx_sale_items_product  ON sale_items(product_id);
CREATE INDEX idx_po_supplier         ON purchase_orders(supplier_id);
CREATE INDEX idx_po_status           ON purchase_orders(status);
CREATE INDEX idx_movements_product   ON stock_movements(product_id, created_at);

/* ---------------------------------------------------------------------
   3. TRIGGER: a sale line reduces stock and updates the sale total
   --------------------------------------------------------------------- */
CREATE OR REPLACE FUNCTION fn_apply_sale_item()
RETURNS TRIGGER AS $$
DECLARE
    v_store INT;
BEGIN
    SELECT store_id INTO v_store FROM sales WHERE sale_id = NEW.sale_id;

    UPDATE inventory
       SET quantity_on_hand = quantity_on_hand - NEW.quantity,
           last_updated     = now()
     WHERE store_id = v_store AND product_id = NEW.product_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Product % is not stocked in store %', NEW.product_id, v_store;
    END IF;

    INSERT INTO stock_movements (store_id, product_id, movement_type, quantity, reference)
    VALUES (v_store, NEW.product_id, 'SALE', -NEW.quantity, 'SALE-' || NEW.sale_id);

    UPDATE sales
       SET total_amount = total_amount + (NEW.quantity * NEW.unit_price - NEW.discount)
     WHERE sale_id = NEW.sale_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sale_item_after_insert
AFTER INSERT ON sale_items
FOR EACH ROW EXECUTE FUNCTION fn_apply_sale_item();

/* ---------------------------------------------------------------------
   4. FUNCTION: receive a purchase order (adds stock)
      Usage:  SELECT receive_purchase_order(1);
   --------------------------------------------------------------------- */
CREATE OR REPLACE FUNCTION receive_purchase_order(p_po_id INT)
RETURNS VOID AS $$
DECLARE
    v_store  INT;
    v_status VARCHAR;
    r        RECORD;
BEGIN
    SELECT store_id, status INTO v_store, v_status
      FROM purchase_orders WHERE po_id = p_po_id;

    IF v_store IS NULL THEN
        RAISE EXCEPTION 'Purchase order % not found', p_po_id;
    ELSIF v_status <> 'Ordered' THEN
        RAISE EXCEPTION 'Purchase order % is % and cannot be received', p_po_id, v_status;
    END IF;

    FOR r IN
        SELECT product_id, quantity - received_qty AS qty
          FROM purchase_order_items WHERE po_id = p_po_id
    LOOP
        IF r.qty > 0 THEN
            INSERT INTO inventory (store_id, product_id, quantity_on_hand)
            VALUES (v_store, r.product_id, r.qty)
            ON CONFLICT (store_id, product_id)
            DO UPDATE SET quantity_on_hand = inventory.quantity_on_hand + EXCLUDED.quantity_on_hand,
                          last_updated     = now();

            INSERT INTO stock_movements (store_id, product_id, movement_type, quantity, reference)
            VALUES (v_store, r.product_id, 'PURCHASE', r.qty, 'PO-' || p_po_id);
        END IF;
    END LOOP;

    UPDATE purchase_order_items SET received_qty = quantity WHERE po_id = p_po_id;
    UPDATE purchase_orders      SET status = 'Received'     WHERE po_id = p_po_id;
END;
$$ LANGUAGE plpgsql;

/* ---------------------------------------------------------------------
   5. VIEWS (reports / intelligence)
   --------------------------------------------------------------------- */

-- 5.1 Stock status of every product in every store
CREATE OR REPLACE VIEW v_stock_status AS
SELECT s.store_id,
       s.store_name,
       p.product_id,
       p.sku,
       p.product_name,
       c.category_name,
       i.quantity_on_hand,
       p.reorder_level,
       CASE
           WHEN i.quantity_on_hand = 0                    THEN 'OUT OF STOCK'
           WHEN i.quantity_on_hand <= p.reorder_level / 2.0 THEN 'CRITICAL'
           WHEN i.quantity_on_hand <= p.reorder_level     THEN 'REORDER'
           ELSE 'OK'
       END AS stock_status
FROM inventory i
JOIN stores     s ON s.store_id    = i.store_id
JOIN products   p ON p.product_id  = i.product_id
JOIN categories c ON c.category_id = p.category_id
WHERE p.is_active;

-- 5.2 REORDER LIST: which products must be reordered, from whom, how much
CREATE OR REPLACE VIEW v_reorder_list AS
SELECT s.store_name,
       p.sku,
       p.product_name,
       sup.supplier_name,
       sup.lead_time_days,
       i.quantity_on_hand,
       p.reorder_level,
       COALESCE((SELECT SUM(poi.quantity - poi.received_qty)
                   FROM purchase_order_items poi
                   JOIN purchase_orders po ON po.po_id = poi.po_id
                  WHERE po.status = 'Ordered'
                    AND po.store_id   = i.store_id
                    AND poi.product_id = i.product_id), 0) AS qty_already_on_order,
       p.reorder_quantity                                  AS suggested_order_qty,
       (p.reorder_quantity * p.unit_cost)                  AS estimated_cost,
       CASE
           WHEN i.quantity_on_hand = 0                      THEN 'OUT OF STOCK'
           WHEN i.quantity_on_hand <= p.reorder_level / 2.0 THEN 'CRITICAL'
           ELSE 'REORDER'
       END AS priority
FROM inventory i
JOIN stores    s   ON s.store_id   = i.store_id
JOIN products  p   ON p.product_id = i.product_id
JOIN suppliers sup ON sup.supplier_id = p.supplier_id
WHERE p.is_active
  AND i.quantity_on_hand <= p.reorder_level
ORDER BY CASE
             WHEN i.quantity_on_hand = 0                      THEN 1
             WHEN i.quantity_on_hand <= p.reorder_level / 2.0 THEN 2
             ELSE 3
         END,
         s.store_name, p.product_name;

-- 5.3 Value of stock held in each store
CREATE OR REPLACE VIEW v_inventory_valuation AS
SELECT s.store_name,
       SUM(i.quantity_on_hand)                     AS total_units,
       SUM(i.quantity_on_hand * p.unit_cost)       AS stock_value_at_cost,
       SUM(i.quantity_on_hand * p.unit_price)      AS stock_value_at_retail
FROM inventory i
JOIN stores   s ON s.store_id   = i.store_id
JOIN products p ON p.product_id = i.product_id
GROUP BY s.store_name;

-- 5.4 Daily sales per store
CREATE OR REPLACE VIEW v_daily_sales AS
SELECT s.sale_date::date          AS sale_day,
       st.store_name,
       COUNT(*)                   AS total_invoices,
       SUM(s.total_amount)        AS total_revenue
FROM sales s
JOIN stores st ON st.store_id = s.store_id
GROUP BY s.sale_date::date, st.store_name
ORDER BY sale_day DESC, st.store_name;

-- 5.5 Monthly revenue
CREATE OR REPLACE VIEW v_monthly_revenue AS
SELECT date_trunc('month', sale_date)::date AS month,
       COUNT(*)                             AS total_invoices,
       SUM(total_amount)                    AS total_revenue
FROM sales
GROUP BY date_trunc('month', sale_date)
ORDER BY month DESC;

-- 5.6 Product performance: units sold, revenue and profit
CREATE OR REPLACE VIEW v_product_performance AS
SELECT p.sku,
       p.product_name,
       c.category_name,
       COALESCE(SUM(si.quantity), 0)                               AS units_sold,
       COALESCE(SUM(si.line_total), 0)                             AS revenue,
       COALESCE(SUM(si.line_total - si.quantity * p.unit_cost), 0) AS profit
FROM products p
JOIN categories c ON c.category_id = p.category_id
LEFT JOIN sale_items si ON si.product_id = p.product_id
GROUP BY p.sku, p.product_name, c.category_name
ORDER BY revenue DESC;

/* ---------------------------------------------------------------------
   6. SAMPLE DATA  (currency: PKR)
   --------------------------------------------------------------------- */

INSERT INTO categories (category_name, description) VALUES
 ('Grocery',       'Daily staples such as rice, oil and tea'),
 ('Dairy',         'Milk and dairy products'),
 ('Personal Care', 'Hygiene and beauty products'),
 ('Household',     'Cleaning and home supplies'),
 ('Beverages',     'Water and soft drinks');

INSERT INTO suppliers (supplier_name, contact_person, email, phone, city, lead_time_days) VALUES
 ('Grocery Wholesalers Ltd',   'Ahmed Raza',   'ahmed@groceryws.com',  '0300-1111111', 'Lahore',    3),
 ('Dairy Fresh Co.',           'Sana Malik',   'sana@dairyfresh.com',  '0301-2222222', 'Faisalabad', 1),
 ('Care & Home Distributors',  'Bilal Hussain','bilal@carehome.com',   '0302-3333333', 'Karachi',    5),
 ('Beverage Traders',          'Usman Tariq',  'usman@bevtraders.com', '0303-4444444', 'Lahore',     2);

INSERT INTO products (sku, product_name, category_id, supplier_id, unit_cost, unit_price, reorder_level, reorder_quantity) VALUES
 ('GRC-001', 'Basmati Rice 5kg',        1, 1, 1800, 2200, 20, 60),
 ('GRC-002', 'Cooking Oil 3L',          1, 1, 1500, 1800, 25, 60),
 ('GRC-003', 'Tea 950g',                1, 1, 1100, 1350, 15, 40),
 ('DRY-001', 'Fresh Milk 1L',           2, 2,  210,  250, 30, 100),
 ('DRY-002', 'Yogurt 1kg',              2, 2,  260,  320, 20, 50),
 ('PCR-001', 'Shampoo 400ml',           3, 3,  480,  620, 15, 40),
 ('PCR-002', 'Soap Bar',                3, 3,   90,  120, 40, 150),
 ('PCR-003', 'Toothpaste 150g',         3, 3,  150,  210, 25, 80),
 ('HSE-001', 'Detergent Powder 2kg',    4, 3,  700,  850, 20, 50),
 ('HSE-002', 'Dish Wash Liquid 500ml',  4, 3,  220,  290, 15, 40),
 ('BEV-001', 'Mineral Water 1.5L',      5, 4,   60,   90, 50, 200),
 ('BEV-002', 'Cola 2.25L',              5, 4,  170,  220, 30, 100);

INSERT INTO stores (store_name, city, address, phone) VALUES
 ('Main Branch',  'Lahore',  'Mall Road, Lahore',       '042-1111111'),
 ('City Branch',  'Karachi', 'Clifton Block 5, Karachi','021-2222222');

-- Opening stock (some items are intentionally low to demonstrate reorder alerts)
INSERT INTO inventory (store_id, product_id, quantity_on_hand) VALUES
 (1,1,50),(1,2,60),(1,3,12),(1,4,80),(1,5,40),(1,6,30),(1,7,100),(1,8,20),(1,9,45),(1,10,8),(1,11,120),(1,12,60),
 (2,1,30),(2,2,15),(2,3,35),(2,4,25),(2,5,30),(2,6,22),(2,7,60),(2,8,40),(2,9,18),(2,10,25),(2,11,30),(2,12,45);

INSERT INTO employees (store_id, full_name, role, email, hire_date) VALUES
 (1, 'Hamza Ali',    'Manager',     'hamza@retail.com',  '2024-01-10'),
 (1, 'Ayesha Khan',  'Cashier',     'ayesha@retail.com', '2024-03-15'),
 (2, 'Zain Abbas',   'Cashier',     'zain@retail.com',   '2024-05-20'),
 (2, 'Fatima Noor',  'Cashier',     'fatima@retail.com', '2024-06-01'),
 (1, 'Kamran Shah',  'Stock Clerk', 'kamran@retail.com', '2024-02-01');

INSERT INTO customers (full_name, email, phone, city) VALUES
 ('Ali Hassan',   'ali.hassan@mail.com',  '0311-1000001', 'Lahore'),
 ('Sara Ahmed',   'sara.ahmed@mail.com',  '0311-1000002', 'Lahore'),
 ('Omar Farooq',  'omar.farooq@mail.com', '0311-1000003', 'Karachi'),
 ('Hina Iqbal',   'hina.iqbal@mail.com',  '0311-1000004', 'Lahore'),
 ('Danish Mehmood','danish.m@mail.com',   '0311-1000005', 'Karachi');

-- Sales headers (total_amount is filled automatically by the trigger)
INSERT INTO sales (store_id, customer_id, employee_id, sale_date, payment_method) VALUES
 (1, 1,    2, '2026-09-20 11:15+05', 'Cash'),
 (1, 2,    2, '2026-09-22 16:40+05', 'Card'),
 (2, 3,    3, '2026-09-24 13:05+05', 'Cash'),
 (2, NULL, 3, '2026-09-25 18:30+05', 'Cash'),
 (1, 4,    2, '2026-09-27 12:20+05', 'Online'),
 (2, 5,    4, '2026-09-28 19:10+05', 'Card');

-- Sale lines (unit_price is copied from the product at time of sale)
INSERT INTO sale_items (sale_id, product_id, quantity, unit_price)
SELECT v.sale_id, v.product_id, v.qty, p.unit_price
FROM (VALUES
        (1, 1, 2), (1, 4, 5), (1, 7, 4),
        (2, 2, 1), (2, 11, 6), (2, 12, 2),
        (3, 6, 2), (3, 8, 3), (3, 9, 1),
        (4, 4, 3), (4, 11, 4),
        (5, 3, 2), (5, 5, 2), (5, 10, 1),
        (6, 1, 1), (6, 2, 2), (6, 9, 2)
     ) AS v(sale_id, product_id, qty)
JOIN products p ON p.product_id = v.product_id;

-- One open purchase order (restock of tea for Main Branch)
INSERT INTO purchase_orders (supplier_id, store_id, order_date, expected_date, status)
VALUES (1, 1, '2026-09-28', '2026-10-01', 'Ordered');

INSERT INTO purchase_order_items (po_id, product_id, quantity, unit_cost)
VALUES (1, 3, 40, 1100);

/* ---------------------------------------------------------------------
   7. QUICK TEST QUERIES
   ---------------------------------------------------------------------
   -- Which products must be reordered?
   SELECT * FROM retail.v_reorder_list;

   -- Full stock status
   SELECT * FROM retail.v_stock_status ORDER BY store_name, stock_status;

   -- Stock value per store
   SELECT * FROM retail.v_inventory_valuation;

   -- Sales reports
   SELECT * FROM retail.v_daily_sales;
   SELECT * FROM retail.v_monthly_revenue;
   SELECT * FROM retail.v_product_performance;

   -- Receive the purchase order (stock goes up automatically)
   SELECT retail.receive_purchase_order(1);
   --------------------------------------------------------------------- */
