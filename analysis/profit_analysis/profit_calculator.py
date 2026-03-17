"""
Coupang 选品系统 - 利润分析模块
功能:
  1. 成本核算（采购成本 + 头程运费 + 平台佣金 + 配送费）
  2. 利润计算（单件利润、利润率、ROI）
  3. 盈亏平衡分析
  4. 多货源比价
"""

import json
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP

from utils.logger import get_logger
from i18n import t, get_language

logger = get_logger()


# ============================================================
# Coupang 平台费用参数（默认值，可通过配置覆盖）
# ============================================================
DEFAULT_PARAMS = {
    # 汇率 (1 RMB = ? KRW)
    "exchange_rate": 190.0,

    # 头程运费 (RMB/kg)
    "freight_per_kg": 15.0,

    # Coupang 平台佣金比例（按类目不同，默认10%）
    "commission_rate": 0.10,

    # Coupang 配送费 (KRW/件)
    "delivery_fee_krw": 3500,

    # 增值税 (韩国VAT 10%)
    "vat_rate": 0.10,

    # 其他费用（包装、标签等，RMB/件）
    "misc_cost_rmb": 2.0,

    # 退货率
    "return_rate": 0.05,
}


class ProfitCalculator:
    """
    利润计算器
    支持: 单品利润核算 / 批量比价 / 盈亏平衡分析
    """

    def __init__(self, params: dict = None):
        self.params = {**DEFAULT_PARAMS, **(params or {})}

    def calculate(self, selling_price_krw: float, source_data: dict,
                  weight_kg: float = 0.5, category_commission: float = None) -> dict:
        """
        计算单个产品的利润

        :param selling_price_krw: Coupang售价 (KRW)
        :param source_data: 1688货源数据 {"price_rmb": ..., "moq": ...}
        :param weight_kg: 产品重量 (kg)
        :param category_commission: 类目佣金比例（覆盖默认值）
        :return: 利润分析结果
        """
        p = self.params
        rate = p["exchange_rate"]
        commission_rate = category_commission or p["commission_rate"]

        # === 成本计算 ===

        # 1. 采购成本 (RMB → KRW)
        purchase_cost_rmb = source_data.get("price_rmb", 0) or 0
        purchase_cost_krw = purchase_cost_rmb * rate

        # 2. 头程运费 (RMB → KRW)
        freight_rmb = weight_kg * p["freight_per_kg"]
        freight_krw = freight_rmb * rate

        # 3. 其他费用 (RMB → KRW)
        misc_cost_krw = p["misc_cost_rmb"] * rate

        # 4. Coupang 配送费 (KRW)
        delivery_fee = p["delivery_fee_krw"]

        # 5. 平台佣金 (基于售价)
        commission = selling_price_krw * commission_rate

        # 6. 增值税 (基于售价)
        vat = selling_price_krw * p["vat_rate"]

        # === 总成本 ===
        total_cost_krw = purchase_cost_krw + freight_krw + misc_cost_krw + delivery_fee + commission + vat

        # === 利润 ===
        profit_per_unit = selling_price_krw - total_cost_krw
        profit_margin = (profit_per_unit / selling_price_krw) if selling_price_krw > 0 else 0

        # === ROI (投资回报率) ===
        investment = purchase_cost_krw + freight_krw + misc_cost_krw  # 前期投入
        roi = (profit_per_unit / investment) if investment > 0 else 0

        # === 考虑退货的实际利润 ===
        return_rate = p["return_rate"]
        effective_profit = profit_per_unit * (1 - return_rate)

        # === 盈亏平衡价格 ===
        # 售价 = 总成本 → 求最低售价
        # 售价 - (采购+运费+杂费+配送费) - 售价*佣金率 - 售价*VAT率 = 0
        # 售价 * (1 - 佣金率 - VAT率) = 固定成本
        fixed_costs = purchase_cost_krw + freight_krw + misc_cost_krw + delivery_fee
        variable_rate = commission_rate + p["vat_rate"]
        breakeven_price = fixed_costs / (1 - variable_rate) if variable_rate < 1 else float('inf')

        result = {
            # 成本明细
            "cost_breakdown": {
                "purchase_cost_rmb": round(purchase_cost_rmb, 2),
                "purchase_cost_krw": round(purchase_cost_krw, 0),
                "freight_rmb": round(freight_rmb, 2),
                "freight_krw": round(freight_krw, 0),
                "misc_cost_krw": round(misc_cost_krw, 0),
                "delivery_fee_krw": round(delivery_fee, 0),
                "commission_krw": round(commission, 0),
                "commission_rate": f"{commission_rate*100:.1f}%",
                "vat_krw": round(vat, 0),
            },
            # 汇总
            "total_cost_krw": round(total_cost_krw, 0),
            "selling_price_krw": round(selling_price_krw, 0),
            "profit_per_unit_krw": round(profit_per_unit, 0),
            "profit_margin": f"{profit_margin*100:.1f}%",
            "roi": f"{roi*100:.1f}%",
            # 考虑退货
            "effective_profit_krw": round(effective_profit, 0),
            "return_rate": f"{return_rate*100:.1f}%",
            # 盈亏平衡
            "breakeven_price_krw": round(breakeven_price, 0),
            # 判断
            "is_profitable": profit_per_unit > 0,
            "profitability_level": self._profitability_level(profit_margin),
            # 参数
            "exchange_rate": rate,
            "weight_kg": weight_kg,
        }

        return result

    def batch_compare(self, selling_price_krw: float, sources: list[dict],
                      weight_kg: float = 0.5) -> list[dict]:
        """
        批量比较多个货源的利润

        :param selling_price_krw: 售价
        :param sources: 1688货源列表
        :param weight_kg: 产品重量
        :return: 按利润排序的结果列表
        """
        results = []

        for source in sources:
            calc = self.calculate(selling_price_krw, source, weight_kg)
            calc["source"] = {
                "title": source.get("title", ""),
                "supplier_name": source.get("supplier_name", ""),
                "price_rmb": source.get("price_rmb"),
                "moq": source.get("moq", 1),
                "url": source.get("url", ""),
            }
            results.append(calc)

        # 按利润降序排列
        results.sort(key=lambda x: x["profit_per_unit_krw"], reverse=True)

        return results

    def sensitivity_analysis(self, selling_price_krw: float, source_data: dict,
                             weight_kg: float = 0.5) -> dict:
        """
        敏感性分析：分析各因素变化对利润的影响

        :return: 各因素变化±20%时的利润变化
        """
        base = self.calculate(selling_price_krw, source_data, weight_kg)
        base_profit = base["profit_per_unit_krw"]

        factors = {
            "selling_price": {"param": "selling_price_krw", "base": selling_price_krw},
            "purchase_cost": {"param": "price_rmb", "base": source_data.get("price_rmb", 0)},
            "exchange_rate": {"param": "exchange_rate", "base": self.params["exchange_rate"]},
            "freight": {"param": "freight_per_kg", "base": self.params["freight_per_kg"]},
        }

        analysis = {}
        for factor_name, info in factors.items():
            base_val = info["base"]
            if base_val == 0:
                continue

            # -20% 和 +20%
            results = {}
            for pct in [-20, -10, 0, 10, 20]:
                adjusted = base_val * (1 + pct / 100)

                if factor_name == "selling_price":
                    calc = self.calculate(adjusted, source_data, weight_kg)
                elif factor_name == "purchase_cost":
                    adjusted_source = {**source_data, "price_rmb": adjusted}
                    calc = self.calculate(selling_price_krw, adjusted_source, weight_kg)
                elif factor_name == "exchange_rate":
                    old_rate = self.params["exchange_rate"]
                    self.params["exchange_rate"] = adjusted
                    calc = self.calculate(selling_price_krw, source_data, weight_kg)
                    self.params["exchange_rate"] = old_rate
                elif factor_name == "freight":
                    old_freight = self.params["freight_per_kg"]
                    self.params["freight_per_kg"] = adjusted
                    calc = self.calculate(selling_price_krw, source_data, weight_kg)
                    self.params["freight_per_kg"] = old_freight

                results[f"{pct:+d}%"] = {
                    "value": round(adjusted, 2),
                    "profit_krw": calc["profit_per_unit_krw"],
                    "profit_change": calc["profit_per_unit_krw"] - base_profit,
                    "margin": calc["profit_margin"],
                }

            analysis[factor_name] = results

        return {
            "base_profit_krw": base_profit,
            "factors": analysis,
        }

    def _profitability_level(self, margin: float) -> str:
        """利润率等级判定"""
        if margin >= 0.30:
            return "excellent"  # 优秀
        elif margin >= 0.20:
            return "good"       # 良好
        elif margin >= 0.10:
            return "acceptable" # 可接受
        elif margin >= 0:
            return "marginal"   # 微利
        else:
            return "loss"       # 亏损

    def format_report(self, result: dict) -> str:
        """
        格式化利润报告（多语言）
        """
        lang = get_language()

        if lang == "zh_CN":
            return self._format_zh(result)
        elif lang == "ko_KR":
            return self._format_ko(result)
        else:
            return self._format_en(result)

    def _format_zh(self, r: dict) -> str:
        """中文利润报告"""
        cb = r["cost_breakdown"]
        status = "✓ 可盈利" if r["is_profitable"] else "✗ 不可盈利"
        return f"""
┌─────────────────────────────────────────┐
│           利润分析报告                    │
├─────────────────────────────────────────┤
│ 售价:           {r['selling_price_krw']:>12,.0f} KRW      │
│                                         │
│ 成本明细:                                │
│   采购成本:     {cb['purchase_cost_rmb']:>8,.2f} RMB ({cb['purchase_cost_krw']:>8,.0f} KRW) │
│   头程运费:     {cb['freight_rmb']:>8,.2f} RMB ({cb['freight_krw']:>8,.0f} KRW) │
│   杂费:                     {cb['misc_cost_krw']:>8,.0f} KRW │
│   配送费:                   {cb['delivery_fee_krw']:>8,.0f} KRW │
│   佣金({cb['commission_rate']}):           {cb['commission_krw']:>8,.0f} KRW │
│   增值税:                   {cb['vat_krw']:>8,.0f} KRW │
│                                         │
│ 总成本:         {r['total_cost_krw']:>12,.0f} KRW      │
│ 单件利润:       {r['profit_per_unit_krw']:>12,.0f} KRW      │
│ 利润率:         {r['profit_margin']:>12s}          │
│ ROI:            {r['roi']:>12s}          │
│ 盈亏平衡价:     {r['breakeven_price_krw']:>12,.0f} KRW      │
│                                         │
│ 结论: {status:>20s}                │
└─────────────────────────────────────────┘"""

    def _format_en(self, r: dict) -> str:
        """英文利润报告"""
        cb = r["cost_breakdown"]
        status = "Profitable" if r["is_profitable"] else "Not Profitable"
        return f"""
┌─────────────────────────────────────────┐
│         Profit Analysis Report          │
├─────────────────────────────────────────┤
│ Selling Price:  {r['selling_price_krw']:>12,.0f} KRW      │
│ Total Cost:     {r['total_cost_krw']:>12,.0f} KRW      │
│ Profit/Unit:    {r['profit_per_unit_krw']:>12,.0f} KRW      │
│ Profit Margin:  {r['profit_margin']:>12s}          │
│ ROI:            {r['roi']:>12s}          │
│ Breakeven:      {r['breakeven_price_krw']:>12,.0f} KRW      │
│ Status:         {status:>20s}      │
└─────────────────────────────────────────┘"""

    def _format_ko(self, r: dict) -> str:
        """韩文利润报告"""
        cb = r["cost_breakdown"]
        status = "수익성 있음" if r["is_profitable"] else "수익성 없음"
        return f"""
┌─────────────────────────────────────────┐
│          수익 분석 보고서                  │
├─────────────────────────────────────────┤
│ 판매가:         {r['selling_price_krw']:>12,.0f} KRW      │
│ 총 원가:        {r['total_cost_krw']:>12,.0f} KRW      │
│ 개당 이익:      {r['profit_per_unit_krw']:>12,.0f} KRW      │
│ 이익률:         {r['profit_margin']:>12s}          │
│ ROI:            {r['roi']:>12s}          │
│ 손익분기가:     {r['breakeven_price_krw']:>12,.0f} KRW      │
│ 결과:           {status:>20s}      │
└─────────────────────────────────────────┘"""
