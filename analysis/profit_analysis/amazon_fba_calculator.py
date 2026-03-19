"""
Amazon FBA 利润计算器 - 兼容别名模块

提供对 analysis.profit_analysis.amazon_profit_calculator.AmazonFBAProfitCalculator
的便捷导入路径，同时保持向后兼容。

两种导入方式均可使用：
    from analysis.profit_analysis.amazon_fba_calculator import AmazonFBAProfitCalculator
    from analysis.profit_analysis.amazon_profit_calculator import AmazonFBAProfitCalculator
"""

# 直接从实际实现模块导入
from analysis.profit_analysis.amazon_profit_calculator import AmazonFBAProfitCalculator

__all__ = ["AmazonFBAProfitCalculator"]
