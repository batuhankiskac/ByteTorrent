import os


def split_file(filepath, num_chunks=3):
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.")
        return []

    filesize = os.path.getsize(filepath)
    chunk_size = filesize // num_chunks
    remainder = filesize % num_chunks

    basename = os.path.splitext(os.path.basename(filepath))[0]
    dirpath = os.path.dirname(filepath) or "."

    chunk_names = []

    with open(filepath, "rb") as f:
        for i in range(num_chunks):
            size = chunk_size + (1 if i < remainder else 0)
            data = f.read(size)

            chunk_name = f"{basename}_{i + 1}"
            chunk_path = os.path.join(dirpath, chunk_name)

            with open(chunk_path, "wb") as cf:
                cf.write(data)

            chunk_names.append(chunk_name)

    return chunk_names


def merge_chunks(content_name, num_chunks=3, output_dir="."):
    basename = os.path.splitext(content_name)[0]

    chunk_paths = []
    for i in range(1, num_chunks + 1):
        chunk_name = f"{basename}_{i}"
        if os.path.exists(chunk_name):
            chunk_paths.append(chunk_name)
        else:
            print(f"Error: Chunk '{chunk_name}' not found. Cannot merge.")
            return None

    output_path = os.path.join(output_dir, basename)

    with open(output_path, "wb") as out:
        for cp in chunk_paths:
            with open(cp, "rb") as cf:
                out.write(cf.read())

    print(f"Merged {num_chunks} chunks into '{output_path}'")
    return output_path