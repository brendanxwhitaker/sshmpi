# type: ignore
""" SSHMPI utilities. """
import functools
from typing import Tuple, Any, Dict

# pylint: disable=too-few-public-methods


def partialclass(cls: type, *args: Tuple[Any, ...], **kwargs: Dict[str, Any]) -> type:
    """ Like ``functools.partial``, but for a class instantiator. """

    class Cls(cls):
        """ Dummy class to partial-ize. """

        __init__ = functools.partialmethod(cls.__init__, *args, **kwargs)

    return Cls
