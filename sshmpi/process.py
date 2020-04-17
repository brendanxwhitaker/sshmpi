""" Class for distributed processes. """
from typing import Callable, Any, Tuple, Dict
from sshmpi.parcel import get_parcel

# pylint: disable=too-few-public-methods


class Process:
    """ Called with a function and arguments to run on remote nodes. """

    def __init__(
        self,
        target: Callable[..., Any],
        *args: Tuple[Any, ...],
        **kwargs: Dict[str, Any]
    ):
        self.target = target
        self.args = args
        self.kwargs = kwargs

    def start(self, output: dict) -> None:
        """ Broadcast the ``Process`` to remote nodes. """
        # Pickle the ``Process`` object.
        parcel = get_parcel(self)

        # Broadcast the parcel to remote nodes.
        for out in output.values():
            out.stdin.buffer.write(parcel + "\n".encode("ascii"))
