"""Domain errors. The UI layer turns these into user-facing messages."""


class UVRError(Exception):
    """Base class for expected, user-reportable failures."""


class SeparationError(UVRError):
    pass


class DownloadError(UVRError):
    pass
