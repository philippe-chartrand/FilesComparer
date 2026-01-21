#!/usr/bin/env python3
import sys


from comparelib.cache import get_files, update_cache, remove_cache
from comparelib.utilities import choose_first, remove_trailing_slash, sum_mb
from comparelib.comparisons import find_moved, intersection, minus, modified
from comparelib.actions import add, cleanup_empty_dirs, move, update, remove, restore

valid_actions = ('help', 'move', 'add', 'update', 'restore', 'remove', 'cleanup')

help_text = """
Compare content of a source and a destination directory, and provide actions to update destination.

actions
=======

help: show this text
move: move files inside destination according to changes in source
add: copy files from source to destination when not found in destination
update: copy files from source to destination when modified in source later than in destination
restore: restore files from destination back to source when modified in destination later than in source
remove: remove files from destination when not found in source
cleanup: remove cache files for source and destination
"""


if __name__ == '__main__':
    print(sys.argv[0], ": Valid actions: ", valid_actions,"\n")
    if len(sys.argv) == 1 or sys.argv[1] == 'help':
        print(help_text);
        sys.exit(1)
        
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
    changed_in_one, changed_in_two, unchanged = modified(common)

    print('unchanged:',len(unchanged), sum_mb(choose_first(unchanged)))
    print('added:', len(added), sum_mb(added))
    print('moved:', len(moved), sum_mb(choose_first(moved)))
    print('changed in source:',len(changed_in_one), sum_mb(choose_first(changed_in_one)))
    print('changed in destination:',len(changed_in_two), sum_mb(choose_first(changed_in_two)))
    print('removed:', len(removed), sum_mb(removed),"\n")

    print('action:', action)
    if action is not None:
        assert action in valid_actions
            
        if action == 'move':
            move(moved, dir_one_path, dir_two_path, dir_two, confirm)
            cleanup_empty_dirs(dir_two_path, confirm)
            if confirm is not None:
                update_cache(dir_two_path, dir_two)
        
        elif action == 'remove':
            remove(removed, dir_two, confirm)
            cleanup_empty_dirs(dir_two_path, confirm)
            if confirm is not None:
                update_cache(dir_two_path, dir_two)
        
        elif action == 'add':
            add(added, dir_one_path, dir_two_path, dir_two, confirm)
            if confirm is not None:
                update_cache(dir_two_path, dir_two)
        
        elif action == 'update':
            update(changed_in_one, dir_two, confirm)
            if confirm is not None:
                update_cache(dir_two_path, dir_two)
        
        elif action == 'restore':
            restore(changed_in_two, dir_one, confirm)
            if confirm is not None:
                update_cache(dir_one_path, dir_one)
            
        elif action == 'cleanup':
            remove_cache(dir_one_path)
            remove_cache(dir_two_path)
            
        if confirm is not None:
            if action == 'restore':
                remove_cache(dir_one_path)
            else:
                if action not in ('add', 'remove', 'move', 'update'):
                    remove_cache(dir_two_path)

