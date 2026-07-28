"""Sanitized Discovery execution errors for total non-usable failures."""

from app.agents.contracts import AgentFailure


class DiscoveryExecutionError(Exception):
    """A total Discovery failure carrying only one stable typed issue."""

    __slots__ = ("failure",)

    def __init__(self, failure: AgentFailure) -> None:
        self.failure = failure
        super().__init__(failure.code.value)


class InvalidDiscoveryModelOutputError(Exception):
    """A model result did not close over its run-local normalized registry."""

