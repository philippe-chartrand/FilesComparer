import datetime
import os
import shutil
from pathlib import Path

from comparelib.utilities import make_partial_dest, remove_prefix, make_dest_directory


def cleanup_empty_dirs(path, execute_now):
    for root, dirs, files in os.walk(path, topdown=False):
        for dir in dirs:
            try:
                if execute_now:
                    os.removedirs(os.path.join(root, dir))
                    print(f"Deleted empty directory: {os.path.join(root, dir)}")
                else:
                    if len(os.listdir(os.path.join(root, dir))) == 0:
                        print(f"Found empty directory: {os.path.join(root, dir)}")
            except OSError:
                pass


def move(moved, dir_one_path, dir_two_path, dir_two, execute_now):
    actions = []
    for k in sorted(moved.keys()):
        try:
            d1, d2, dest_dir, new_path, old_path = move_prepare_one(dir_one_path, dir_two_path, k, moved)
            if execute_now:
                move_one(dest_dir, new_path, old_path)
                update_dir_two(d2, dir_one_path, dir_two, k, new_path)
            else:
                actions.append((d2, dest_dir, dir_one_path, dir_two, k, new_path, old_path))
        except:
            print("Failed to move", d1.__str__().encode('utf-8', 'surrogateescape'))
            pass
    return actions

def move_prepare_one(dir_one_path, dir_two_path, k, moved):
    d1 = moved[k][0]
    d2 = moved[k][1]
    old_path = str(d1['path'])
    new_path = dir_two_path + '/' + remove_prefix(d2['path'], dir_one_path)
    partial_dest = make_partial_dest(d2['path'], dir_one_path)
    dest_dir = dir_two_path + partial_dest
    if old_path != new_path:
        print(f"mv \"{old_path}\" \"{new_path}\"")
    else:
        print(f"moving {old_path} on {new_path} is useless.")
    return d1, d2, dest_dir, new_path, old_path


def move_one(dest_dir, new_path, old_path):
    make_dest_directory(dest_dir)
    shutil.move(old_path, new_path)

def update_dir_two(d2, dir_one_path, dir_two, k, new_path):
    new_key = "/" + remove_prefix(d2['path'], dir_one_path)
    dir_two[new_key] = dir_two[k].copy()
    dir_two[new_key]['path'] = Path(new_path)
    del dir_two[k]


def add(to_add, dir_one_path, dir_two_path, dir_two, execute_now):
    actions = []
    for k in sorted(to_add):
        try:
            dest_dir, d = add_prepare_one(dir_one_path, dir_two_path, k, to_add)
            if execute_now:
                add_one(d, dest_dir, dir_two, k)
            else:
                actions.append((d, dest_dir, dir_two, k))
        except:
            print("failed to copy", k.encode('utf-8', 'surrogateescape'))
            pass
    return actions

def add_one(d, dest_dir, dir_two, k):
    make_dest_directory(dest_dir)
    shutil.copy2(d['path'], dest_dir)
    add_update_cache_one(d, dest_dir, dir_two, k)


def add_update_cache_one(d, dest_dir, dir_two, k):
    dir_two[k] = d.copy()
    dir_two[k]['path'] = Path(f"{dest_dir}/{k}")


def add_prepare_one(dir_one_path, dir_two_path, k, to_add):
    d = to_add[k]
    partial_dest = make_partial_dest(d['path'], dir_one_path)
    dest_dir = dir_two_path + "/" + partial_dest
    print(f"cp \"{d['path']}\" \"{dest_dir}\"")
    return dest_dir, d


def compare_mtimes(mtime1, mtime2):
    if mtime1 > mtime2:
        return ">"
    elif mtime1 == mtime2:
        return "="
    elif mtime1 < mtime2:
        return "<"


def update(changed, dir_two, execute_now):
    actions = []
    for k in sorted(changed.keys()):
        try:
            source, destination = update_prepare_one(changed, k)
            if execute_now:
                update_one(changed, destination, dir_two, k, source)
            else:
                actions.append((changed, destination, dir_two, k, source))
        except:
            print("failed to update", k.encode('utf-8', 'surrogateescape'))
            pass
    return actions

def update_one(changed, destination, dir_two, k, source):
    make_dest_directory("/".join(destination.parts[0:-1]))
    shutil.copyfile(source, destination)
    dir_two[k]['mtime'] = changed[k][0]['mtime']
    dir_two[k]['md5'] = changed[k][0]['md5']


def update_prepare_one(changed, k):
    source = changed[k][0]['path']
    destination = changed[k][1]['path']
    if changed[k][0]['mtime'] != changed[k][1]['mtime']:
        comparator = compare_mtimes(changed[k][0]['mtime'], changed[k][1]['mtime'])
        print(
            f"# changed: {datetime.datetime.fromtimestamp(changed[k][0]['mtime'])} {comparator} {datetime.datetime.fromtimestamp(changed[k][1]['mtime'])}")
    if changed[k][0]['size'] != changed[k][1]['size']:
        print(f"# size: {changed[k][0]['size']} != {changed[k][1]['size']}")
    if changed[k][0]['md5'] != changed[k][1]['md5']:
        print(f"# md5: {changed[k][0]['md5']} != {changed[k][1]['md5']}")
    print(f"cp \"{source}\" \"{destination}\"")
    return source, destination


def restore(changed, dir_one, execute_now):
    actions = []
    for k in sorted(changed.keys()):
        try:
            source, destination = restore_prepare_one(changed, k)
            if execute_now:
                restore_one(changed, destination, dir_one, k, source)
            else:
                actions.append((changed, destination, dir_one, k, source))
        except:
            print("failed to restore", k.encode('utf-8', 'surrogateescape'))
    return actions


def restore_one(changed, destination, dir_one, k, source):
    make_dest_directory("/".join(source.parts[0:-1]))
    shutil.copyfile(destination, source)
    dir_one[k]['mtime'] = changed[k][1]['mtime']
    dir_one[k]['md5'] = changed[k][1]['md5']


def restore_prepare_one(changed, k):
    source = changed[k][0]['path']
    destination = changed[k][1]['path']
    if changed[k][0]['mtime'] != changed[k][1]['mtime']:
        comparator = compare_mtimes(changed[k][0]['mtime'], changed[k][1]['mtime'])
        print(
            f"# changed: {datetime.datetime.fromtimestamp(changed[k][0]['mtime'])} {comparator} {datetime.datetime.fromtimestamp(changed[k][1]['mtime'])}")
    if changed[k][0]['size'] != changed[k][1]['size']:
        print(f"# size: {changed[k][0]['size']} != {changed[k][1]['size']}")
    if changed[k][0]['md5'] != changed[k][1]['md5']:
        print(f"# md5: {changed[k][0]['md5']} != {changed[k][1]['md5']}")
    print(f"cp \"{destination}\" \"{source}\"")
    return source, destination


def remove(deleted, dir_two, execute_now):
    actions = []
    for k in sorted(deleted.keys()):
        d=deleted[k]
        try:
            remove_prepare_one(d)
            if execute_now:
                remove_one(d, dir_two, k)
            else:
                actions.append((d, dir_two, k))
        except:
            print("Failed to unlink",d['path'].encode('utf-8', 'surrogateescape'))
            pass
    return actions


def remove_one(d, dir_two, k):
    os.unlink(d['path'])
    del dir_two[k]


def remove_prepare_one(d):
    print(f"rm \"{d['path']}\"")