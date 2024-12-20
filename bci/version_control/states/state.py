from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum


class StateCondition(Enum):
    """
    The condition of a state.
    """

    # This state has been evaluated and the result is available.
    COMPLETED = 0
    # The evaluation of this state has failed.
    FAILED = 1
    # The evaluation of this state is in progress.
    IN_PROGRESS = 2
    # The evaluation of this state has not started yet.
    PENDING = 3
    # This state is not available.
    UNAVAILABLE = 4


@dataclass(frozen=True)
class StateResult:
    requests: list[dict[str, str]]
    request_vars: list[dict[str, str]]
    log_vars: list[dict[str, str]]
    is_dirty: bool

    @property
    def reproduced(self):
        entry_if_reproduced = {'var': 'reproduced', 'val': 'OK'}
        reproduced_in_req_vars = [entry for entry in self.request_vars if entry == entry_if_reproduced] != []
        reproduced_in_log_vars = [entry for entry in self.log_vars if entry == entry_if_reproduced] != []
        return reproduced_in_req_vars or reproduced_in_log_vars

    @staticmethod
    def from_dict(data: dict, is_dirty: bool = False) -> StateResult:
        return StateResult(data['requests'], data['req_vars'], data['log_vars'], is_dirty)


class State:
    def __init__(self):
        self.condition = StateCondition.PENDING
        self.result: StateResult
        self.outcome: bool | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def browser_name(self) -> str:
        pass

    @property
    @abstractmethod
    def type(self) -> str:
        pass

    @property
    @abstractmethod
    def index(self) -> int:
        """
        The index of the element in the sequence.
        """
        pass

    @property
    @abstractmethod
    def revision_nb(self) -> int:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass

    @staticmethod
    def from_dict(data: dict) -> State:
        from bci.version_control.states.revisions.base import BaseRevision
        from bci.version_control.states.versions.base import BaseVersion

        match data['type']:
            case 'revision':
                return BaseRevision.from_dict(data)
            case 'version':
                return BaseVersion.from_dict(data)
            case _:
                raise Exception(f'Unknown state type: {data["type"]}')

    @abstractmethod
    def has_online_binary(self) -> bool:
        pass

    @abstractmethod
    def get_online_binary_url(self) -> str:
        pass

    def has_available_binary(self) -> bool:
        if self.condition == StateCondition.UNAVAILABLE:
            return False
        else:
            has_available_binary = self.has_online_binary()
            if not has_available_binary:
                self.condition = StateCondition.UNAVAILABLE
            return has_available_binary

    def get_previous_and_next_state_with_binary(self) -> tuple[State, State]:
        raise NotImplementedError(f'This function is not implemented for {self}')

    def __repr__(self) -> str:
        return f'State(index={self.index})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, State):
            return False
        return self.index == other.index

    def __hash__(self) -> int:
        return hash((self.index, self.browser_name))
