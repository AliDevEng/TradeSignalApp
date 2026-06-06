"""Risk & position sizing — turn a signal into an exact, account-aware trade.

The package is pure and IO-free (mirroring the outcome/performance services): a
small in-code contract-spec table (:mod:`app.services.risk.contracts`) plus a
deterministic sizer (:mod:`app.services.risk.position_sizing`). Nothing here
touches the database, the network, or stored account data — the endpoint built on
it is stateless by construction.
"""

from __future__ import annotations

from app.services.risk.contracts import ContractSpec, get_contract_spec
from app.services.risk.position_sizing import (
    PositionSize,
    PositionSizingError,
    TakeProfitProjection,
    compute_position_size,
)

__all__ = [
    "ContractSpec",
    "PositionSize",
    "PositionSizingError",
    "TakeProfitProjection",
    "compute_position_size",
    "get_contract_spec",
]
