"""
Coupang 选品系统 - 数据库初始化脚本
运行此脚本自动创建数据库和所有表
用法: python database/init_db.py
"""

import pymysql
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.database import db_config


def init_database():
    """读取 schema.sql 并执行建表"""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

    if not os.path.exists(schema_path):
        print("[ERROR] 找不到 schema.sql 文件")
        return False

    with open(schema_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # 先连接MySQL（不指定数据库），创建数据库
    conn = pymysql.connect(
        host=db_config.host,
        port=db_config.port,
        user=db_config.user,
        password=db_config.password,
        charset=db_config.charset,
    )

    try:
        with conn.cursor() as cursor:
            # 按分号拆分SQL语句并逐条执行
            statements = sql_content.split(";")
            success_count = 0
            for stmt in statements:
                stmt = stmt.strip()
                if not stmt or stmt.startswith("--"):
                    continue
                try:
                    cursor.execute(stmt)
                    success_count += 1
                except pymysql.Error as e:
                    print(f"[WARN] SQL执行警告: {e}")
                    print(f"       语句: {stmt[:80]}...")

            conn.commit()
            print(f"[SUCCESS] 数据库初始化完成！共执行 {success_count} 条SQL语句")
            print(f"[INFO] 数据库名: {db_config.database}")
            print(f"[INFO] 连接地址: {db_config.host}:{db_config.port}")
            return True

    except Exception as e:
        print(f"[ERROR] 数据库初始化失败: {e}")
        return False
    finally:
        conn.close()


def check_tables():
    """检查所有表是否创建成功"""
    conn = pymysql.connect(**db_config.pymysql_config)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"\n[INFO] 数据库中共有 {len(tables)} 张表:")
            print("-" * 40)
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                count = cursor.fetchone()[0]
                print(f"  ✓ {table_name} ({count} 条记录)")
            print("-" * 40)
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 50)
    print("  Coupang 选品系统 - 数据库初始化")
    print("=" * 50)
    print()

    if init_database():
        check_tables()
    else:
        print("\n请检查数据库配置后重试。")
        print("配置方式: 设置环境变量 DB_HOST, DB_PORT, DB_USER, DB_PASSWORD")
        print("或修改 config/database.py 文件")
