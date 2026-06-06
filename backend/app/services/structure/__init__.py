"""Market-structure analysis — the price *geometry* the AI anchors levels to.

Where :mod:`app.services.indicators` reports momentum/volatility *numbers*, this
package reports the *levels* a trader actually places stops and targets at: swing
pivots, the nearest support/resistance to current price, and the recent range.

Kept pure and separate so the AI prompt can be handed real structure to reason
about — instead of being told to infer it from raw candles — and so the
detection is unit-tested without a model or the network.
"""

from __future__ import annotations

from app.services.structure.analyzer import (
    StructureAnalyzer,
    StructureSnapshot,
    find_pivots,
)

__all__ = [
    "StructureAnalyzer",
    "StructureSnapshot",
    "find_pivots",
]
