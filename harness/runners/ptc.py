"""Shared JS prelude and transport for expected host rejections."""

from functools import wraps
from pathlib import Path

from harness.contracts import Rejected

PTC_PRELUDE = Path(__file__).with_name("ptc.js").read_text(encoding="utf-8")


def bridge_method(method):
    """Keep native APIs exception-based; carry only expected rejections across PTC.

    Arbitrary executor errors and cancellation are not serialized as domain data.
    wraps preserves the signature and docstring used for agent tool schemas.
    """

    @wraps(method)
    async def invoke(*args, **kwargs):
        try:
            return await method(*args, **kwargs)
        except Rejected as error:
            return {"__harness_rejection__": str(error)}

    return invoke
