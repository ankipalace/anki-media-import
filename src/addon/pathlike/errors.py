class MalformedURLError(Exception):
    pass


class RootNotFoundError(Exception):
    """The URL looks fine, but doesn't point to a valid location."""
    pass


class RequestError(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__()
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        return f"RequestError<{self.code}>: {self.msg}"
