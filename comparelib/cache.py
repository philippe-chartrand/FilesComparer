import datetime
import hashlib
from json import JSONDecoder, JSONEncoder, dump, load
from pathlib import Path
import os
import sys


MD5_CHUNK_SIZE = 1048576
MD5_SAMPLE_SIZE = 262144
CACHE_MAX_AGE = 5400


def md5_checksum(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(MD5_CHUNK_SIZE), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def md5_partial_checksum(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        hasher.update(f.read(MD5_SAMPLE_SIZE))
    return hasher.hexdigest()


def calc_cache_file_path(dir_path):
    path_hash = hashlib.md5(dir_path.encode()).hexdigest()
    cache_file_path = Path(path_hash)
    return cache_file_path


def check_cache_age(cache_file_path):
    ctime = datetime.datetime.fromtimestamp(os.stat(cache_file_path).st_ctime)
    now = datetime.datetime.now()
    age = now - ctime
    return age


def can_read_from_cache(dir_path):
    cache_file_path = calc_cache_file_path(dir_path)

    if cache_file_path.is_file():
        age = check_cache_age(cache_file_path)
        if age.seconds < CACHE_MAX_AGE:
            return True
    return False


def exit_if_cache_stale(cache_file_path):
    age = check_cache_age(cache_file_path)
    if age.seconds > CACHE_MAX_AGE:
        print(f"Warning: cache {cache_file_path} is {age.seconds / 60} minutes old, which is more than expected.")
        print(f"Remove or touch {cache_file_path}.")
        sys.exit()


def read_from_cache(dir_path, cache_file_path):
    dir_files = {}
    print(f"Reading {dir_path} infos from cache {cache_file_path}")
    with open(cache_file_path, 'r', encoding='utf-8') as f:
        dir_files = {
            Path(k): dict(path=Path(v['path']), size=v['size'], md5=v['md5'], mtime=v['mtime']) for k, v in
            JSONDecoder().decode(load(f)).items()
        }
    return dir_files


def save_to_cache(dir_path, cache_file_path, dir_files):
    print(f"Saving {dir_path} infos to cache {cache_file_path}")
    with open(cache_file_path, 'w', encoding='utf-8') as f:
        serialized = {str(k): dict(path=str(v['path']), size=v['size'], md5=v['md5'], mtime=v['mtime']) for k, v in
                      dir_files.items()}
        dump(JSONEncoder().encode(serialized), f, ensure_ascii=False, indent=4)


def update_cache(dir_path, dir_data):
    save_to_cache(dir_path, calc_cache_file_path(dir_path), dir_data)


def remove_cache(dir_path):
    cache_file_path = calc_cache_file_path(dir_path)
    print(f"Removing cache infos {cache_file_path} for {dir_path}")
    os.unlink(cache_file_path)


def scan_directories(dir_path):
    dir_files = []
    print(f"Scanning all files in {dir_path} for infos...")
    for p in Path(dir_path).rglob("*.*"):
        if p.is_file() and not 'listes' in p.parts:
            dir_files.append(p)
    return dir_files


def get_files_paginated(dir_path, files_list, offset, size):
    dir_files = {}
    for i, p in enumerate(files_list[offset:offset+size]):
        dir_files[os.fspath(p).replace(dir_path, '')] = dict(path=p, size=os.stat(p).st_size,
                                                                 md5=md5_partial_checksum(p),
                                                                 mtime=os.stat(p).st_mtime)
    return dir_files

def get_files(dir_path):
    cache_file_path = calc_cache_file_path(dir_path)
    dir_files = {}
    feedback_every = 100
    if cache_file_path.is_file():
        exit_if_cache_stale(cache_file_path);
        dir_files = read_from_cache(dir_path, cache_file_path)
    else:
        print(f"Scanning all files in {dir_path} for infos...")
        for i, p in enumerate(Path(dir_path).rglob("*.*")):
            if p.is_file() and not 'listes' in p.parts:
                dir_files[os.fspath(p).replace(dir_path, '')] = dict(path=p, size=os.stat(p).st_size,
                                                                     md5=md5_partial_checksum(p),
                                                                     mtime=os.stat(p).st_mtime)
                if (i == feedback_every or i % feedback_every == 0):
                    sys.stdout.write(f"\r{i}")
        sys.stdout.write(f"\r{i} files scanned")
        sys.stdout.flush()
        print()
        save_to_cache(dir_path, cache_file_path, dir_files)
        dir_files = read_from_cache(dir_path, cache_file_path)

    return dir_files
