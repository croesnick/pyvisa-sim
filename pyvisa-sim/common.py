# -*- coding: utf-8 -*-
"""
    pyvisa-sim.common
    ~~~~~~~~~~~~~~~~~

    This code is currently taken from PyVISA-py.
    Do not edit here.

    :copyright: 2014 by PyVISA-sim Authors, see AUTHORS for more details.
    :license: MIT, see LICENSE for more details.
"""

import logging
from typing import Any, Sequence, Generator

from pyvisa import logger

logger = logging.LoggerAdapter(logger, {'backend': 'py'})


class NamedObject:
    """A class to construct named sentinels.
    """

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<%s>' % self.name


def iter_bytes(data: Sequence[int], mask: int, send_end: bool) -> Generator[bytes, None, None]:
    for d in data[:-1]:
        yield bytes([d & ~mask])

    if send_end:
        yield bytes([data[-1] | ~mask])
    else:
        yield bytes([data[-1] & ~mask])


def int_to_byte(value: int) -> bytes:
    return bytes([value])


def last_int(items: Sequence[Any]) -> Any:
    return items[-1]
