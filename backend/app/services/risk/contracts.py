"""Per-instrument contract specifications — the metadata that turns a price
distance into account-currency risk.

Position sizing needs to know how much money a 1.0 price move is worth for one
standard lot of an instrument; that is a property of the *contract*, not of the
signal. Rather than add columns + a migration to ``pairs`` for a single
currently-traded instrument, the specs live in this small, in-code lookup (the
iteration plan explicitly allows "a small spec lookup"). It is a pure, IO-free
table; promoting it onto the ``Pair`` model later is a mechanical change behind
the same :func:`get_contract_spec` seam.

Money is ``Decimal`` throughout — never float for prices or P&L.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ContractSpec:
    """How one instrument's price moves map to money.

    ``contract_size`` is the number of base units in one standard lot (XAUUSD:
    100 troy oz), so the loss for one lot if price moves ``d`` against you is
    ``d * contract_size`` in the ``quote_currency``. ``min_lot``/``lot_step`` are
    the broker's tradeable granularity; ``pip`` is the smallest quoted price
    increment, used to express a position's per-pip value.
    """

    symbol: str
    contract_size: Decimal
    min_lot: Decimal
    lot_step: Decimal
    pip: Decimal
    quote_currency: str

    @property
    def pip_value_per_lot(self) -> Decimal:
        """Value of a one-pip move for a single standard lot, in the quote currency."""
        return self.contract_size * self.pip


# XAUUSD (spot Gold): one standard lot is 100 troy oz, so a $1.00 move is
# $100/lot; the conventional pip is $0.01. P&L is denominated in USD, which we
# also take to be the account currency (single-currency assumption, documented on
# the endpoint).
_SPECS: dict[str, ContractSpec] = {
    "XAUUSD": ContractSpec(
        symbol="XAUUSD",
        contract_size=Decimal("100"),
        min_lot=Decimal("0.01"),
        lot_step=Decimal("0.01"),
        pip=Decimal("0.01"),
        quote_currency="USD",
    ),
}


def get_contract_spec(symbol: str) -> ContractSpec | None:
    """Look up the contract spec for ``symbol`` (case-insensitive), or ``None``.

    Returning ``None`` for an unknown instrument is deliberate: mis-sizing a
    position from a guessed spec is dangerous, so the caller surfaces a clean
    "unknown pair" rather than fabricating one.
    """
    return _SPECS.get(symbol.upper())
