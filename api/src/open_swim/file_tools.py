import os


def remove_file(file_path: str) -> bool:
    """
    Clean up (delete) an MP3 file.
    
    Args:
        file_path: Full path to the file to delete
        
    Returns:
        True if successfully deleted, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            print(f"Cleaned up file: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Failed to delete file {file_path}: {e}")
        return False