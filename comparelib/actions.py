import datetime
import os
import shutil
from pathlib import Path

from comparelib.utilities import make_partial_dest, remove_prefix, make_dest_directory

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


def move(moved, dir_one_path, dir_two_path, dir_two, confirm):
    for k in sorted(moved.keys()):
        d1 = moved[k][0]
        d2 = moved[k][1]
        try:
            old_path = d1['path'].__str__()
            new_path = dir_two_path + '/' + remove_prefix(d2['path'], dir_one_path)
            partial_dest = make_partial_dest(d2['path'], dir_one_path)
            dest_dir = dir_two_path + partial_dest
            if old_path != new_path:
                print(f"mv \"{old_path}\" \"{new_path}\"")
                if confirm is not None:
                    make_dest_directory(dest_dir)
                    shutil.move(old_path, new_path)
                    new_key = "/" + remove_prefix(d2['path'], dir_one_path)
                    dir_two[new_key] = dir_two[k].copy()
                    dir_two[new_key]['path'] = Path(new_path)
                    del dir_two[k]
            else:
                print(f"moving {old_path} on {new_path} is useless.")
        except:
            print("Failed to move", d1['path'].__str__().encode('utf-8', 'surrogateescape'))
            pass


def add(to_add, dir_one_path, dir_two_path, dir_two, confirm):
    for k in sorted(to_add):
        try:
            d = to_add[k]
            partial_dest = make_partial_dest(d['path'], dir_one_path)
            dest_dir = dir_two_path + "/" + partial_dest
            print(f"cp \"{d['path']}\" \"{dest_dir}\"")
            if confirm is not None:
                make_dest_directory(dest_dir)
                shutil.copy2(d['path'], dest_dir)
                dir_two[k] = d.copy()
                dir_two[k]['path'] = Path(f"{dest_dir}/{k}")

        except:
            print("failed to copy", k.encode('utf-8', 'surrogateescape'))
            pass


def update(changed, dir_two, confirm):
    for k in sorted(changed.keys()):
        try:
            source = changed[k][0]['path']
            destination = changed[k][1]['path']
            if changed[k][0]['mtime'] != changed[k][1]['mtime']:
                print(
                    f"# changed: {datetime.datetime.fromtimestamp(changed[k][0]['mtime'])} != {datetime.datetime.fromtimestamp(changed[k][1]['mtime'])}")
            if changed[k][0]['size'] != changed[k][1]['size']:
                print(f"# size: {changed[k][0]['size']} != {changed[k][1]['size']}")
            if changed[k][0]['md5'] != changed[k][1]['md5']:
                print(f"# md5: {changed[k][0]['md5']} != {changed[k][1]['md5']}")
            print(f"cp \"{source}\" \"{destination}\"")
            if confirm is not None:
                make_dest_directory("/".join(destination.parts[0:-1]))
                shutil.copyfile(source, destination)
                dir_two[k]['mtime'] = changed[k][0]['mtime']
                dir_two[k]['md5'] = changed[k][0]['md5']
        except:
            print("failed to update", k.encode('utf-8', 'surrogateescape'))
            pass


def restore(changed, confirm):
    for k in sorted(changed.keys()):
        try:
            source = changed[k][0]['path']
            destination = changed[k][1]['path']
            if changed[k][0]['mtime'] != changed[k][1]['mtime']:
                print(
                    f"# changed: {datetime.datetime.fromtimestamp(changed[k][0]['mtime'])} != {datetime.datetime.fromtimestamp(changed[k][1]['mtime'])}")
            if changed[k][0]['size'] != changed[k][1]['size']:
                print(f"# size: {changed[k][0]['size']} != {changed[k][1]['size']}")
            if changed[k][0]['md5'] != changed[k][1]['md5']:
                print(f"# md5: {changed[k][0]['md5']} != {changed[k][1]['md5']}")
            print(f"cp \"{destination}\" \"{source}\"")
            if confirm is not None:
                make_dest_directory("/".join(source.parts[0:-1]))
                shutil.copyfile(destination, source)
        except:
            print("failed to restore", k.encode('utf-8', 'surrogateescape'))
            pass


def remove(deleted, dir_two, confirm):
    for k in sorted(deleted.keys()):
        d=deleted[k]
        try:
            print(f"rm \"{d['path']}\"")
            if confirm is not None:
                os.unlink(d['path'])
                del dir_two[k]
        except:
            print("Failed to unlink",d['path'].encode('utf-8', 'surrogateescape'))
            pass

