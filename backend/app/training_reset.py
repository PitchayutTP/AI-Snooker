"""Bounded cleanup of generated camera evidence, never datasets/models/downloads."""

from pathlib import Path
from uuid import UUID


def recording_cleanup_plan(recordings, profile_id, session_id=None):
    root = Path(recordings).absolute()
    if root.resolve() != root:
        raise ValueError("Recording directory must not contain a symlink")
    profile = int(profile_id)
    if profile <= 0:
        raise ValueError("Invalid profile")
    folder = root / str(profile)
    if session_id is not None:
        folder = folder / str(UUID(str(session_id)))
    if folder.resolve() != folder or not folder.resolve().is_relative_to(root.resolve()):
        raise ValueError("Invalid profile recording directory")
    if not folder.exists():
        return [], []
    files = []
    directories = []

    def visit(directory):
        for child in directory.iterdir():
            if (
                child.is_symlink()
                or child.resolve() != child.absolute()
                or not child.resolve().is_relative_to(folder)
            ):
                raise ValueError("Unsafe recording path")
            if child.is_dir():
                visit(child)
            elif child.is_file() and child.suffix.lower() in (".jpg", ".webm"):
                files.append(child)
            else:
                raise ValueError("Unexpected file in recording directory")
        directories.append(directory)

    visit(folder)
    return files, directories


def cleanup_recordings(recordings, profile_id, session_id=None):
    # Revalidate immediately before mutation, including on a retry after a file lock.
    files, directories = recording_cleanup_plan(recordings, profile_id, session_id)
    removed = 0
    failed = 0
    for path in files:
        try:
            if path.is_symlink() or path.resolve() != path.absolute():
                raise ValueError("Unsafe recording path")
            path.unlink(missing_ok=True)
            removed += 1
        except (OSError, ValueError):
            failed += 1
    for folder in directories:
        try:
            if folder.is_symlink() or folder.resolve() != folder.absolute():
                raise ValueError("Unsafe recording directory")
            folder.rmdir()
        except (OSError, ValueError):
            failed += 1
    return {"images_removed": removed, "cleanup_complete": failed == 0}
