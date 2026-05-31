"""Controller-layer error types — the business-logic failure vocabulary.

These are framework-agnostic on purpose: a controller raises them without
knowing anything about HTTP status codes, and the view/error-handling layer
(Iteration 4.4) maps them to responses in one place. That keeps the mapping
between a domain failure and its wire representation single-sourced instead of
scattered across every handler.
"""

from __future__ import annotations


class ControllerError(Exception):
    """Base for every error originating in the controller layer."""


class ResourceNotFoundError(ControllerError):
    """A requested resource (by id, symbol, …) does not exist.

    Carries the resource kind and identifier separately so a handler can build a
    structured 404 without re-parsing the message string.
    """

    def __init__(self, resource: str, identifier: object) -> None:
        self.resource = resource
        self.identifier = str(identifier)
        super().__init__(f"{resource} '{self.identifier}' was not found")
