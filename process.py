import pickle
from typing import Callable, Any, Tuple, Dict
from local import get_parcel


class Process:
    def __init__(
        self,
        target: Callable[[Any, ...], Any],
        *args: Tuple[Any, ...],
        **kwargs: Dict[str, Any]
    ):
        self.target = target
        self.args = args
        self.kwargs = kwargs

    def start(self, output) -> None:

        # Pickle the ``Process`` object.
        parcel = get_parcel(self)

        # Broadcast the parcel to remote nodes.
        for out in output.values():
            out.stdin.buffer.write(parcel + "\n".encode("ascii"))
