def readable_size(size: int) -> str:
    for unit in ['B','KB','MB','GB','TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

def progress_bar(percentage: float, width: int = 10) -> str:
    full = int(width * percentage / 100)
    return '▰' * full + '▱' * (width - full)