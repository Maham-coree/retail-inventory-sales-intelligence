"""Admin-only transaction and query optimization demonstrations."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from ..database import engine, get_db
from ..deps import require_roles

router = APIRouter(prefix="/labs", tags=["database labs"])
ADMIN = Depends(require_roles("admin"))


def _step(step: str, sql: str, result: Any) -> dict[str, Any]:
    return {"step": step, "sql": sql, "result": result}


@router.post("/transactions/commit", summary="Demonstrate COMMIT")
def commit_demo(
    db: Session = Depends(get_db), _: dict[str, object] = ADMIN
) -> list[dict[str, Any]]:
    item_name = f"commit-{uuid4().hex}"
    sql = "INSERT INTO retail.lab_demo(item_name, qty) VALUES (:item_name, 1)"
    row = (
        db.execute(
            text(sql + " RETURNING item_id, item_name, qty"),
            {"item_name": item_name},
        )
        .mappings()
        .one()
    )
    db.commit()
    visible = (
        db.execute(
            text("SELECT item_id, item_name, qty FROM retail.lab_demo WHERE item_id=:id"),
            {"id": row["item_id"]},
        )
        .mappings()
        .one()
    )
    db.execute(
        text("DELETE FROM retail.lab_demo WHERE item_id=:id"),
        {"id": row["item_id"]},
    )
    db.commit()
    return [
        _step("insert", sql, dict(row)),
        _step("commit", "COMMIT", "Transaction committed"),
        _step("verify", "SELECT ... WHERE item_id = :id", dict(visible)),
        _step("cleanup", "DELETE FROM retail.lab_demo WHERE item_id = :id", "Demo row removed"),
    ]


@router.post("/transactions/rollback", summary="Demonstrate ROLLBACK")
def rollback_demo(
    db: Session = Depends(get_db), _: dict[str, object] = ADMIN
) -> list[dict[str, Any]]:
    item_name = f"rollback-{uuid4().hex}"
    row = (
        db.execute(
            text(
                "INSERT INTO retail.lab_demo(item_name, qty) "
                "VALUES (:item_name, 1) RETURNING item_id"
            ),
            {"item_name": item_name},
        )
        .mappings()
        .one()
    )
    item_id = row["item_id"]
    db.rollback()
    visible = db.execute(
        text("SELECT item_id FROM retail.lab_demo WHERE item_id=:id"),
        {"id": item_id},
    ).first()
    db.rollback()
    return [
        _step("insert", "INSERT INTO retail.lab_demo ...", {"item_id": item_id}),
        _step("rollback", "ROLLBACK", "Transaction rolled back"),
        _step(
            "verify", "SELECT item_id FROM retail.lab_demo WHERE item_id = :id", visible is not None
        ),
    ]


@router.post("/transactions/savepoint", summary="Demonstrate SAVEPOINT")
def savepoint_demo(
    db: Session = Depends(get_db), _: dict[str, object] = ADMIN
) -> list[dict[str, Any]]:
    suffix = uuid4().hex
    a = db.execute(
        text("INSERT INTO retail.lab_demo(item_name, qty) VALUES (:name, 1) RETURNING item_id"),
        {"name": f"savepoint-A-{suffix}"},
    ).scalar_one()
    db.execute(text("SAVEPOINT s1"))
    b = db.execute(
        text("INSERT INTO retail.lab_demo(item_name, qty) VALUES (:name, 2) RETURNING item_id"),
        {"name": f"savepoint-B-{suffix}"},
    ).scalar_one()
    db.execute(text("ROLLBACK TO SAVEPOINT s1"))
    db.commit()
    rows = (
        db.execute(
            text(
                "SELECT item_id, item_name, qty FROM retail.lab_demo "
                "WHERE item_id IN (:a, :b) ORDER BY item_id"
            ),
            {"a": a, "b": b},
        )
        .mappings()
        .all()
    )
    db.execute(text("DELETE FROM retail.lab_demo WHERE item_id=:id"), {"id": a})
    db.commit()
    return [
        _step("insert A", "INSERT INTO retail.lab_demo ... ('savepoint-A-*', 1)", a),
        _step("savepoint", "SAVEPOINT s1", "Savepoint created"),
        _step("insert B", "INSERT INTO retail.lab_demo ... ('savepoint-B', 2)", b),
        _step("rollback to savepoint", "ROLLBACK TO SAVEPOINT s1", "B was discarded"),
        _step("commit and verify", "COMMIT; SELECT ...", [dict(row) for row in rows]),
        _step(
            "cleanup",
            "DELETE FROM retail.lab_demo WHERE item_id = :id",
            "Persisted demo row removed",
        ),
    ]


@router.post("/transactions/isolation", summary="Demonstrate transaction isolation")
def isolation_demo(
    db: Session = Depends(get_db), _: dict[str, object] = ADMIN
) -> list[dict[str, Any]]:
    default_level = db.execute(text("SHOW transaction_isolation")).scalar_one()
    db.rollback()
    steps = [_step("current isolation", "SHOW transaction_isolation", default_level)]
    for level in ("READ COMMITTED", "REPEATABLE READ"):
        with engine.connect() as reader, engine.connect() as writer:
            reader = reader.execution_options(isolation_level=level)
            reader_tx = reader.begin()
            current = reader.execute(
                text("SELECT item_id, qty FROM retail.lab_demo ORDER BY item_id LIMIT 1")
            ).first()
            if current is None:
                reader_tx.rollback()
                raise HTTPException(409, "Lab seed row is missing")
            row_id, original_qty = current
            writer.execute(
                text("UPDATE retail.lab_demo SET qty=qty+1 WHERE item_id=:id"),
                {"id": row_id},
            )
            writer.commit()
            second = reader.execute(
                text("SELECT qty FROM retail.lab_demo WHERE item_id=:id"),
                {"id": row_id},
            ).scalar_one()
            reader_tx.rollback()
            with engine.begin() as restore:
                restore.execute(
                    text("UPDATE retail.lab_demo SET qty=:qty WHERE item_id=:id"),
                    {"qty": original_qty, "id": row_id},
                )
            steps.append(
                _step(
                    level,
                    "Read qty; another transaction commits qty+1; read qty again",
                    {"first_read": original_qty, "second_read": second},
                )
            )
    return steps


@router.post("/transactions/locks", summary="Demonstrate row locks and NOWAIT")
def lock_demo(_: dict[str, object] = ADMIN) -> list[dict[str, Any]]:
    with engine.connect() as first, engine.connect() as second:
        tx = first.begin()
        row_id = first.execute(
            text("SELECT item_id FROM retail.lab_demo ORDER BY item_id LIMIT 1 FOR UPDATE")
        ).scalar_one_or_none()
        if row_id is None:
            tx.rollback()
            raise HTTPException(409, "Lab seed row is missing")
        second.begin()
        try:
            second.execute(
                text("SELECT item_id FROM retail.lab_demo WHERE item_id=:id FOR UPDATE NOWAIT"),
                {"id": row_id},
            )
            result = "Unexpectedly acquired lock"
            code = None
        except DBAPIError as exc:
            code = getattr(exc.orig, "sqlstate", None)
            result = str(code)
            second.rollback()
        finally:
            tx.rollback()
    return [
        _step("connection A", "SELECT ... FOR UPDATE", {"item_id": row_id}),
        _step("connection B", "SELECT ... FOR UPDATE NOWAIT", {"sqlstate": code, "result": result}),
    ]


@router.post("/transactions/deadlock", summary="Demonstrate PostgreSQL deadlock detection")
def deadlock_demo(_: dict[str, object] = ADMIN) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        ids = (
            conn.execute(text("SELECT item_id FROM retail.lab_demo ORDER BY item_id LIMIT 2"))
            .scalars()
            .all()
        )
    if len(ids) < 2:
        raise HTTPException(409, "Two lab_demo rows are required")
    barrier = Barrier(2)

    def worker(first_id: int, second_id: int) -> str:
        transaction = None
        try:
            with engine.connect() as conn:
                transaction = conn.begin()
                conn.execute(
                    text("UPDATE retail.lab_demo SET qty=qty WHERE item_id=:id"),
                    {"id": first_id},
                )
                barrier.wait(timeout=5)
                conn.execute(
                    text("UPDATE retail.lab_demo SET qty=qty WHERE item_id=:id"),
                    {"id": second_id},
                )
                transaction.commit()
                return "committed"
        except DBAPIError as exc:
            if transaction is not None and transaction.is_active:
                transaction.rollback()
            code = getattr(exc.orig, "sqlstate", None)
            return f"aborted: {code}"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda pair: worker(*pair), ((ids[0], ids[1]), (ids[1], ids[0]))))
    if not any("40P01" in outcome for outcome in outcomes):
        raise HTTPException(500, f"Expected deadlock SQLSTATE 40P01; got {outcomes}")
    return [
        _step(
            "opposing updates",
            "Two connections update the same two lab rows in opposite order",
            {"outcomes": outcomes, "deadlock_sqlstate": "40P01"},
        )
    ]


@router.post("/transactions/unique-violation", summary="Demonstrate unique-violation mapping")
def unique_violation_demo(
    db: Session = Depends(get_db), _: dict[str, object] = ADMIN
) -> list[dict[str, Any]]:
    name = f"__unique_demo__{uuid4().hex}"
    try:
        db.execute(
            text(
                "INSERT INTO retail.lab_demo(item_name, qty) "
                "VALUES (:name, 1) ON CONFLICT (item_name) DO NOTHING"
            ),
            {"name": name},
        )
        db.commit()
        db.execute(
            text("INSERT INTO retail.lab_demo(item_name, qty) VALUES (:name, 2)"),
            {"name": name},
        )
        db.commit()
        result = {"status_code": 201, "unexpected": "duplicate accepted"}
    except IntegrityError as exc:
        db.rollback()
        result = {"sqlstate": getattr(exc.orig, "sqlstate", None), "http_status": 409}
    db.execute(
        text("DELETE FROM retail.lab_demo WHERE item_name=:name"),
        {"name": name},
    )
    db.commit()
    return [
        _step("duplicate insert", "INSERT same unique item_name twice", result),
    ]


@router.post("/optimization/seed", summary="Seed 200,000 lab orders once")
def seed_optimization(
    db: Session = Depends(get_db), _: dict[str, object] = ADMIN
) -> dict[str, int | str]:
    existing = db.execute(text("SELECT count(*) FROM retail.lab_orders")).scalar_one()
    if existing:
        return {"rows": existing, "message": "Seed skipped; lab_orders is not empty"}
    db.execute(
        text(
            "INSERT INTO retail.lab_orders(customer_ref, amount, created_at) "
            "SELECT (g % 10000)::text, (g % 50000)::numeric / 100, "
            "now() - (g % 365) * interval '1 day' FROM generate_series(1, 200000) g"
        )
    )
    db.commit()
    return {"rows": 200000, "message": "Optimization data seeded"}


@router.post("/optimization/run", summary="Compare query plans with and without a B-tree index")
def optimization_run(
    customer_ref: str = Query(min_length=1, max_length=80),
    db: Session = Depends(get_db),
    _: dict[str, object] = ADMIN,
) -> dict[str, Any]:
    count = db.execute(text("SELECT count(*) FROM retail.lab_orders")).scalar_one()
    if not count:
        raise HTTPException(409, "Run optimization seed before the comparison")
    explain = text(
        "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM retail.lab_orders "
        "WHERE customer_ref=:customer_ref"
    )
    db.execute(text("DROP INDEX IF EXISTS retail.idx_lab_orders_customer_ref_demo"))
    db.commit()
    before = [row[0] for row in db.execute(explain, {"customer_ref": customer_ref})]
    try:
        db.execute(
            text(
                "CREATE INDEX idx_lab_orders_customer_ref_demo "
                "ON retail.lab_orders USING btree(customer_ref)"
            )
        )
        db.execute(text("ANALYZE retail.lab_orders"))
        after = [row[0] for row in db.execute(explain, {"customer_ref": customer_ref})]
        db.commit()
    finally:
        db.rollback()
        db.execute(text("DROP INDEX IF EXISTS retail.idx_lab_orders_customer_ref_demo"))
        db.commit()
    return {
        "customer_ref": customer_ref,
        "before_plan": before,
        "after_plan": after,
        "before_execution_ms": _execution_ms(before),
        "after_execution_ms": _execution_ms(after),
    }


def _execution_ms(plan: list[str]) -> float | None:
    for line in plan:
        if line.strip().startswith("Execution Time:"):
            try:
                return float(line.split(":", 1)[1].strip().split()[0])
            except (ValueError, IndexError):
                return None
    return None
