import os
from pathlib import Path

from srcs.config import CHUNK_COUNT
from srcs.path_utils import chunk_path as get_chunk_path, ensure_chunk_dir, PROJECT_ROOT


def chunk_name(base, index):
    return f"{base}_{index}"


def parse_chunk_base(name):
    base, separator, index = name.rpartition("_")
    if not separator or not base or not index.isdigit():
        return None
    return base


def split_file(filepath, num_chunks=CHUNK_COUNT):
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


def merge_chunks(
    content_name: str,
    num_chunks: int = CHUNK_COUNT,
    output_dir: str = ".",
    output_name: str | None = None
) -> str | None:
    basename = os.path.splitext(content_name)[0]
    output_base = PROJECT_ROOT if output_dir == "." else Path(output_dir)
    final_name: str = output_name or basename

    chunk_paths = []
    for i in range(1, num_chunks + 1):
        current_chunk = chunk_name(basename, i)
        current_path = get_chunk_path(current_chunk)
        if current_path.exists():
            chunk_paths.append(current_path)
        else:
            print(f"Error: Chunk '{current_chunk}' not found. Cannot merge.")
            return None

    output_path = output_base / final_name

    with open(output_path, "wb") as out:
        for chunk_path in chunk_paths:
            with open(chunk_path, "rb") as cf:
                out.write(cf.read())

    return str(output_path)
