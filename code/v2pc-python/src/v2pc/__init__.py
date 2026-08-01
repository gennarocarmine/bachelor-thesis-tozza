"""Visual Two-Party Computation.

Il package espone un nucleo indipendente dalle interfacce: la stessa costruzione
viene usata dalla riga di comando e dalla demo web.
"""

from .circuit import Circuit, parse_expression
from .protocol import (
    Construction,
    Evaluation,
    Transfer,
    build,
    evaluate,
    reconstruct,
    select_shares,
)

__all__ = [
    "Circuit",
    "Construction",
    "Evaluation",
    "Transfer",
    "build",
    "evaluate",
    "parse_expression",
    "reconstruct",
    "select_shares",
]

__version__ = "0.1.0"
