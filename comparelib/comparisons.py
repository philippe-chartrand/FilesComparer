
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


def find_moved(removed, added):
    moved = {}
    for previous_file in removed.copy():
        for new_file in added.copy():
            if previous_file != new_file:
                if previous_file in removed and new_file in added:
                    if removed[previous_file]['md5'] == added[new_file]['md5']:
                        moved[previous_file] = [removed[previous_file], added[new_file]]
                        del removed[previous_file]
                        del added[new_file]
    return moved