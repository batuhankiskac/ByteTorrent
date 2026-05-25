import os
import re

try:
    from .path_utils import chunk_path, ensure_chunk_dir, PROJECT_ROOT
except ImportError:
    from pathlib import Path
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from srcs.path_utils import chunk_path, ensure_chunk_dir, PROJECT_ROOT


CHUNK_PATTERN = re.compile(r"^(?P<base>.+?)(?:_| )(?P<index>\d+)$")


def chunk_name(base, index):
    return f"{base} {index}"


def parse_chunk_base(name):
    match = CHUNK_PATTERN.match(name)
    if not match:
        return None
    return match.group("base")


def split_file(filepath, num_chunks=3):
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.")
        return []

    filesize = os.path.getsize(filepath)
    chunk_size = filesize // num_chunks
    remainder = filesize % num_chunks

    basename = os.path.splitext(os.path.basename(filepath))[0]
    chunk_dir = ensure_chunk_dir()

    chunk_names = []

    with open(filepath, "rb") as f:
        for i in range(num_chunks):
            size = chunk_size + (1 if i < remainder else 0)
            data = f.read(size)

            current_chunk = chunk_name(basename, i + 1)
            current_path = chunk_dir / current_chunk

            with open(current_path, "wb") as cf:
                cf.write(data)

            chunk_names.append(current_chunk)

    return chunk_names


def merge_chunks(content_name, num_chunks=3, output_dir=".", output_name=None):
    basename = os.path.splitext(content_name)[0]
    output_base = PROJECT_ROOT if output_dir == "." else output_dir
    final_name = output_name or basename

    chunk_paths = []
    for i in range(1, num_chunks + 1):
        preferred = chunk_name(basename, i)
        legacy = f"{basename}_{i}"
        preferred_path = chunk_path(preferred)
        legacy_path = chunk_path(legacy)
        if preferred_path.exists():
            chunk_paths.append(preferred_path)
        elif legacy_path.exists():
            chunk_paths.append(legacy_path)
        else:
            print(f"Error: Chunk '{preferred}' not found. Cannot merge.")
            return None

    output_path = os.path.join(output_base, final_name)

    with open(output_path, "wb") as out:
        for cp in chunk_paths:
            with open(cp, "rb") as cf:
                out.write(cf.read())

    print(f"Merged {num_chunks} chunks into '{output_path}'")
    return output_path
