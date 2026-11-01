from dataclasses import dataclass


class AppError(Exception):
    """A user-visible domain error; preserve unsaved editor content."""


class ConflictError(AppError):
    pass


class ValidationError(AppError):
    pass


@dataclass(frozen=True)
class Note:
    id: str
    title: str
    body: str
    tags: tuple[str, ...]
    created_at: str
    updated_at: str
    revision: int
    deleted: bool = False


MAX_BODY_BYTES = 1024 * 1024
MAX_ACTIVE_NOTES = 5000
