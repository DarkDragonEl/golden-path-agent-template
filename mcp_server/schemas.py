from pydantic import BaseModel


class PlaceholderLookupInput(BaseModel):
    query: str
    write: bool = False
    # TODO(domain): replace with the real domain tool's actual input fields
    # once the 1-2 domain tools are selected (e.g. record_id, filters).
    # `write` is a generic placeholder signal distinguishing a
    # consequential call from a read — keep an equivalent signal even
    # after the real schema replaces this one.


class PlaceholderLookupOutput(BaseModel):
    result: str
    source: str
    # TODO(domain): replace with the real domain tool's actual output shape
    # (structured record / citation metadata / status code).
