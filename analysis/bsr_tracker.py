"""
BSR 历史追踪器 - Step 4 增强模块
追踪产品 BSR 排名、价格、评论数的历史变化，提供趋势分析和季节性检测。
"""

import math
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger


class BSRTracker:
    """
    BSR 历史追踪器
    - 记录每日 BSR、价格、评论数快照
    - 生成趋势图表数据（30/60/90 天）
    - 检测异常波动和季节性模式
    - 预测未来 BSR 走势
    """

    # BSR 波动告警阈值
    DEFAULT_ALERT_THRESHOLDS = {
        "bsr_spike_pct": 50,       # BSR 上升超过 50% 告警
        "bsr_drop_pct": 30,        # BSR 下降超过 30% 告警（利好）
        "price_change_pct": 15,    # 价格变化超过 15% 告警
        "review_spike_count": 50,  # 单日新增评论超过 50 告警（可能刷评）
    }

    def __init__(self, db=None, marketplace: str = "US"):
        """
        :param db: 数据库连接对象（需要 fetch_all / execute 方法）
        :param marketplace: 站点标识
        """
        self.db = db
        self.marketplace = marketplace

    # ------------------------------------------------------------------
    # 快照记录
    # ------------------------------------------------------------------
    def record_snapshot(self, asin: str, snapshot_data: dict) -> dict:
        """
        记录一条产品快照数据
        :param asin: 产品 ASIN
        :param snapshot_data: 包含 bsr_rank, price, rating, review_count 等
        :return: 保存结果
        """
        record = {
            "asin": asin,
            "marketplace": self.marketplace,
            "bsr_rank": snapshot_data.get("bsr_rank") or snapshot_data.get("bsr"),
            "price": snapshot_data.get("price") or snapshot_data.get("price_current"),
            "rating": snapshot_data.get("rating"),
            "review_count": snapshot_data.get("review_count"),
            "stock_status": snapshot_data.get("stock_status", "in_stock"),
            "buy_box_owner": snapshot_data.get("buy_box_owner", ""),
            "category": snapshot_data.get("category") or snapshot_data.get("bsr_category", ""),
            "recorded_at": datetime.now().isoformat(),
        }

        if self.db:
            try:
                self.db.execute(
                    """INSERT INTO bsr_history
                       (asin, marketplace, bsr_rank, price, rating, review_count,
                        stock_status, buy_box_owner, category, recorded_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
                    (
                        record["asin"], record["marketplace"],
                        record["bsr_rank"], record["price"],
                        record["rating"], record["review_count"],
                        record["stock_status"], record["buy_box_owner"],
                        record["category"],
                    ),
                )
                record["saved"] = True
            except Exception as e:
                logger.warning(f"BSR 快照保存失败: {e}")
                record["saved"] = False
        else:
            record["saved"] = False

        return record

    def batch_record(self, products: list[dict]) -> list[dict]:
        """
        批量记录多个产品的快照
        :param products: 产品列表
        :return: 保存结果列表
        """
        results = []
        for product in products:
            asin = product.get("asin") or product.get("product_id", "")
            if asin:
                result = self.record_snapshot(asin, product)
                results.append(result)
        return results

    # ------------------------------------------------------------------
    # 趋势数据查询
    # ------------------------------------------------------------------
    def get_bsr_history(self, asin: str, days: int = 30) -> dict:
        """
        获取 BSR 历史趋势数据
        :param asin: 产品 ASIN
        :param days: 回溯天数
        :return: 趋势数据（含日期序列、数值序列、统计摘要）
        """
        result = {
            "asin": asin,
            "days": days,
            "labels": [],
            "bsr_values": [],
            "summary": {},
        }

        if not self.db:
            return result

        try:
            since = datetime.now() - timedelta(days=days)
            rows = self.db.fetch_all(
                """SELECT DATE(recorded_at) AS day,
                          AVG(bsr_rank) AS avg_bsr,
                          MIN(bsr_rank) AS min_bsr,
                          MAX(bsr_rank) AS max_bsr
                   FROM bsr_history
                   WHERE asin = %s AND marketplace = %s
                     AND recorded_at >= %s AND bsr_rank IS NOT NULL
                   GROUP BY DATE(recorded_at)
                   ORDER BY day ASC""",
                (asin, self.marketplace, since),
            )

            if rows:
                for row in rows:
                    r = dict(row)
                    result["labels"].append(str(r["day"]))
                    result["bsr_values"].append(round(float(r["avg_bsr"])))

                all_bsr = result["bsr_values"]
                result["summary"] = {
                    "current": all_bsr[-1] if all_bsr else 0,
                    "avg": round(sum(all_bsr) / len(all_bsr)) if all_bsr else 0,
                    "min": min(all_bsr) if all_bsr else 0,
                    "max": max(all_bsr) if all_bsr else 0,
                    "trend": self._calculate_trend(all_bsr),
                    "volatility": self._calculate_volatility(all_bsr),
                    "data_points": len(all_bsr),
                }
        except Exception as e:
            logger.warning(f"BSR 历史查询失败: {e}")

        return result

    def get_price_history(self, asin: str, days: int = 30) -> dict:
        """
        获取价格历史趋势数据
        """
        result = {
            "asin": asin,
            "days": days,
            "labels": [],
            "price_values": [],
            "summary": {},
        }

        if not self.db:
            return result

        try:
            since = datetime.now() - timedelta(days=days)
            rows = self.db.fetch_all(
                """SELECT DATE(recorded_at) AS day,
                          AVG(price) AS avg_price,
                          MIN(price) AS min_price,
                          MAX(price) AS max_price
                   FROM bsr_history
                   WHERE asin = %s AND marketplace = %s
                     AND recorded_at >= %s AND price IS NOT NULL
                   GROUP BY DATE(recorded_at)
                   ORDER BY day ASC""",
                (asin, self.marketplace, since),
            )

            if rows:
                for row in rows:
                    r = dict(row)
                    result["labels"].append(str(r["day"]))
                    result["price_values"].append(round(float(r["avg_price"]), 2))

                all_prices = result["price_values"]
                result["summary"] = {
                    "current": all_prices[-1] if all_prices else 0,
                    "avg": round(sum(all_prices) / len(all_prices), 2) if all_prices else 0,
                    "min": min(all_prices) if all_prices else 0,
                    "max": max(all_prices) if all_prices else 0,
                    "trend": self._calculate_trend(all_prices),
                    "price_range": round(max(all_prices) - min(all_prices), 2) if all_prices else 0,
                }
        except Exception as e:
            logger.warning(f"价格历史查询失败: {e}")

        return result

    def get_review_history(self, asin: str, days: int = 30) -> dict:
        """
        获取评论数增长历史
        """
        result = {
            "asin": asin,
            "days": days,
            "labels": [],
            "review_values": [],
            "daily_growth": [],
            "summary": {},
        }

        if not self.db:
            return result

        try:
            since = datetime.now() - timedelta(days=days)
            rows = self.db.fetch_all(
                """SELECT DATE(recorded_at) AS day,
                          MAX(review_count) AS review_count
                   FROM bsr_history
                   WHERE asin = %s AND marketplace = %s
                     AND recorded_at >= %s AND review_count IS NOT NULL
                   GROUP BY DATE(recorded_at)
                   ORDER BY day ASC""",
                (asin, self.marketplace, since),
            )

            if rows:
                prev_count = None
                for row in rows:
                    r = dict(row)
                    count = int(r["review_count"])
                    result["labels"].append(str(r["day"]))
                    result["review_values"].append(count)
                    if prev_count is not None:
                        result["daily_growth"].append(max(0, count - prev_count))
                    else:
                        result["daily_growth"].append(0)
                    prev_count = count

                growth_values = result["daily_growth"]
                total_growth = sum(growth_values)
                result["summary"] = {
                    "current_total": result["review_values"][-1] if result["review_values"] else 0,
                    "total_growth": total_growth,
                    "avg_daily_growth": round(total_growth / max(len(growth_values), 1), 1),
                    "max_daily_growth": max(growth_values) if growth_values else 0,
                    "growth_trend": self._calculate_trend(result["review_values"]),
                }
        except Exception as e:
            logger.warning(f"评论历史查询失败: {e}")

        return result

    # ------------------------------------------------------------------
    # 综合趋势仪表板数据
    # ------------------------------------------------------------------
    def get_full_trend_dashboard(self, asin: str, days: int = 30) -> dict:
        """
        获取产品的完整趋势仪表板数据（BSR + 价格 + 评论）
        :param asin: 产品 ASIN
        :param days: 回溯天数
        :return: 综合趋势数据
        """
        bsr_data = self.get_bsr_history(asin, days)
        price_data = self.get_price_history(asin, days)
        review_data = self.get_review_history(asin, days)

        # 异常检测
        alerts = self.detect_anomalies(asin, days)

        # 季节性分析（需要至少 90 天数据）
        seasonality = {}
        if days >= 90:
            seasonality = self.analyze_seasonality(asin)

        return {
            "asin": asin,
            "marketplace": self.marketplace,
            "period_days": days,
            "bsr": bsr_data,
            "price": price_data,
            "reviews": review_data,
            "alerts": alerts,
            "seasonality": seasonality,
            "generated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # 异常检测
    # ------------------------------------------------------------------
    def detect_anomalies(self, asin: str, days: int = 30,
                         thresholds: dict = None) -> list[dict]:
        """
        检测 BSR、价格、评论的异常波动
        :param asin: 产品 ASIN
        :param days: 回溯天数
        :param thresholds: 告警阈值
        :return: 异常告警列表
        """
        thresholds = thresholds or self.DEFAULT_ALERT_THRESHOLDS
        alerts = []

        if not self.db:
            return alerts

        try:
            since = datetime.now() - timedelta(days=days)
            rows = self.db.fetch_all(
                """SELECT DATE(recorded_at) AS day,
                          AVG(bsr_rank) AS bsr, AVG(price) AS price,
                          MAX(review_count) AS reviews
                   FROM bsr_history
                   WHERE asin = %s AND marketplace = %s AND recorded_at >= %s
                   GROUP BY DATE(recorded_at)
                   ORDER BY day ASC""",
                (asin, self.marketplace, since),
            )

            if not rows or len(rows) < 2:
                return alerts

            data = [dict(r) for r in rows]

            for i in range(1, len(data)):
                curr = data[i]
                prev = data[i - 1]

                # BSR 异常
                if curr.get("bsr") and prev.get("bsr") and float(prev["bsr"]) > 0:
                    bsr_change_pct = (float(curr["bsr"]) - float(prev["bsr"])) / float(prev["bsr"]) * 100
                    if bsr_change_pct > thresholds["bsr_spike_pct"]:
                        alerts.append({
                            "type": "bsr_spike",
                            "severity": "warning",
                            "date": str(curr["day"]),
                            "message": f"BSR 急升 {bsr_change_pct:.0f}%: {int(float(prev['bsr']))} → {int(float(curr['bsr']))}",
                            "old_value": int(float(prev["bsr"])),
                            "new_value": int(float(curr["bsr"])),
                            "change_pct": round(bsr_change_pct, 1),
                        })
                    elif bsr_change_pct < -thresholds["bsr_drop_pct"]:
                        alerts.append({
                            "type": "bsr_improvement",
                            "severity": "info",
                            "date": str(curr["day"]),
                            "message": f"BSR 大幅改善 {abs(bsr_change_pct):.0f}%: {int(float(prev['bsr']))} → {int(float(curr['bsr']))}",
                            "old_value": int(float(prev["bsr"])),
                            "new_value": int(float(curr["bsr"])),
                            "change_pct": round(bsr_change_pct, 1),
                        })

                # 价格异常
                if curr.get("price") and prev.get("price") and float(prev["price"]) > 0:
                    price_change_pct = (float(curr["price"]) - float(prev["price"])) / float(prev["price"]) * 100
                    if abs(price_change_pct) > thresholds["price_change_pct"]:
                        alerts.append({
                            "type": "price_change",
                            "severity": "warning" if price_change_pct < 0 else "info",
                            "date": str(curr["day"]),
                            "message": f"价格{'下降' if price_change_pct < 0 else '上涨'} {abs(price_change_pct):.1f}%: ${float(prev['price']):.2f} → ${float(curr['price']):.2f}",
                            "old_value": round(float(prev["price"]), 2),
                            "new_value": round(float(curr["price"]), 2),
                            "change_pct": round(price_change_pct, 1),
                        })

                # 评论异常增长
                if curr.get("reviews") and prev.get("reviews"):
                    review_growth = int(curr["reviews"]) - int(prev["reviews"])
                    if review_growth > thresholds["review_spike_count"]:
                        alerts.append({
                            "type": "review_spike",
                            "severity": "high",
                            "date": str(curr["day"]),
                            "message": f"评论异常增长 +{review_growth} 条（可能存在刷评）",
                            "old_value": int(prev["reviews"]),
                            "new_value": int(curr["reviews"]),
                            "growth": review_growth,
                        })

        except Exception as e:
            logger.warning(f"异常检测失败: {e}")

        return alerts

    # ------------------------------------------------------------------
    # 季节性分析
    # ------------------------------------------------------------------
    def analyze_seasonality(self, asin: str, years: int = 1) -> dict:
        """
        分析 BSR 的季节性模式
        :param asin: 产品 ASIN
        :param years: 回溯年数
        :return: 季节性分析结果
        """
        result = {
            "has_seasonality": False,
            "peak_months": [],
            "low_months": [],
            "monthly_avg_bsr": {},
            "recommendation": "",
        }

        if not self.db:
            return result

        try:
            since = datetime.now() - timedelta(days=365 * years)
            rows = self.db.fetch_all(
                """SELECT MONTH(recorded_at) AS month,
                          AVG(bsr_rank) AS avg_bsr,
                          COUNT(*) AS data_points
                   FROM bsr_history
                   WHERE asin = %s AND marketplace = %s
                     AND recorded_at >= %s AND bsr_rank IS NOT NULL
                   GROUP BY MONTH(recorded_at)
                   ORDER BY month ASC""",
                (asin, self.marketplace, since),
            )

            if not rows or len(rows) < 3:
                result["recommendation"] = "数据不足，无法进行季节性分析（至少需要 3 个月数据）"
                return result

            month_names = [
                "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
            ]

            monthly_data = {}
            for row in rows:
                r = dict(row)
                month = int(r["month"])
                avg_bsr = float(r["avg_bsr"])
                monthly_data[month] = avg_bsr
                result["monthly_avg_bsr"][month_names[month]] = round(avg_bsr)

            if not monthly_data:
                return result

            overall_avg = sum(monthly_data.values()) / len(monthly_data)
            std_dev = math.sqrt(
                sum((v - overall_avg) ** 2 for v in monthly_data.values()) / len(monthly_data)
            ) if len(monthly_data) > 1 else 0

            # 季节性判断：标准差超过均值的 20% 认为有季节性
            cv = std_dev / overall_avg if overall_avg > 0 else 0
            result["has_seasonality"] = cv > 0.2

            # 找出旺季（BSR 低 = 销量好）和淡季
            sorted_months = sorted(monthly_data.items(), key=lambda x: x[1])
            result["peak_months"] = [
                month_names[m] for m, bsr in sorted_months[:3]
                if bsr < overall_avg
            ]
            result["low_months"] = [
                month_names[m] for m, bsr in sorted_months[-3:]
                if bsr > overall_avg
            ]

            if result["has_seasonality"]:
                peak_str = ", ".join(result["peak_months"]) if result["peak_months"] else "无明显旺季"
                low_str = ", ".join(result["low_months"]) if result["low_months"] else "无明显淡季"
                result["recommendation"] = (
                    f"该产品存在明显季节性波动（变异系数 {cv:.1%}）。"
                    f"旺季: {peak_str}，淡季: {low_str}。"
                    f"建议在旺季前 1-2 个月备货，淡季减少库存。"
                )
            else:
                result["recommendation"] = (
                    f"该产品无明显季节性波动（变异系数 {cv:.1%}），全年销量相对稳定。"
                )

        except Exception as e:
            logger.warning(f"季节性分析失败: {e}")

        return result

    # ------------------------------------------------------------------
    # BSR 排名预测
    # ------------------------------------------------------------------
    def predict_bsr_trend(self, asin: str, forecast_days: int = 7) -> dict:
        """
        基于线性回归预测未来 BSR 走势
        :param asin: 产品 ASIN
        :param forecast_days: 预测天数
        :return: 预测结果
        """
        result = {
            "asin": asin,
            "forecast_days": forecast_days,
            "predicted_values": [],
            "predicted_labels": [],
            "trend_direction": "stable",
            "confidence": "low",
        }

        # 获取最近 30 天数据用于预测
        history = self.get_bsr_history(asin, days=30)
        values = history.get("bsr_values", [])

        if len(values) < 7:
            result["message"] = "数据不足，至少需要 7 天历史数据"
            return result

        # 简单线性回归
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
            intercept = y_mean
        else:
            slope = numerator / denominator
            intercept = y_mean - slope * x_mean

        # 计算 R² 置信度
        ss_res = sum((values[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 预测未来值
        today = datetime.now()
        for d in range(1, forecast_days + 1):
            future_x = n + d - 1
            predicted = max(1, round(slope * future_x + intercept))
            result["predicted_values"].append(predicted)
            result["predicted_labels"].append(
                (today + timedelta(days=d)).strftime("%Y-%m-%d")
            )

        # 趋势方向
        if slope > 0.5:
            result["trend_direction"] = "declining"  # BSR 上升 = 销量下降
        elif slope < -0.5:
            result["trend_direction"] = "improving"  # BSR 下降 = 销量上升
        else:
            result["trend_direction"] = "stable"

        # 置信度
        if r_squared > 0.7:
            result["confidence"] = "high"
        elif r_squared > 0.4:
            result["confidence"] = "medium"
        else:
            result["confidence"] = "low"

        result["r_squared"] = round(r_squared, 3)
        result["slope"] = round(slope, 2)

        return result

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    @staticmethod
    def _calculate_trend(values: list) -> str:
        """计算趋势方向"""
        if not values or len(values) < 2:
            return "insufficient_data"
        first_half = sum(values[:len(values) // 2]) / max(len(values) // 2, 1)
        second_half = sum(values[len(values) // 2:]) / max(len(values) - len(values) // 2, 1)
        if first_half == 0:
            return "stable"
        change_pct = (second_half - first_half) / first_half * 100
        if change_pct > 10:
            return "increasing"
        elif change_pct < -10:
            return "decreasing"
        return "stable"

    @staticmethod
    def _calculate_volatility(values: list) -> str:
        """计算波动性"""
        if not values or len(values) < 2:
            return "unknown"
        mean = sum(values) / len(values)
        if mean == 0:
            return "low"
        std_dev = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
        cv = std_dev / mean
        if cv > 0.5:
            return "high"
        elif cv > 0.2:
            return "medium"
        return "low"
