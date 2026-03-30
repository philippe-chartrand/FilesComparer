from os.path import basename


def minus (dir_one, dir_two):
    remainder = { k:dir_one[k] for k in dir_one.keys() if k not in dir_two}
    return remainder


def intersection (dir_one, dir_two):
    common = { k:[dir_one[k], dir_two[k]] for k in dir_one.keys() if k in dir_two}
    return common


def modified(common):
    changed_in_dir_one = {}
    changed_in_dir_two = {}
    unchanged = {}
    for k in common.keys():
        first, second = common[k][0], common[k][1]
        if first['md5'] != second['md5']:
            if first['mtime'] > second['mtime']:
                changed_in_dir_one[k] = [first,second]
            elif first['mtime'] < second['mtime']:
                changed_in_dir_two[k] = [first,second]
        else:
            unchanged[k] = [first,second]
    return changed_in_dir_one, changed_in_dir_two, unchanged

def index_by_checksum(items):
    checksums = {}
    for k, v in items.items():
        if not v['md5'] in checksums:
            checksums[v['md5']] = [k]
        else:
            checksums[v['md5']].append(k)
    return checksums

def find_moved(removed, added):
    moved = {}
    added_checksums = index_by_checksum(added)
    removed_checksums = index_by_checksum(removed)
    common_checksums = { k for k in added_checksums.keys() if k in removed_checksums }

    for common_md5 in common_checksums:
        new_file_paths = added_checksums[common_md5]
        for new_file_path in new_file_paths:
            for previous_file_path in removed_checksums[common_md5]:
                if basename(new_file_path) == basename(previous_file_path):
                    src = removed.get(previous_file_path)
                    if src is None:
                        print("find_moved: No such file in removed files: ", previous_file_path)
                        continue
                    dst = added.get(new_file_path)
                    if dst is None:
                        print("find_moved: No such file in added files: ", new_file_path)
                        continue
                    moved[previous_file_path] = (src, dst)
                    del removed[previous_file_path]
                    del added[new_file_path]

    return moved
