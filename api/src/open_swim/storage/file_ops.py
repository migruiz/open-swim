import os


def delete_path(file_path: str) -> bool:
    """
    Delete a file path if it exists.

    Returns True if the file was removed, False otherwise.
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            print(f"Deleted file: {file_path}")
            return True
        return False
    except Exception as exc:
        print(f"Failed to delete file {file_path}: {exc}")
        return False
