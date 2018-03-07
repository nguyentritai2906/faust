import abc
import asyncio
import typing
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    List,
    Mapping,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    no_type_check,
)

from mode import Seconds, ServiceT

from .channels import ChannelT
from .core import K
from .events import EventT
from .models import FieldDescriptorT, ModelArg
from .topics import TopicT

if typing.TYPE_CHECKING:
    from .app import AppT
    from .join import JoinT
else:
    class AppT: ...    # noqa
    class JoinT: ...   # noqa

__all__ = [
    'Processor',
    'GroupByKeyArg',
    'StreamT',
    'T',
    'T_co',
    'T_contra',
]

# Used for typing StreamT[Withdrawal]
T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
T_contra = TypeVar('T_contra', contravariant=True)

Processor = Callable[[T], Union[T, Awaitable[T]]]

#: Type of the `key` argument to `Stream.group_by()`
GroupByKeyArg = Union[FieldDescriptorT, Callable[[T], K]]


class JoinableT(abc.ABC):

    @abc.abstractmethod
    def combine(self, *nodes: 'JoinableT', **kwargs: Any) -> 'StreamT':
        ...

    @abc.abstractmethod
    def join(self, *fields: FieldDescriptorT) -> 'StreamT':
        ...

    @abc.abstractmethod
    def left_join(self, *fields: FieldDescriptorT) -> 'StreamT':
        ...

    @abc.abstractmethod
    def inner_join(self, *fields: FieldDescriptorT) -> 'StreamT':
        ...

    @abc.abstractmethod
    def outer_join(self, *fields: FieldDescriptorT) -> 'StreamT':
        ...

    @abc.abstractmethod
    def __and__(self, other: Any) -> Any:
        ...


class StreamT(AsyncIterable[T_co], JoinableT, ServiceT):

    app: AppT = None
    channel: AsyncIterator[T_co] = None
    outbox: asyncio.Queue = None
    join_strategy: JoinT = None
    task_owner: asyncio.Task = None
    current_event: EventT = None
    concurrency_index: int = None

    # List of combined streams/tables after ret = (s1 & s2) combined them.
    # AFter this ret.combined == [s1, s2]
    combined: List[JoinableT] = None

    # group_by, through, etc. sets this, and it means the
    # active stream (the one the agent would be reading from) can be found
    # by walking the path of links::
    #    >>> node = stream
    #    >>> while node._next:
    #    ...     node = node._next
    # which is also what .get_active_stream() gives
    _next: 'StreamT' = None
    _prev: 'StreamT' = None

    @abc.abstractmethod
    def __init__(self,
                 channel: AsyncIterator[T_co] = None,
                 *,
                 processors: Iterable[Processor[T]] = None,
                 combined: List[JoinableT] = None,
                 join_strategy: JoinT = None,
                 loop: asyncio.AbstractEventLoop = None) -> None:
        ...

    @abc.abstractmethod
    def get_active_stream(self) -> 'StreamT':
        ...

    @abc.abstractmethod
    def add_processor(self, processor: Processor[T]) -> None:
        ...

    @abc.abstractmethod
    def info(self) -> Mapping[str, Any]:
        ...

    @abc.abstractmethod
    def clone(self, **kwargs: Any) -> 'StreamT':
        ...

    @abc.abstractmethod
    @no_type_check
    async def items(self) -> AsyncIterator[Tuple[K, T_co]]:
        ...

    @abc.abstractmethod
    @no_type_check
    async def events(self) -> AsyncIterable[EventT]:
        ...

    @abc.abstractmethod
    @no_type_check
    async def take(self, max_: int,
                   within: Seconds) -> AsyncIterable[Sequence[T_co]]:
        ...

    @abc.abstractmethod
    def tee(self, n: int = 2) -> Tuple['StreamT', ...]:
        ...

    @abc.abstractmethod
    def enumerate(self, start: int = 0) -> AsyncIterable[Tuple[int, T_co]]:
        ...

    @abc.abstractmethod
    def through(self, channel: Union[str, ChannelT]) -> 'StreamT':
        ...

    @abc.abstractmethod
    def echo(self, *channels: Union[str, ChannelT]) -> 'StreamT':
        ...

    @abc.abstractmethod
    def group_by(self,
                 key: GroupByKeyArg,
                 *,
                 name: str = None,
                 topic: TopicT = None) -> 'StreamT':
        ...

    @abc.abstractmethod
    def derive_topic(self,
                     name: str,
                     *,
                     key_type: ModelArg = None,
                     value_type: ModelArg = None,
                     prefix: str = '',
                     suffix: str = '') -> TopicT:
        ...

    @abc.abstractmethod
    async def throw(self, exc: BaseException) -> None:
        ...

    @abc.abstractmethod
    async def send(self, value: T_contra) -> None:
        ...

    @abc.abstractmethod
    def __copy__(self) -> 'StreamT':
        ...

    @abc.abstractmethod
    def __iter__(self) -> Any:
        ...

    @abc.abstractmethod
    def __next__(self) -> T:
        ...

    @abc.abstractmethod
    def __aiter__(self) -> AsyncIterator[T_co]:
        ...

    @abc.abstractmethod
    async def ack(self, event: EventT) -> bool:
        ...
