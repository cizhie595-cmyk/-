"""
Coupang 选品系统 - 数据清理与归档策略
定期清理过期数据、归档历史记录、释放存储空间
"""

import os
import json
import shutil
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger()


# ============================================================
# 清理策略配置
# ============================================================

class CleanupPolicy:
    """清理策略配置"""

    # 数据保留天数
    TASK_RESULT_RETENTION_DAYS = int(os.getenv("CLEANUP_TASK_RESULT_DAYS", "90"))
    AUDIT_LOG_RETENTION_DAYS = int(os.getenv("CLEANUP_AUDIT_LOG_DAYS", "180"))
    NOTIFICATION_RETENTION_DAYS = int(os.getenv("CLEANUP_NOTIFICATION_DAYS", "30"))
    TEMP_FILE_RETENTION_DAYS = int(os.getenv("CLEANUP_TEMP_FILE_DAYS", "7"))
    SESSION_RETENTION_DAYS = int(os.getenv("CLEANUP_SESSION_DAYS", "30"))
    ARCHIVED_PROJECT_RETENTION_DAYS = int(os.getenv("CLEANUP_ARCHIVED_PROJECT_DAYS", "365"))

    # 归档配置
    ARCHIVE_ENABLED = os.getenv("ARCHIVE_ENABLED", "true").lower() == "true"
    ARCHIVE_DIR = os.getenv("ARCHIVE_DIR", "/data/archives")

    # 临时文件目录
    TEMP_DIRS = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "temp"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "uploads", "temp"),
    ]


class DataCleaner:
    """数据清理器"""

    def __init__(self):
        self._db = None

    def _get_db(self):
        if self._db is None:
            try:
                from database.connection import db
                self._db = db
            except Exception:
                pass
        return self._db

    def run_all(self, dry_run: bool = False) -> dict:
        """
        执行全部清理任务

        :param dry_run: 仅预览，不实际删除
        :return: 清理结果汇总
        """
        logger.info(f"[Cleanup] 开始数据清理 (dry_run={dry_run})")
        results = {}

        results["expired_tasks"] = self.cleanup_expired_tasks(dry_run)
        results["old_audit_logs"] = self.cleanup_audit_logs(dry_run)
        results["old_notifications"] = self.cleanup_notifications(dry_run)
        results["temp_files"] = self.cleanup_temp_files(dry_run)
        results["expired_sessions"] = self.cleanup_expired_sessions(dry_run)
        results["expired_invitations"] = self.cleanup_expired_invitations(dry_run)

        total_cleaned = sum(r.get("count", 0) for r in results.values())
        logger.info(f"[Cleanup] 清理完成: 共处理 {total_cleaned} 条记录")

        return {
            "success": True,
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat(),
            "total_cleaned": total_cleaned,
            "details": results,
        }

    def cleanup_expired_tasks(self, dry_run: bool = False) -> dict:
        """清理过期的任务结果"""
        db = self._get_db()
        if not db:
            return {"count": 0, "skipped": True}

        cutoff = datetime.now() - timedelta(days=CleanupPolicy.TASK_RESULT_RETENTION_DAYS)
        try:
            count_row = db.fetch_one(
                "SELECT COUNT(*) AS cnt FROM analysis_tasks WHERE status IN ('completed','failed') AND created_at < %s",
                (cutoff,),
            )
            count = count_row["cnt"] if count_row else 0

            if not dry_run and count > 0:
                # 归档后删除
                if CleanupPolicy.ARCHIVE_ENABLED:
                    self._archive_tasks(cutoff)

                db.execute(
                    "DELETE FROM analysis_tasks WHERE status IN ('completed','failed') AND created_at < %s",
                    (cutoff,),
                )

            logger.info(f"[Cleanup] 过期任务: {count} 条 (cutoff={cutoff.date()})")
            return {"count": count, "cutoff": str(cutoff.date())}

        except Exception as e:
            logger.error(f"[Cleanup] 清理任务失败: {e}")
            return {"count": 0, "error": str(e)}

    def cleanup_audit_logs(self, dry_run: bool = False) -> dict:
        """清理过期审计日志"""
        db = self._get_db()
        if not db:
            return {"count": 0, "skipped": True}

        cutoff = datetime.now() - timedelta(days=CleanupPolicy.AUDIT_LOG_RETENTION_DAYS)
        try:
            count_row = db.fetch_one(
                "SELECT COUNT(*) AS cnt FROM audit_logs WHERE created_at < %s", (cutoff,)
            )
            count = count_row["cnt"] if count_row else 0

            if not dry_run and count > 0:
                db.execute("DELETE FROM audit_logs WHERE created_at < %s", (cutoff,))

            logger.info(f"[Cleanup] 过期审计日志: {count} 条")
            return {"count": count, "cutoff": str(cutoff.date())}

        except Exception as e:
            logger.error(f"[Cleanup] 清理审计日志失败: {e}")
            return {"count": 0, "error": str(e)}

    def cleanup_notifications(self, dry_run: bool = False) -> dict:
        """清理过期通知"""
        db = self._get_db()
        if not db:
            return {"count": 0, "skipped": True}

        cutoff = datetime.now() - timedelta(days=CleanupPolicy.NOTIFICATION_RETENTION_DAYS)
        try:
            count_row = db.fetch_one(
                "SELECT COUNT(*) AS cnt FROM notifications WHERE is_read = 1 AND created_at < %s",
                (cutoff,),
            )
            count = count_row["cnt"] if count_row else 0

            if not dry_run and count > 0:
                db.execute(
                    "DELETE FROM notifications WHERE is_read = 1 AND created_at < %s",
                    (cutoff,),
                )

            logger.info(f"[Cleanup] 过期通知: {count} 条")
            return {"count": count, "cutoff": str(cutoff.date())}

        except Exception as e:
            logger.error(f"[Cleanup] 清理通知失败: {e}")
            return {"count": 0, "error": str(e)}

    def cleanup_temp_files(self, dry_run: bool = False) -> dict:
        """清理临时文件"""
        cutoff = datetime.now() - timedelta(days=CleanupPolicy.TEMP_FILE_RETENTION_DAYS)
        cutoff_ts = cutoff.timestamp()
        count = 0

        for temp_dir in CleanupPolicy.TEMP_DIRS:
            if not os.path.exists(temp_dir):
                continue

            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        if os.path.getmtime(fpath) < cutoff_ts:
                            count += 1
                            if not dry_run:
                                os.remove(fpath)
                    except Exception:
                        pass

                # 删除空目录
                for dname in dirs:
                    dpath = os.path.join(root, dname)
                    try:
                        if not dry_run and not os.listdir(dpath):
                            os.rmdir(dpath)
                    except Exception:
                        pass

        logger.info(f"[Cleanup] 临时文件: {count} 个")
        return {"count": count, "cutoff": str(cutoff.date())}

    def cleanup_expired_sessions(self, dry_run: bool = False) -> dict:
        """清理过期会话/Token"""
        db = self._get_db()
        if not db:
            return {"count": 0, "skipped": True}

        cutoff = datetime.now() - timedelta(days=CleanupPolicy.SESSION_RETENTION_DAYS)
        try:
            # 清理过期的 OAuth state 和邀请
            count = 0

            # 过期邀请
            row = db.fetch_one(
                "SELECT COUNT(*) AS cnt FROM team_invitations WHERE expires_at < NOW()", ()
            )
            inv_count = row["cnt"] if row else 0

            if not dry_run and inv_count > 0:
                db.execute("DELETE FROM team_invitations WHERE expires_at < NOW()", ())

            count += inv_count

            logger.info(f"[Cleanup] 过期会话/邀请: {count} 条")
            return {"count": count}

        except Exception as e:
            logger.error(f"[Cleanup] 清理会话失败: {e}")
            return {"count": 0, "error": str(e)}

    def cleanup_expired_invitations(self, dry_run: bool = False) -> dict:
        """清理过期团队邀请"""
        db = self._get_db()
        if not db:
            return {"count": 0, "skipped": True}

        try:
            count_row = db.fetch_one(
                "SELECT COUNT(*) AS cnt FROM team_invitations WHERE expires_at < NOW() AND accepted = 0",
                (),
            )
            count = count_row["cnt"] if count_row else 0

            if not dry_run and count > 0:
                db.execute(
                    "DELETE FROM team_invitations WHERE expires_at < NOW() AND accepted = 0", ()
                )

            return {"count": count}

        except Exception as e:
            return {"count": 0, "error": str(e)}

    def archive_project(self, project_id: int, user_id: int) -> dict:
        """归档项目"""
        db = self._get_db()
        if not db:
            return {"success": False, "message": "数据库不可用"}

        try:
            project = db.fetch_one(
                "SELECT * FROM sourcing_projects WHERE id = %s AND user_id = %s",
                (project_id, user_id),
            )
            if not project:
                return {"success": False, "message": "项目不存在"}

            # 标记为已归档
            db.execute(
                "UPDATE sourcing_projects SET status = 'archived', updated_at = NOW() WHERE id = %s",
                (project_id,),
            )

            logger.info(f"[Cleanup] 项目已归档: project_id={project_id}")
            return {"success": True, "message": "项目已归档"}

        except Exception as e:
            logger.error(f"[Cleanup] 归档项目失败: {e}")
            return {"success": False, "message": str(e)}

    def get_storage_stats(self) -> dict:
        """获取存储统计信息"""
        db = self._get_db()
        stats = {"tables": {}}

        if db:
            tables = [
                "analysis_tasks", "audit_logs", "notifications",
                "sourcing_projects", "project_products", "team_invitations",
            ]
            for table in tables:
                try:
                    row = db.fetch_one(f"SELECT COUNT(*) AS cnt FROM {table}", ())
                    stats["tables"][table] = row["cnt"] if row else 0
                except Exception:
                    stats["tables"][table] = -1

        # 磁盘使用
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        if os.path.exists(data_dir):
            total_size = 0
            for root, dirs, files in os.walk(data_dir):
                for f in files:
                    total_size += os.path.getsize(os.path.join(root, f))
            stats["disk_usage_mb"] = round(total_size / (1024 * 1024), 2)
        else:
            stats["disk_usage_mb"] = 0

        return stats

    def _archive_tasks(self, cutoff):
        """归档任务数据到文件"""
        if not CleanupPolicy.ARCHIVE_ENABLED:
            return

        archive_dir = CleanupPolicy.ARCHIVE_DIR
        os.makedirs(archive_dir, exist_ok=True)

        db = self._get_db()
        if not db:
            return

        try:
            rows = db.fetch_all(
                "SELECT * FROM analysis_tasks WHERE status IN ('completed','failed') AND created_at < %s",
                (cutoff,),
            )
            if rows:
                archive_file = os.path.join(
                    archive_dir,
                    f"tasks_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                )
                with open(archive_file, "w", encoding="utf-8") as f:
                    json.dump(
                        [dict(r) for r in rows], f,
                        ensure_ascii=False, indent=2, default=str,
                    )
                logger.info(f"[Cleanup] 已归档 {len(rows)} 条任务到 {archive_file}")
        except Exception as e:
            logger.warning(f"[Cleanup] 归档失败: {e}")


# 全局实例
cleaner = DataCleaner()
