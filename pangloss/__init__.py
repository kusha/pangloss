"""
Pangloss: A language graph analysis and transformation framework.

Pangloss analyzes relationships between natural languages using graph-based
algorithms to identify linguistic patterns, generate similarity matrices,
and transform language representations.
"""

__version__ = "0.1.0"
__author__ = "Pangloss Contributors"

from . import data, graph, algo, output

__all__ = ["data", "graph", "algo", "output"]
