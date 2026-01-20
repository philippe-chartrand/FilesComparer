import os

def choose_first(dual_list):
    return {k:v[0] for k,v in dual_list.items()}


def sum_bytes(data):
    return sum(d['size'] for d in data.values())


def sum_mb(data):
    return f"{sum_bytes(data)/1048576:,.0f} Mb"


def remove_trailing_slash(str):
    return str[0:-1] if str.endswith('/') else str


def remove_prefix(str, substring):
    parts = []
    prefix = ['/']+substring.split('/')[1:]
    for i, part in enumerate(str.parts):
        if i < len(prefix):
            assert part == prefix[i]
        else:
            parts.append(part)
    return '/'.join(parts)


def make_dest_directory(dest_dir):
    if not os.path.isdir(dest_dir):
        print(f"Creating destination directory {dest_dir}")
        os.makedirs(dest_dir, exist_ok=True)


def make_partial_dest(posix_path, dir_path):
    partial = "/".join(posix_path.parts[0:-1])
    return partial.removeprefix('/' + dir_path)

