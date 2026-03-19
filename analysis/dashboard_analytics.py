"""
数据看板分析引擎 - Step 10 增强模块
为 Dashboard 提供实时统计、趋势图表、选品漏斗分析等增强数据。
"""

import math
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger


class DashboardAnalytics:
    """
    数据看板分析引擎
    - 选品漏斗分析（搜索 → 筛选 → 分析 → 利润计算 → 最终选品）
    - 项目进度追踪
    - 关键指标 KPI 卡片数据
    - 趋势图表数据
    - 活动日志聚合
    """

    def __init__(self, db=None):
        self.db = db

    # ------------------------------------------------------------------
    # 选品漏斗分析
    # ------------------------------------------------------------------
    def get_selection_funnel(self, project_id: int = None) -> dict:
        """
        获取选品漏斗数据
        :param project_id: 项目 ID（可选，不传则统计全部）
        :return: 漏斗数据
        """
        funnel = {
            "stages": [
                {"name": "搜索发现", "key": "searched", "count": 0, "icon": "search"},
                {"name": "初步筛选", "key": "filtered", "count": 0, "icon": "filter"},
                {"name": "详情分析", "key": "analyzed", "count": 0, "icon": "chart-bar"},
                {"name": "利润计算", "key": "profit_calculated", "count": 0, "icon": "calculator"},
                {"name": "最终选品", "key": "selected", "count": 0, "icon": "check-circle"},
            ],
            "conversion_rates": [],
        }

        if not self.db:
            return funnel

        try:
            where_clause = "WHERE project_id = %s" if project_id else ""
            params = (project_id,) if project_id else ()

            # 搜索发现数
            row = self.db.fetch_all(
                f"SELECT COUNT(*) AS cnt FROM project_products {where_clause}",
                params,
            )
            funnel["stages"][0]["count"] = int(row[0]["cnt"]) if row else 0

            # 初步筛选通过数
            row = self.db.fetch_all(
                f"""SELECT COUNT(*) AS cnt FROM project_products
                    {where_clause}{'AND' if where_clause else 'WHERE'}
                    status != 'filtered_out'""",
                params,
            )
            funnel["stages"][1]["count"] = int(row[0]["cnt"]) if row else 0

            # 详情分析完成数
            row = self.db.fetch_all(
                f"""SELECT COUNT(DISTINCT asin) AS cnt FROM analysis_tasks
                    WHERE status = 'completed'
                    {'AND project_id = %s' if project_id else ''}""",
                params if project_id else (),
            )
            funnel["stages"][2]["count"] = int(row[0]["cnt"]) if row else 0

            # 利润计算完成数
            row = self.db.fetch_all(
                f"""SELECT COUNT(*) AS cnt FROM profit_calculations
                    {'WHERE project_id = %s' if project_id else ''}""",
                params if project_id else (),
            )
            funnel["stages"][3]["count"] = int(row[0]["cnt"]) if row else 0

            # 最终选品数（利润率 > 15% 的产品）
            row = self.db.fetch_all(
                f"""SELECT COUNT(*) AS cnt FROM profit_calculations
                    WHERE profit_margin > 15
                    {'AND project_id = %s' if project_id else ''}""",
                params if project_id else (),
            )
            funnel["stages"][4]["count"] = int(row[0]["cnt"]) if row else 0

            # 计算转化率
            for i in range(1, len(funnel["stages"])):
                prev_count = funnel["stages"][i - 1]["count"]
                curr_count = funnel["stages"][i]["count"]
                rate = round(curr_count / max(prev_count, 1) * 100, 1)
                funnel["conversion_rates"].append({
                    "from": funnel["stages"][i - 1]["key"],
                    "to": funnel["stages"][i]["key"],
                    "rate": rate,
                })

        except Exception as e:
            logger.warning(f"漏斗数据查询失败: {e}")

        return funnel

    # ------------------------------------------------------------------
    # KPI 卡片数据
    # ------------------------------------------------------------------
    def get_kpi_cards(self) -> list[dict]:
        """
        获取 Dashboard KPI 卡片数据
        :return: KPI 卡片列表
        """
        cards = [
            {
                "title": "活跃项目",
                "key": "active_projects",
                "value": 0,
                "change": 0,
                "change_label": "vs 上周",
                "icon": "folder",
                "color": "primary",
            },
            {
                "title": "已分析产品",
                "key": "analyzed_products",
                "value": 0,
                "change": 0,
                "change_label": "vs 上周",
                "icon": "package",
                "color": "success",
            },
            {
                "title": "平均利润率",
                "key": "avg_profit_margin",
                "value": "0%",
                "change": 0,
                "change_label": "vs 上周",
                "icon": "trending-up",
                "color": "warning",
            },
            {
                "title": "选品成功率",
                "key": "selection_rate",
                "value": "0%",
                "change": 0,
                "change_label": "vs 上周",
                "icon": "target",
                "color": "info",
            },
        ]

        if not self.db:
            return cards

        try:
            now = datetime.now()
            week_ago = now - timedelta(days=7)
            two_weeks_ago = now - timedelta(days=14)

            # 活跃项目
            row = self.db.fetch_all(
                "SELECT COUNT(*) AS cnt FROM sourcing_projects WHERE status = 'active'"
            )
            cards[0]["value"] = int(row[0]["cnt"]) if row else 0

            row_prev = self.db.fetch_all(
                "SELECT COUNT(*) AS cnt FROM sourcing_projects WHERE status = 'active' AND created_at < %s",
                (week_ago,),
            )
            prev_val = int(row_prev[0]["cnt"]) if row_prev else 0
            cards[0]["change"] = cards[0]["value"] - prev_val

            # 已分析产品
            row = self.db.fetch_all(
                "SELECT COUNT(*) AS cnt FROM project_products"
            )
            total_products = int(row[0]["cnt"]) if row else 0
            cards[1]["value"] = total_products

            row_prev = self.db.fetch_all(
                "SELECT COUNT(*) AS cnt FROM project_products WHERE created_at < %s",
                (week_ago,),
            )
            prev_products = int(row_prev[0]["cnt"]) if row_prev else 0
            cards[1]["change"] = total_products - prev_products

            # 平均利润率
            row = self.db.fetch_all(
                "SELECT AVG(profit_margin) AS avg_margin FROM profit_calculations"
            )
            avg_margin = float(row[0]["avg_margin"]) if row and row[0]["avg_margin"] else 0
            cards[2]["value"] = f"{avg_margin:.1f}%"

            row_prev = self.db.fetch_all(
                "SELECT AVG(profit_margin) AS avg_margin FROM profit_calculations WHERE created_at < %s",
                (week_ago,),
            )
            prev_margin = float(row_prev[0]["avg_margin"]) if row_prev and row_prev[0]["avg_margin"] else 0
            cards[2]["change"] = round(avg_margin - prev_margin, 1)

            # 选品成功率
            row_profitable = self.db.fetch_all(
                "SELECT COUNT(*) AS cnt FROM profit_calculations WHERE profit_margin > 15"
            )
            profitable = int(row_profitable[0]["cnt"]) if row_profitable else 0
            row_total_calc = self.db.fetch_all(
                "SELECT COUNT(*) AS cnt FROM profit_calculations"
            )
            total_calc = int(row_total_calc[0]["cnt"]) if row_total_calc else 0
            rate = round(profitable / max(total_calc, 1) * 100, 1)
            cards[3]["value"] = f"{rate}%"

        except Exception as e:
            logger.warning(f"KPI 数据查询失败: {e}")

        return cards

    # ------------------------------------------------------------------
    # 趋势图表数据
    # ------------------------------------------------------------------
    def get_activity_trend(self, days: int = 30) -> dict:
        """
        获取最近 N 天的活动趋势
        :param days: 天数
        :return: 趋势图表数据
        """
        result = {
            "labels": [],
            "products_added": [],
            "analyses_completed": [],
            "profit_calculated": [],
        }

        if not self.db:
            # 生成空数据
            for i in range(days):
                day = (datetime.now() - timedelta(days=days - 1 - i)).strftime("%m/%d")
                result["labels"].append(day)
                result["products_added"].append(0)
                result["analyses_completed"].append(0)
                result["profit_calculated"].append(0)
            return result

        try:
            since = datetime.now() - timedelta(days=days)

            # 每日新增产品
            rows = self.db.fetch_all(
                """SELECT DATE(created_at) AS day, COUNT(*) AS cnt
                   FROM project_products
                   WHERE created_at >= %s
                   GROUP BY DATE(created_at)
                   ORDER BY day ASC""",
                (since,),
            )
            products_by_day = {str(dict(r)["day"]): int(dict(r)["cnt"]) for r in rows} if rows else {}

            # 每日完成分析
            rows = self.db.fetch_all(
                """SELECT DATE(updated_at) AS day, COUNT(*) AS cnt
                   FROM analysis_tasks
                   WHERE status = 'completed' AND updated_at >= %s
                   GROUP BY DATE(updated_at)
                   ORDER BY day ASC""",
                (since,),
            )
            analyses_by_day = {str(dict(r)["day"]): int(dict(r)["cnt"]) for r in rows} if rows else {}

            # 每日利润计算
            rows = self.db.fetch_all(
                """SELECT DATE(created_at) AS day, COUNT(*) AS cnt
                   FROM profit_calculations
                   WHERE created_at >= %s
                   GROUP BY DATE(created_at)
                   ORDER BY day ASC""",
                (since,),
            )
            profit_by_day = {str(dict(r)["day"]): int(dict(r)["cnt"]) for r in rows} if rows else {}

            # 填充每一天的数据
            for i in range(days):
                day = datetime.now() - timedelta(days=days - 1 - i)
                day_str = day.strftime("%Y-%m-%d")
                label = day.strftime("%m/%d")
                result["labels"].append(label)
                result["products_added"].append(products_by_day.get(day_str, 0))
                result["analyses_completed"].append(analyses_by_day.get(day_str, 0))
                result["profit_calculated"].append(profit_by_day.get(day_str, 0))

        except Exception as e:
            logger.warning(f"活动趋势查询失败: {e}")

        return result

    # ------------------------------------------------------------------
    # 项目进度概览
    # ------------------------------------------------------------------
    def get_project_progress(self) -> list[dict]:
        """
        获取所有项目的进度概览
        :return: 项目进度列表
        """
        projects = []

        if not self.db:
            return projects

        try:
            rows = self.db.fetch_all(
                """SELECT id, keyword, marketplace_id, platform, status,
                          product_count, created_at, updated_at
                   FROM sourcing_projects
                   ORDER BY updated_at DESC
                   LIMIT 20"""
            )

            if not rows:
                return projects

            for row in rows:
                r = dict(row)
                project_id = r["id"]

                # 获取各阶段完成数
                analyzed = 0
                profit_done = 0
                try:
                    a_row = self.db.fetch_all(
                        "SELECT COUNT(DISTINCT asin) AS cnt FROM analysis_tasks WHERE project_id = %s AND status = 'completed'",
                        (project_id,),
                    )
                    analyzed = int(a_row[0]["cnt"]) if a_row else 0

                    p_row = self.db.fetch_all(
                        "SELECT COUNT(*) AS cnt FROM profit_calculations WHERE project_id = %s",
                        (project_id,),
                    )
                    profit_done = int(p_row[0]["cnt"]) if p_row else 0
                except Exception:
                    pass

                product_count = r.get("product_count") or 0

                # 计算进度百分比
                if product_count > 0:
                    progress = round(
                        (analyzed + profit_done) / (product_count * 2) * 100
                    )
                else:
                    progress = 0

                projects.append({
                    "id": project_id,
                    "keyword": r.get("keyword", ""),
                    "marketplace": r.get("marketplace_id", ""),
                    "platform": r.get("platform", ""),
                    "status": r.get("status", ""),
                    "product_count": product_count,
                    "analyzed_count": analyzed,
                    "profit_calculated": profit_done,
                    "progress_pct": min(progress, 100),
                    "created_at": str(r.get("created_at", "")),
                    "updated_at": str(r.get("updated_at", "")),
                })

        except Exception as e:
            logger.warning(f"项目进度查询失败: {e}")

        return projects

    # ------------------------------------------------------------------
    # 利润分布分析
    # ------------------------------------------------------------------
    def get_profit_distribution(self) -> dict:
        """
        获取利润率分布数据（用于直方图）
        :return: 利润分布数据
        """
        result = {
            "labels": ["<0%", "0-10%", "10-20%", "20-30%", "30-40%", "40%+"],
            "counts": [0, 0, 0, 0, 0, 0],
            "total": 0,
            "avg_margin": 0,
        }

        if not self.db:
            return result

        try:
            rows = self.db.fetch_all(
                "SELECT profit_margin FROM profit_calculations"
            )

            if not rows:
                return result

            margins = [float(dict(r)["profit_margin"]) for r in rows if dict(r).get("profit_margin") is not None]
            result["total"] = len(margins)

            if margins:
                result["avg_margin"] = round(sum(margins) / len(margins), 1)

            for m in margins:
                if m < 0:
                    result["counts"][0] += 1
                elif m < 10:
                    result["counts"][1] += 1
                elif m < 20:
                    result["counts"][2] += 1
                elif m < 30:
                    result["counts"][3] += 1
                elif m < 40:
                    result["counts"][4] += 1
                else:
                    result["counts"][5] += 1

        except Exception as e:
            logger.warning(f"利润分布查询失败: {e}")

        return result

    # ------------------------------------------------------------------
    # 综合看板数据
    # ------------------------------------------------------------------
    def get_full_dashboard(self, project_id: int = None) -> dict:
        """
        获取完整的看板数据
        :param project_id: 项目 ID（可选）
        :return: 综合看板数据
        """
        return {
            "kpi_cards": self.get_kpi_cards(),
            "funnel": self.get_selection_funnel(project_id),
            "activity_trend": self.get_activity_trend(30),
            "project_progress": self.get_project_progress(),
            "profit_distribution": self.get_profit_distribution(),
            "generated_at": datetime.now().isoformat(),
        }
