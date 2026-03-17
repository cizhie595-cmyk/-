"""
Amazon Visionary Sourcing Tool - 数据库初始化脚本

按顺序执行所有 SQL 文件：
  1. schema.sql          - 核心业务表（keywords, products, reviews, etc.）
  2. user_schema.sql     - 用户系统表（users, login_logs, tasks）
  3. migrations/001_*    - 初始数据迁移
  4. migrations/002_*    - API 密钥与设置
  5. migrations/003_*    - 商业化（订阅、返佣）
  6. migrations/004_*    - 选品项目与 3D 资产

用法:
  python database/init_db.py              # 完整初始化
  python database/init_db.py --check      # 仅检查表状态
  python database/init_db.py --migrate    # 仅执行迁移文件
"""

import pymysql
import os
import sys
import glob
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.database import db_config

# SQL 文件执行顺序
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCHEMA_FILES = [
    os.path.join(BASE_DIR, "schema.sql"),
    os.path.join(BASE_DIR, "user_schema.sql"),
]

MIGRATION_DIR = os.path.join(BASE_DIR, "migrations")


def get_connection(use_database: bool = False):
    """获取数据库连接"""
    params = {
        "host": db_config.host,
        "port": db_config.port,
        "user": db_config.user,
        "password": db_config.password,
        "charset": db_config.charset,
    }
    if use_database:
        params["database"] = db_config.database
    return pymysql.connect(**params)


def execute_sql_file(conn, filepath: str) -> tuple[int, int]:
    """
    执行单个 SQL 文件。

    :return: (成功数, 失败数)
    """
    if not os.path.exists(filepath):
        print(f"  [SKIP] 文件不存在: {filepath}")
        return 0, 0

    filename = os.path.basename(filepath)
    print(f"\n  [EXEC] {filename}")

    with open(filepath, "r", encoding="utf-8") as f:
        sql_content = f.read()

    success = 0
    failed = 0

    with conn.cursor() as cursor:
        # 按分号拆分 SQL 语句
        statements = sql_content.split(";")
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt or stmt.startswith("--") or stmt.startswith("/*"):
                continue
            try:
                cursor.execute(stmt)
                success += 1
            except pymysql.Error as e:
                error_code = e.args[0] if e.args else 0
                # 忽略 "table already exists" 和 "duplicate column" 等非致命错误
                if error_code in (1050, 1060, 1061, 1068, 1091):
                    success += 1  # 幂等操作，视为成功
                else:
                    failed += 1
                    print(f"    [WARN] {e}")
                    print(f"           SQL: {stmt[:100]}...")

    conn.commit()
    print(f"    -> {success} succeeded, {failed} failed")
    return success, failed


def create_database(conn):
    """创建数据库（如果不存在）"""
    db_name = db_config.database
    print(f"\n  [DB] Creating database '{db_name}' if not exists...")
    with conn.cursor() as cursor:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{db_name}`")
    conn.commit()
    print(f"    -> Database '{db_name}' ready")


def create_migration_tracking_table(conn):
    """创建迁移追踪表，记录已执行的迁移"""
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                filename VARCHAR(255) NOT NULL UNIQUE,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()


def get_executed_migrations(conn) -> set:
    """获取已执行的迁移文件列表"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT filename FROM _migrations")
            return {row[0] for row in cursor.fetchall()}
    except pymysql.Error:
        return set()


def record_migration(conn, filename: str):
    """记录已执行的迁移"""
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT IGNORE INTO _migrations (filename) VALUES (%s)",
            (filename,)
        )
    conn.commit()


def init_schemas(conn) -> tuple[int, int]:
    """执行所有 schema 文件"""
    total_success = 0
    total_failed = 0

    print("\n" + "=" * 50)
    print("  Phase 1: Core Schema Files")
    print("=" * 50)

    for filepath in SCHEMA_FILES:
        s, f = execute_sql_file(conn, filepath)
        total_success += s
        total_failed += f

    return total_success, total_failed


def run_migrations(conn) -> tuple[int, int]:
    """按顺序执行所有迁移文件"""
    total_success = 0
    total_failed = 0

    print("\n" + "=" * 50)
    print("  Phase 2: Migration Files")
    print("=" * 50)

    create_migration_tracking_table(conn)
    executed = get_executed_migrations(conn)

    # 按文件名排序获取所有迁移文件
    migration_files = sorted(glob.glob(os.path.join(MIGRATION_DIR, "*.sql")))

    if not migration_files:
        print("\n  [INFO] No migration files found")
        return 0, 0

    for filepath in migration_files:
        filename = os.path.basename(filepath)

        if filename in executed:
            print(f"\n  [SKIP] {filename} (already executed)")
            continue

        s, f = execute_sql_file(conn, filepath)
        total_success += s
        total_failed += f

        if f == 0:
            record_migration(conn, filename)

    return total_success, total_failed


def check_tables():
    """检查所有表是否创建成功"""
    conn = get_connection(use_database=True)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()

            print(f"\n{'=' * 50}")
            print(f"  Database: {db_config.database}")
            print(f"  Tables: {len(tables)}")
            print(f"{'=' * 50}")

            for table in tables:
                table_name = table[0]
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                    count = cursor.fetchone()[0]
                    print(f"  + {table_name:<35} ({count:>6} rows)")
                except pymysql.Error:
                    print(f"  ! {table_name:<35} (error reading)")

            print(f"{'=' * 50}")

            # 检查迁移状态
            try:
                cursor.execute("SELECT filename, executed_at FROM _migrations ORDER BY id")
                migrations = cursor.fetchall()
                if migrations:
                    print(f"\n  Executed Migrations:")
                    for m in migrations:
                        print(f"    + {m[0]} ({m[1]})")
            except pymysql.Error:
                pass

    finally:
        conn.close()


def full_init():
    """完整初始化：创建数据库 + schema + migrations"""
    conn = get_connection(use_database=False)
    try:
        create_database(conn)

        s1, f1 = init_schemas(conn)
        s2, f2 = run_migrations(conn)

        total_success = s1 + s2
        total_failed = f1 + f2

        print(f"\n{'=' * 50}")
        print(f"  INITIALIZATION COMPLETE")
        print(f"  Total: {total_success} succeeded, {total_failed} failed")
        print(f"  Database: {db_config.database}")
        print(f"  Host: {db_config.host}:{db_config.port}")
        print(f"{'=' * 50}")

        return total_failed == 0

    except Exception as e:
        print(f"\n  [ERROR] Database initialization failed: {e}")
        return False
    finally:
        conn.close()


def migrate_only():
    """仅执行迁移文件"""
    conn = get_connection(use_database=True)
    try:
        s, f = run_migrations(conn)
        print(f"\n  Migration complete: {s} succeeded, {f} failed")
        return f == 0
    except Exception as e:
        print(f"\n  [ERROR] Migration failed: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Amazon Visionary Sourcing Tool - Database Initialization"
    )
    parser.add_argument("--check", action="store_true",
                        help="Only check table status")
    parser.add_argument("--migrate", action="store_true",
                        help="Only run migration files")
    args = parser.parse_args()

    print("=" * 50)
    print("  Amazon Visionary Sourcing Tool")
    print("  Database Initialization")
    print("=" * 50)

    if args.check:
        check_tables()
    elif args.migrate:
        if migrate_only():
            check_tables()
        else:
            print("\nMigration failed. Check errors above.")
            sys.exit(1)
    else:
        if full_init():
            check_tables()
        else:
            print("\nInitialization failed. Check database config:")
            print("  Environment: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME")
            print("  Or edit: config/database.py")
            sys.exit(1)
