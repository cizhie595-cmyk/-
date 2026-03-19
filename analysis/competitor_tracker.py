"""
竞品监控追踪器 (Competitor Tracker)

Step 2 扩展模块 - 追踪竞品价格/BSR/评论变化，支持定时监控和历史趋势分析

功能:
1. 添加竞品 ASIN 到监控列表
2. 定期抓取竞品数据快照（价格、BSR、评论数、评分、库存状态）
3. 变化检测与告警（价格降幅 > 10%、BSR 大幅波动、新增差评等）
4. 历史趋势分析（30/60/90 天趋势图数据）
5. 竞品对比矩阵生成
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional

from utils.logger import get_logger

logger = get_logger()


class CompetitorTracker:
    """
    竞品监控追踪器

    支持追踪多个竞品 ASIN 的关键指标变化，
    生成对比矩阵和趋势分析数据。
    """

    # 告警阈值默认配置
    DEFAULT_ALERT_THRESHOLDS = {
        "price_drop_pct": 10.0,       # 价格降幅超过 10% 触发告警
        "price_rise_pct": 15.0,       # 价格涨幅超过 15% 触发告警
        "bsr_improve_pct": 30.0,      # BSR 排名提升超过 30% 触发告警
        "bsr_decline_pct": 50.0,      # BSR 排名下降超过 50% 触发告警
        "review_spike_count": 20,     # 单日新增评论超过 20 条触发告警
        "rating_drop_threshold": 0.3, # 评分下降超过 0.3 触发告警
    }

    def __init__(self, db=None, http_client=None, marketplace: str = "US"):
        """
        :param db: 数据库连接实例
        :param http_client: HTTP 客户端（用于抓取数据）
        :param marketplace: 市场站点
        """
        self.db = db
        self.http_client = http_client
        self.marketplace = marketplace

    # ================================================================
    # 监控列表管理
    # ================================================================

    def add_competitor(self, user_id: int, project_id: int, asin: str,
                       label: str = "", notes: str = "") -> dict:
        """
        添加竞品到监控列表

        :param user_id: 用户 ID
        :param project_id: 所属项目 ID
        :param asin: 竞品 ASIN
        :param label: 自定义标签（如 "主竞品"、"价格标杆"）
        :param notes: 备注
        :return: 新建的监控记录
        """
        now = datetime.now()
        record = {
            "user_id": user_id,
            "project_id": project_id,
            "asin": asin,
            "label": label,
            "notes": notes,
            "status": "active",
            "created_at": now.isoformat(),
            "last_snapshot_at": None,
        }

        if self.db:
            try:
                self.db.execute(
                    """INSERT INTO competitor_monitors
                       (user_id, project_id, asin, label, notes, status, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (user_id, project_id, asin, label, notes, "active", now),
                )
                row = self.db.fetch_one(
                    "SELECT id FROM competitor_monitors WHERE user_id=%s AND asin=%s ORDER BY id DESC LIMIT 1",
                    (user_id, asin),
                )
                if row:
                    record["id"] = row["id"]
            except Exception as e:
                logger.error(f"添加竞品监控失败: {e}")

        logger.info(f"添加竞品监控: {asin} (label={label})")
        return record

    def remove_competitor(self, user_id: int, monitor_id: int) -> bool:
        """移除竞品监控"""
        if self.db:
            try:
                self.db.execute(
                    "UPDATE competitor_monitors SET status='removed' WHERE id=%s AND user_id=%s",
                    (monitor_id, user_id),
                )
                return True
            except Exception as e:
                logger.error(f"移除竞品监控失败: {e}")
        return False

    def list_competitors(self, user_id: int, project_id: int = None) -> list[dict]:
        """获取用户的竞品监控列表"""
        if not self.db:
            return []

        try:
            if project_id:
                rows = self.db.fetch_all(
                    """SELECT id, asin, label, notes, status, last_snapshot_at, created_at
                       FROM competitor_monitors
                       WHERE user_id=%s AND project_id=%s AND status='active'
                       ORDER BY created_at DESC""",
                    (user_id, project_id),
                )
            else:
                rows = self.db.fetch_all(
                    """SELECT id, project_id, asin, label, notes, status, last_snapshot_at, created_at
                       FROM competitor_monitors
                       WHERE user_id=%s AND status='active'
                       ORDER BY created_at DESC""",
                    (user_id,),
                )
            return [dict(r) for r in rows] if rows else []
        except Exception as e:
            logger.error(f"获取竞品列表失败: {e}")
            return []

    # ================================================================
    # 数据快照
    # ================================================================

    def take_snapshot(self, asin: str) -> dict:
        """
        抓取竞品当前数据快照

        :param asin: 竞品 ASIN
        :return: 快照数据字典
        """
        snapshot = {
            "asin": asin,
            "timestamp": datetime.now().isoformat(),
            "marketplace": self.marketplace,
            "price": None,
            "bsr_rank": None,
            "bsr_category": None,
            "rating": None,
            "review_count": None,
            "seller_count": None,
            "fulfillment": None,
            "stock_status": "in_stock",
            "buy_box_seller": None,
        }

        # 使用详情页爬虫抓取数据
        try:
            from scrapers.amazon.detail_crawler import AmazonDetailCrawler

            crawler = AmazonDetailCrawler(
                http_client=self.http_client,
                marketplace=self.marketplace,
            )
            try:
                detail = crawler.crawl_detail(asin)
                if detail:
                    snapshot["price"] = detail.get("price") or detail.get("price_current")
                    snapshot["bsr_rank"] = detail.get("bsr_rank") or detail.get("bsr")
                    snapshot["bsr_category"] = detail.get("bsr_category") or detail.get("category")
                    snapshot["rating"] = detail.get("rating")
                    snapshot["review_count"] = detail.get("review_count") or detail.get("reviews")
                    snapshot["seller_count"] = detail.get("seller_count")
                    snapshot["fulfillment"] = detail.get("fulfillment_type") or detail.get("fulfillment")
                    snapshot["buy_box_seller"] = detail.get("buy_box_seller")

                    # 判断库存状态
                    if detail.get("availability"):
                        avail = detail["availability"].lower()
                        if "out of stock" in avail or "unavailable" in avail:
                            snapshot["stock_status"] = "out_of_stock"
                        elif "limited" in avail or "only" in avail:
                            snapshot["stock_status"] = "low_stock"
            finally:
                crawler.close()
        except Exception as e:
            logger.warning(f"快照抓取失败 {asin}: {e}")

        return snapshot

    def save_snapshot(self, user_id: int, monitor_id: int, snapshot: dict) -> bool:
        """保存快照到数据库"""
        if not self.db:
            return False

        try:
            self.db.execute(
                """INSERT INTO competitor_snapshots
                   (monitor_id, asin, price, bsr_rank, bsr_category, rating,
                    review_count, seller_count, fulfillment, stock_status,
                    buy_box_seller, snapshot_data, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    monitor_id,
                    snapshot["asin"],
                    snapshot.get("price"),
                    snapshot.get("bsr_rank"),
                    snapshot.get("bsr_category"),
                    snapshot.get("rating"),
                    snapshot.get("review_count"),
                    snapshot.get("seller_count"),
                    snapshot.get("fulfillment"),
                    snapshot.get("stock_status", "in_stock"),
                    snapshot.get("buy_box_seller"),
                    json.dumps(snapshot, default=str),
                    datetime.now(),
                ),
            )
            # 更新最后快照时间
            self.db.execute(
                "UPDATE competitor_monitors SET last_snapshot_at=NOW() WHERE id=%s",
                (monitor_id,),
            )
            return True
        except Exception as e:
            logger.error(f"保存快照失败: {e}")
            return False

    def batch_snapshot(self, user_id: int, project_id: int = None) -> list[dict]:
        """
        批量抓取所有监控竞品的快照

        :return: 所有快照结果列表
        """
        monitors = self.list_competitors(user_id, project_id)
        results = []

        for monitor in monitors:
            asin = monitor.get("asin")
            if not asin:
                continue

            snapshot = self.take_snapshot(asin)
            saved = self.save_snapshot(user_id, monitor.get("id"), snapshot)

            results.append({
                "monitor_id": monitor.get("id"),
                "asin": asin,
                "label": monitor.get("label", ""),
                "snapshot": snapshot,
                "saved": saved,
            })

        logger.info(f"批量快照完成: {len(results)} 个竞品")
        return results

    # ================================================================
    # 变化检测与告警
    # ================================================================

    def detect_changes(self, monitor_id: int,
                       thresholds: dict = None) -> list[dict]:
        """
        检测竞品数据变化，生成告警

        :param monitor_id: 监控记录 ID
        :param thresholds: 告警阈值配置
        :return: 告警列表
        """
        thresholds = thresholds or self.DEFAULT_ALERT_THRESHOLDS
        alerts = []

        if not self.db:
            return alerts

        try:
            # 获取最近两次快照
            rows = self.db.fetch_all(
                """SELECT price, bsr_rank, rating, review_count, stock_status, created_at
                   FROM competitor_snapshots
                   WHERE monitor_id = %s
                   ORDER BY created_at DESC LIMIT 2""",
                (monitor_id,),
            )

            if not rows or len(rows) < 2:
                return alerts

            current = dict(rows[0])
            previous = dict(rows[1])

            # 价格变化检测
            if current.get("price") and previous.get("price"):
                price_change_pct = (
                    (current["price"] - previous["price"]) / previous["price"] * 100
                )
                if price_change_pct < -thresholds["price_drop_pct"]:
                    alerts.append({
                        "type": "price_drop",
                        "severity": "high",
                        "message": f"价格下降 {abs(price_change_pct):.1f}%: "
                                   f"${previous['price']:.2f} → ${current['price']:.2f}",
                        "old_value": previous["price"],
                        "new_value": current["price"],
                        "change_pct": price_change_pct,
                    })
                elif price_change_pct > thresholds["price_rise_pct"]:
                    alerts.append({
                        "type": "price_rise",
                        "severity": "medium",
                        "message": f"价格上涨 {price_change_pct:.1f}%: "
                                   f"${previous['price']:.2f} → ${current['price']:.2f}",
                        "old_value": previous["price"],
                        "new_value": current["price"],
                        "change_pct": price_change_pct,
                    })

            # BSR 变化检测
            if current.get("bsr_rank") and previous.get("bsr_rank"):
                bsr_change_pct = (
                    (previous["bsr_rank"] - current["bsr_rank"]) / previous["bsr_rank"] * 100
                )
                if bsr_change_pct > thresholds["bsr_improve_pct"]:
                    alerts.append({
                        "type": "bsr_improve",
                        "severity": "high",
                        "message": f"BSR 排名提升 {bsr_change_pct:.1f}%: "
                                   f"#{previous['bsr_rank']} → #{current['bsr_rank']}",
                        "old_value": previous["bsr_rank"],
                        "new_value": current["bsr_rank"],
                        "change_pct": bsr_change_pct,
                    })
                elif bsr_change_pct < -thresholds["bsr_decline_pct"]:
                    alerts.append({
                        "type": "bsr_decline",
                        "severity": "low",
                        "message": f"BSR 排名下降 {abs(bsr_change_pct):.1f}%: "
                                   f"#{previous['bsr_rank']} → #{current['bsr_rank']}",
                        "old_value": previous["bsr_rank"],
                        "new_value": current["bsr_rank"],
                        "change_pct": bsr_change_pct,
                    })

            # 评论数变化检测
            if current.get("review_count") and previous.get("review_count"):
                review_diff = current["review_count"] - previous["review_count"]
                if review_diff > thresholds["review_spike_count"]:
                    alerts.append({
                        "type": "review_spike",
                        "severity": "medium",
                        "message": f"评论激增 +{review_diff} 条: "
                                   f"{previous['review_count']} → {current['review_count']}",
                        "old_value": previous["review_count"],
                        "new_value": current["review_count"],
                        "change_count": review_diff,
                    })

            # 评分变化检测
            if current.get("rating") and previous.get("rating"):
                rating_diff = current["rating"] - previous["rating"]
                if rating_diff < -thresholds["rating_drop_threshold"]:
                    alerts.append({
                        "type": "rating_drop",
                        "severity": "medium",
                        "message": f"评分下降 {abs(rating_diff):.1f}: "
                                   f"{previous['rating']:.1f} → {current['rating']:.1f}",
                        "old_value": previous["rating"],
                        "new_value": current["rating"],
                        "change_value": rating_diff,
                    })

            # 库存状态变化
            if current.get("stock_status") != previous.get("stock_status"):
                alerts.append({
                    "type": "stock_change",
                    "severity": "high" if current["stock_status"] == "out_of_stock" else "medium",
                    "message": f"库存状态变化: {previous.get('stock_status')} → {current['stock_status']}",
                    "old_value": previous.get("stock_status"),
                    "new_value": current["stock_status"],
                })

        except Exception as e:
            logger.error(f"变化检测失败: {e}")

        return alerts

    # ================================================================
    # 历史趋势分析
    # ================================================================

    def get_trend_data(self, monitor_id: int, days: int = 30,
                       metric: str = "price") -> dict:
        """
        获取竞品指标的历史趋势数据

        :param monitor_id: 监控记录 ID
        :param days: 回溯天数
        :param metric: 指标名称 (price/bsr_rank/rating/review_count)
        :return: 趋势数据（含日期序列和数值序列）
        """
        valid_metrics = {"price", "bsr_rank", "rating", "review_count"}
        if metric not in valid_metrics:
            metric = "price"

        result = {
            "monitor_id": monitor_id,
            "metric": metric,
            "days": days,
            "labels": [],
            "values": [],
            "summary": {},
        }

        if not self.db:
            return result

        try:
            since = datetime.now() - timedelta(days=days)
            rows = self.db.fetch_all(
                f"""SELECT DATE(created_at) AS day, AVG({metric}) AS avg_val,
                           MIN({metric}) AS min_val, MAX({metric}) AS max_val
                    FROM competitor_snapshots
                    WHERE monitor_id = %s AND created_at >= %s AND {metric} IS NOT NULL
                    GROUP BY DATE(created_at)
                    ORDER BY day ASC""",
                (monitor_id, since),
            )

            if rows:
                values = []
                for row in rows:
                    r = dict(row)
                    result["labels"].append(str(r["day"]))
                    val = float(r["avg_val"]) if r["avg_val"] is not None else 0
                    result["values"].append(round(val, 2))
                    values.append(val)

                if values:
                    result["summary"] = {
                        "min": round(min(values), 2),
                        "max": round(max(values), 2),
                        "avg": round(sum(values) / len(values), 2),
                        "current": round(values[-1], 2),
                        "change": round(values[-1] - values[0], 2) if len(values) > 1 else 0,
                        "change_pct": round(
                            (values[-1] - values[0]) / values[0] * 100, 1
                        ) if len(values) > 1 and values[0] != 0 else 0,
                        "data_points": len(values),
                    }

        except Exception as e:
            logger.error(f"获取趋势数据失败: {e}")

        return result

    # ================================================================
    # 竞品对比矩阵
    # ================================================================

    def generate_comparison_matrix(self, user_id: int,
                                    project_id: int) -> dict:
        """
        生成竞品对比矩阵

        将所有监控竞品的最新数据汇总为对比表格，
        包含价格、BSR、评分、评论数、库存状态等维度。

        :return: 对比矩阵数据
        """
        monitors = self.list_competitors(user_id, project_id)
        if not monitors:
            return {"competitors": [], "dimensions": []}

        matrix = {
            "project_id": project_id,
            "generated_at": datetime.now().isoformat(),
            "competitors": [],
            "dimensions": [
                "price", "bsr_rank", "rating", "review_count",
                "seller_count", "fulfillment", "stock_status",
            ],
            "insights": [],
        }

        for monitor in monitors:
            monitor_id = monitor.get("id")
            asin = monitor.get("asin")

            # 获取最新快照
            latest = self._get_latest_snapshot(monitor_id)
            if not latest:
                continue

            # 获取 7 天变化
            trend_7d = self._get_short_trend(monitor_id, days=7)

            competitor = {
                "monitor_id": monitor_id,
                "asin": asin,
                "label": monitor.get("label", ""),
                "current": latest,
                "trend_7d": trend_7d,
            }
            matrix["competitors"].append(competitor)

        # 生成洞察
        matrix["insights"] = self._generate_insights(matrix["competitors"])

        return matrix

    def _get_latest_snapshot(self, monitor_id: int) -> Optional[dict]:
        """获取最新快照"""
        if not self.db:
            return None

        try:
            row = self.db.fetch_one(
                """SELECT price, bsr_rank, bsr_category, rating, review_count,
                          seller_count, fulfillment, stock_status, buy_box_seller,
                          created_at
                   FROM competitor_snapshots
                   WHERE monitor_id = %s
                   ORDER BY created_at DESC LIMIT 1""",
                (monitor_id,),
            )
            return dict(row) if row else None
        except Exception:
            return None

    def _get_short_trend(self, monitor_id: int, days: int = 7) -> dict:
        """获取短期趋势摘要"""
        if not self.db:
            return {}

        try:
            since = datetime.now() - timedelta(days=days)
            rows = self.db.fetch_all(
                """SELECT price, bsr_rank, rating, review_count, created_at
                   FROM competitor_snapshots
                   WHERE monitor_id = %s AND created_at >= %s
                   ORDER BY created_at ASC""",
                (monitor_id, since),
            )

            if not rows or len(rows) < 2:
                return {}

            first = dict(rows[0])
            last = dict(rows[-1])

            trend = {}
            for metric in ["price", "bsr_rank", "rating", "review_count"]:
                old_val = first.get(metric)
                new_val = last.get(metric)
                if old_val and new_val and old_val != 0:
                    change_pct = (new_val - old_val) / old_val * 100
                    trend[metric] = {
                        "old": old_val,
                        "new": new_val,
                        "change_pct": round(change_pct, 1),
                        "direction": "up" if change_pct > 0 else "down" if change_pct < 0 else "flat",
                    }

            return trend
        except Exception:
            return {}

    def _generate_insights(self, competitors: list[dict]) -> list[str]:
        """根据对比数据生成洞察"""
        insights = []

        if not competitors:
            return insights

        # 找出价格最低/最高的竞品
        priced = [
            c for c in competitors
            if c.get("current", {}).get("price")
        ]
        if priced:
            cheapest = min(priced, key=lambda c: c["current"]["price"])
            most_expensive = max(priced, key=lambda c: c["current"]["price"])
            price_range = most_expensive["current"]["price"] - cheapest["current"]["price"]
            insights.append(
                f"价格区间 ${cheapest['current']['price']:.2f} - "
                f"${most_expensive['current']['price']:.2f} "
                f"(差距 ${price_range:.2f})"
            )

        # 找出 BSR 最好的竞品
        bsr_ranked = [
            c for c in competitors
            if c.get("current", {}).get("bsr_rank")
        ]
        if bsr_ranked:
            best_bsr = min(bsr_ranked, key=lambda c: c["current"]["bsr_rank"])
            insights.append(
                f"BSR 最佳: {best_bsr['asin']} "
                f"(#{best_bsr['current']['bsr_rank']:,})"
            )

        # 找出评分最高的竞品
        rated = [
            c for c in competitors
            if c.get("current", {}).get("rating")
        ]
        if rated:
            best_rated = max(rated, key=lambda c: c["current"]["rating"])
            insights.append(
                f"评分最高: {best_rated['asin']} "
                f"({best_rated['current']['rating']:.1f}★)"
            )

        # 检测缺货竞品
        out_of_stock = [
            c for c in competitors
            if c.get("current", {}).get("stock_status") == "out_of_stock"
        ]
        if out_of_stock:
            asins = ", ".join(c["asin"] for c in out_of_stock)
            insights.append(f"当前缺货: {asins} — 可能是入场机会")

        # 7 天价格下降最多的竞品
        price_drops = []
        for c in competitors:
            trend = c.get("trend_7d", {}).get("price", {})
            if trend.get("direction") == "down":
                price_drops.append((c["asin"], trend["change_pct"]))
        if price_drops:
            price_drops.sort(key=lambda x: x[1])
            worst = price_drops[0]
            insights.append(
                f"7天价格降幅最大: {worst[0]} ({worst[1]:.1f}%) — 注意价格战风险"
            )

        return insights
