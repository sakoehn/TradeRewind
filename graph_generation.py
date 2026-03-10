"""Backward-compatibility shim for graph_generation.

The chart logic has moved into the ``charts`` package:

* ``charts/common.py``               - shared building blocks
* ``charts/buy_and_hold_chart.py``   - Buy-and-Hold dashboard
* ``charts/moving_average_chart.py`` - Moving Average Crossover dashboard
* ``charts/__init__.py``             - routing via ``strategy_dashboard``

This module re-exports ``strategy_dashboard`` so that any existing code
still importing from ``graph_generation`` continues to work unchanged.

Prefer importing directly from ``charts`` in new code::

    from charts import strategy_dashboard
"""

from charts import strategy_dashboard  # noqa: F401 - public re-export

__all__ = ["strategy_dashboard"]
