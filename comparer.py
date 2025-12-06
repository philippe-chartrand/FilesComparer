#!/usr/bin/env python3
from pathlib import Path
import sys
import os
import shutil
import hashlib
import datetime, time
from json import JSONDecoder, JSONEncoder, dump, load

valid_actions = ('move', 'add', 'update', 'remove', 'cleanup')


def remove_trailing_slash(str):
    return str[0:-1] if str.endswith('/') else str
    

def md5_checksum(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def md5_partial_checksum(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        hasher.update(f.read(262144))
    return hasher.hexdigest()


def calc_cache_file_path(dir_path):
    path_hash=hashlib.md5(dir_path.encode()).hexdigest()
    cache_file_path=Path(path_hash)
    return cache_file_path


def is_cache_stale(cache_file_path):    
    ctime = datetime.datetime.fromtimestamp(os.stat(cache_file_path).st_ctime)
    now = datetime.datetime.now()
    age = now - ctime
    if age.seconds > 3600:
        print(f"Warning: cache {cache_file_path} is {age.seconds / 60} minutes old")
        return True
    return False
        
    
def read_from_cache(dir_path, cache_file_path):
    dir_files = {}
    print(f"Reading {dir_path} infos from cache {cache_file_path}")
    with open(cache_file_path, 'r', encoding='utf-8') as f:
        dir_files = {
        	Path(k) : dict(path=Path(v['path']),size=v['size'],md5=v['md5'])  for k,v in JSONDecoder().decode(load(f)).items()
        }   
    return dir_files


def save_to_cache(dir_path, cache_file_path, dir_files):
        print(f"Saving {dir_path} infos to cache {cache_file_path}")
        with open(cache_file_path, 'w', encoding='utf-8') as f:
            serialized = {str(k) : dict(path=str(v['path']),size=v['size'],md5=v['md5']) for k, v in dir_files.items()}
            dump(JSONEncoder().encode(serialized), f, ensure_ascii=False, indent=4)
 
  
def remove_cache(dir_path):
    cache_file_path = calc_cache_file_path(dir_path)
    print(f"Removing cache infos {cache_file_path} for {dir_path}")
    os.unlink(cache_file_path)
    

def get_files(dir_path):
    cache_file_path = calc_cache_file_path(dir_path)
    dir_files = {}
    feedback_every = 100
    if cache_file_path.is_file() and not is_cache_stale(cache_file_path):
        dir_files = read_from_cache(dir_path, cache_file_path)
    else:
         print(f"Scanning all files in {dir_path} for infos...")   
         for i,p in enumerate(Path(dir_path).rglob("*.*")):
            if p.is_file() and not 'listes' in p.parts:
                dir_files[os.fspath(p).replace(dir_path, '')] = dict(path=p, size=os.stat(p).st_size, md5=md5_partial_checksum(p))
                if (i == feedback_every or i % feedback_every == 0):
                     sys.stdout.write(f"\r{i}")
         sys.stdout.write(f"\r{i} files scanned")       
         sys.stdout.flush()
         print()
         save_to_cache(dir_path, cache_file_path, dir_files)
         dir_files = read_from_cache(dir_path, cache_file_path)
        
    return dir_files


def minus (dir_one, dir_two):
    remainder = { k:dir_one[k] for k in dir_one.keys() if k not in dir_two}
    return remainder


def intersection (dir_one, dir_two):
    common = { k:[dir_one[k], dir_two[k]] for k in dir_one.keys() if k in dir_two}
    return common


def modified(common):
    changed = {}
    unchanged = {}
    for k in common.keys():
        first, second = common[k][0], common[k][1]
        if first['md5'] != second['md5']: #        if first['size'] != second['size']:
            changed[k] = [first,second]
        else:
            unchanged[k] = [first,second]
    return changed, unchanged


def remove(deleted,confirm):
    for k in sorted(deleted.keys()):
        d=deleted[k]
        try:
            print(f"rm \"{d['path']}\"")
            if confirm is not None:
                os.unlink(d['path'])
        except:
            print("Failed to unlink",d['path'].encode('utf-8', 'surrogateescape'))
            pass


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


def cleanup_empty_dirs(path, confirm):
    for root, dirs, files in os.walk(path, topdown=False):
        for dir in dirs:
            try:
                if confirm is not None:
                    os.removedirs(os.path.join(root, dir))
                    print(f"Deleted empty directory: {os.path.join(root, dir)}")
                else:
                    if len(os.listdir(os.path.join(root, dir))) == 0:
                        print(f"Found empty directory: {os.path.join(root, dir)}")
            except OSError:
                pass


def move(moved, dir_one_path, dir_two_path, confirm):
    for k in sorted(moved.keys()):
        d1 = moved[k][0]
        d2 = moved[k][1]
        try:
            old_path = d1['path'].__str__()
            new_path = dir_two_path + '/' + remove_prefix(d2['path'], dir_one_path)
            partial_dest = make_partial_dest(d2['path'], dir_one_path)
            dest_dir = dir_two_path + partial_dest
            print(f"mv \"{old_path}\" \"{new_path}\"")
            if confirm is not None:
                make_dest_directory(dest_dir)
                shutil.move(old_path, new_path)

        except:
            print("Failed to move",d1['path'].__str__().encode('utf-8', 'surrogateescape'))
            pass


def make_partial_dest(posix_path, dir_path):
    partial = "/".join(posix_path.parts[0:-1])
    return partial.removeprefix('/' + dir_path)


def add(to_add, dir_one_path, dir_two_path, confirm):
    for k in sorted(to_add):
        try:
            d=to_add[k]
            partial_dest = make_partial_dest(d['path'], dir_one_path)
            dest_dir  = dir_two_path + "/" + partial_dest
            print(f"cp \"{d['path']}\" \"{dest_dir}\"")
            if confirm is not None:
                make_dest_directory(dest_dir)
                shutil.copy2(d['path'], dest_dir)

        except:
            print("failed to copy", k.encode('utf-8', 'surrogateescape'))
            pass


def update(changed, confirm):
    for k in sorted(changed.keys()):
        try:
            source = changed[k][0]['path']
            destination = changed[k][1]['path']
            if  changed[k][0]['size'] != changed[k][1]['size']:
                print(f"# size changed: {changed[k][0]['size']} -> {changed[k][1]['size']}")
            if  changed[k][0]['md5'] != changed[k][1]['md5']:
                print(f"# md5 changed: {changed[k][0]['md5']} -> {changed[k][1]['md5']}")
            print(f"cp \"{source}\" \"{destination}\"")
            if confirm is not None:
                make_dest_directory("/".join(destination.parts[0:-1]))
                shutil.copyfile(source,destination)
        except:
            print("failed to update", d[0].encode('utf-8', 'surrogateescape'))
            pass


def choose_first(dual_list):
    return {k:v[0] for k,v in dual_list.items()}


def sum_bytes(data):
    return sum(d['size'] for d in data.values())


def sum_mb(data):
    return f"{sum_bytes(data)/1048576:,.0f} Mb"


def find_moved(removed, added):
    moved = {}
    for previous_file in removed.copy():
        for new_file in added.copy():
            if previous_file in removed and new_file in added:
                if removed[previous_file]['md5'] == added[new_file]['md5']:
                    moved[previous_file] = [removed[previous_file], added[new_file]]
                    del removed[previous_file]
                    del added[new_file]
    return moved


if __name__ == '__main__':
    print('Valid actions: ', valid_actions,"\n")
    dir_one_path = remove_trailing_slash(sys.argv[1])
    dir_two_path = remove_trailing_slash(sys.argv[2])
    action = sys.argv[3] if len(sys.argv)> 3 else None
    confirm = sys.argv[4] if len(sys.argv)> 4 else None

    dir_one = get_files(dir_one_path)
    print('dir_one:', len(dir_one), sum_mb(dir_one))
    dir_two = get_files(dir_two_path)
    print('dir_two:', len(dir_two), sum_mb(dir_two),"\n")

    removed = minus(dir_two, dir_one)
    added = minus(dir_one, dir_two)
    moved = find_moved(removed, added)

    common = intersection(dir_one, dir_two)
    changed, unchanged = modified(common)

    print('unchanged:',len(unchanged), sum_mb(choose_first(unchanged)))
    print('added:', len(added), sum_mb(added))
    print('moved:', len(moved), sum_mb(choose_first(moved)))
    print('modified:',len(changed), sum_mb(choose_first(changed)))
    print('removed:', len(removed), sum_mb(removed),"\n")

    print('action:', action)
    if action is not None:
        assert action in valid_actions
        if action == 'move':
            move(moved, dir_one_path, dir_two_path, confirm)
            cleanup_empty_dirs(dir_two_path, confirm)	
        
        elif action == 'remove':
            remove(removed, confirm)
            cleanup_empty_dirs(dir_two_path, confirm)	
        
        elif action == 'add':
            add(added, dir_one_path, dir_two_path, confirm)
        
        elif action == 'update':
            update(changed, confirm)
        
        elif action == 'cleanup':
            remove_cache(dir_one_path)
            remove_cache(dir_two_path)
            
        if confirm is not None:
            remove_cache(dir_two_path)
