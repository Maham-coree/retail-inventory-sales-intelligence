/*
 * pgAdmin Query Tool: open the target database, choose Tools > Query Tool,
 * open this file, and execute sections individually. To open a psql terminal,
 * use Tools > PSQL Tool. All data-changing business-object examples are wrapped
 * in ROLLBACK; persistent examples operate only in retail.lab_*.
 */

-- 1. DCL: grants, revokes, and SET ROLE (rolled back).
BEGIN;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'role_admin') THEN
        EXECUTE 'GRANT SELECT ON retail.lab_demo TO role_admin';
        EXECUTE 'REVOKE SELECT ON retail.lab_demo FROM role_admin';
        IF pg_has_role(current_user, 'role_admin', 'MEMBER') THEN
            EXECUTE 'SET LOCAL ROLE role_admin';
            EXECUTE 'RESET ROLE';
        END IF;
    END IF;
END
$$;
ROLLBACK;
-- Equivalent role-switch syntax for a login that is a member of the role:
-- BEGIN; SET LOCAL ROLE role_admin; SELECT current_user; ROLLBACK;

-- 2. TCL: commit visibility, rollback, and savepoint; remove the committed row.
BEGIN;
INSERT INTO retail.lab_demo(item_name, qty)
VALUES ('pgadmin-commit-demo', 7)
ON CONFLICT (item_name) DO UPDATE SET qty = EXCLUDED.qty;
COMMIT;
SELECT * FROM retail.lab_demo WHERE item_name = 'pgadmin-commit-demo';
DELETE FROM retail.lab_demo WHERE item_name = 'pgadmin-commit-demo';

BEGIN;
INSERT INTO retail.lab_demo(item_name, qty)
VALUES ('pgadmin-rollback-demo', 8)
ON CONFLICT (item_name) DO UPDATE SET qty = EXCLUDED.qty;
ROLLBACK;
SELECT * FROM retail.lab_demo WHERE item_name = 'pgadmin-rollback-demo';

BEGIN;
INSERT INTO retail.lab_demo(item_name, qty)
VALUES ('pgadmin-savepoint-A', 1)
ON CONFLICT (item_name) DO UPDATE SET qty = EXCLUDED.qty;
SAVEPOINT s1;
INSERT INTO retail.lab_demo(item_name, qty)
VALUES ('pgadmin-savepoint-B', 2)
ON CONFLICT (item_name) DO UPDATE SET qty = EXCLUDED.qty;
ROLLBACK TO SAVEPOINT s1;
COMMIT;
SELECT * FROM retail.lab_demo
WHERE item_name IN ('pgadmin-savepoint-A', 'pgadmin-savepoint-B');
DELETE FROM retail.lab_demo WHERE item_name = 'pgadmin-savepoint-A';

-- 3. Isolation levels: run in two query tabs with a seeded lab_demo row.
-- Tab A: BEGIN; SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
--        SELECT qty FROM retail.lab_demo WHERE item_id = 1;
-- Tab B: UPDATE retail.lab_demo SET qty = qty + 1 WHERE item_id = 1; COMMIT;
-- Tab A: SELECT qty FROM retail.lab_demo WHERE item_id = 1; ROLLBACK;
-- Repeat with REPEATABLE READ in Tab A; its second read retains its snapshot.
-- Restore the lab-only value after the demonstration if the seed row was changed.
SHOW transaction_isolation;

-- 4. Row locks: run Tab A first and keep its transaction open while running Tab B.
-- Tab A: BEGIN; SELECT item_id FROM retail.lab_demo ORDER BY item_id LIMIT 1
--        FOR UPDATE;
-- Tab B: SELECT item_id FROM retail.lab_demo ORDER BY item_id LIMIT 1
--        FOR UPDATE NOWAIT; -- expected SQLSTATE 55P03
-- Tab A: ROLLBACK;

-- 5. Deadlock: run the first update in Tab A and Tab B before each second update.
-- Tab A: BEGIN; UPDATE retail.lab_demo SET qty = qty WHERE item_id = 1;
-- Tab B: BEGIN; UPDATE retail.lab_demo SET qty = qty WHERE item_id = 2;
-- Tab A: UPDATE retail.lab_demo SET qty = qty WHERE item_id = 2;
-- Tab B: UPDATE retail.lab_demo SET qty = qty WHERE item_id = 1;
-- PostgreSQL aborts one transaction with SQLSTATE 40P01; issue ROLLBACK in both tabs.

-- 6. Query plans: only the lab_orders table/index is changed; transaction rolls back.
BEGIN;
DROP INDEX IF EXISTS retail.idx_pgadmin_lab_orders_customer_ref;
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM retail.lab_orders WHERE customer_ref = '42';
CREATE INDEX idx_pgadmin_lab_orders_customer_ref
    ON retail.lab_orders USING btree(customer_ref);
ANALYZE retail.lab_orders;
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM retail.lab_orders WHERE customer_ref = '42';
ROLLBACK;

-- 7. Unique violation 23505 caught and reported; outer transaction is rolled back.
BEGIN;
DO $$
BEGIN
    INSERT INTO retail.lab_demo(item_name, qty)
    VALUES ('pgadmin-unique-demo', 1);
    INSERT INTO retail.lab_demo(item_name, qty)
    VALUES ('pgadmin-unique-demo', 2);
EXCEPTION WHEN unique_violation THEN
    RAISE NOTICE 'Expected duplicate key error: SQLSTATE %', SQLSTATE;
END
$$;
ROLLBACK;

-- 8. Materialized-view refresh is rolled back after demonstrating the command.
BEGIN;
REFRESH MATERIALIZED VIEW retail.mv_monthly_sales;
ROLLBACK;

-- 9. Stock procedure invocation is rolled back, so inventory and ledger remain unchanged.
-- Replace the two example IDs only with valid existing store/product IDs.
BEGIN;
CALL retail.sp_adjust_stock(1, 1, 1, 'pgAdmin rollback demo');
ROLLBACK;

-- 10. RIGHT and FULL joins are read-only. The transaction is ended explicitly.
BEGIN;
SELECT s.supplier_name, p.product_name
FROM retail.products p
RIGHT JOIN retail.suppliers s ON s.supplier_id = p.supplier_id
ORDER BY s.supplier_name, p.product_name;
SELECT c.full_name, s.sale_id, s.total_amount
FROM retail.customers c
FULL JOIN retail.sales s ON s.customer_id = c.customer_id
ORDER BY c.full_name, s.sale_id;
ROLLBACK;

-- 11. PostgreSQL role listing (read-only).
BEGIN;
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin
FROM pg_roles
ORDER BY rolname;
ROLLBACK;

-- 12. Schema verification counts (read-only).
BEGIN;
SELECT 'tables' AS object_type, count(*) AS object_count
FROM information_schema.tables
WHERE table_schema = 'retail' AND table_type = 'BASE TABLE'
UNION ALL
SELECT 'views', count(*)
FROM information_schema.views WHERE table_schema = 'retail'
UNION ALL
SELECT 'indexes', count(*)
FROM pg_indexes WHERE schemaname = 'retail'
UNION ALL
SELECT 'constraints', count(*)
FROM information_schema.table_constraints WHERE constraint_schema = 'retail'
UNION ALL
SELECT 'triggers', count(*)
FROM information_schema.triggers WHERE trigger_schema = 'retail';
ROLLBACK;
