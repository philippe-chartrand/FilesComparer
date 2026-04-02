import datetime

from comparelib.actions import add_one, update_one, restore_one, move_one, update_dir_two, cleanup_empty_dirs, \
    remove_one, add_update_cache_one
from comparelib.cache import get_files_paginated, update_cache
from comparelib.utilities import sum_mb


class BatchActions(object):
    INDEXING_BATCH_SIZE = 30
    COPY_BATCH_SIZE = 5
    DELETE_BATCH_SIZE = 10

    def __init__(self):
        super().__init__()
        self.source_chunk_count = 0
        self.destination_chunk_count = 0

        self.simulate_checkbox = None

        self.add_actions = []
        self.update_actions = []
        self.restore_actions = []
        self.move_actions = []
        self.remove_actions = []
        self.pending_action = ''

    def _calc_progressbar_ratio(self, count, dir):
        frac = float(len(dir)) / float(count)
        return frac

    def process_chunk(self, files, chunk_count, dir, path):
        if len(files) > 0:
            offset = chunk_count * self.INDEXING_BATCH_SIZE
            if len(files) < self.INDEXING_BATCH_SIZE:
                    size = len(files)

            chunk = get_files_paginated(path, files, offset, self.INDEXING_BATCH_SIZE)
            dir = {**dir, **chunk}

            if len(files) > len(dir):
                chunk_count = chunk_count + 1
            # print(path, len(dir))

        return chunk_count, dir

    def index_source(self, source_files, dir_one, dir_one_path, source_stats, len_dir_two):
        source_files_count = len(source_files)
        frac = 0.0
        done = False
        if source_files_count > 0:
            before = datetime.datetime.now()
            self.source_chunk_count, dir_one = self.process_chunk(source_files, self.source_chunk_count,
                                                                  dir_one, dir_one_path)
            duration = datetime.datetime.now() - before
            frac = self._calc_progressbar_ratio(source_files_count, dir_one)
            print(
                f"     source: {len(dir_one)}/{source_files_count} {duration.microseconds / 1000:.0f} ms {frac:.0%}")
        else:
            self.pending_action = '' if self.pending_action == 'INDEX_SOURCE' else None

        if source_files_count == len(dir_one) and len_dir_two == 0:
            source_stats.set_text(f"{len(dir_one)} fichiers, {sum_mb(dir_one)}")
            update_cache(dir_one_path, dir_one)
            source_files = []
            self.source_chunk_count = 0
            self.pending_action = 'INDEX_DESTINATION'
            done = True
        return frac, dir_one, source_files, done

    def index_destination(self, destination_files, dir_two, dir_two_path, dest_stats):
        frac = 0.0
        done = False
        destination_files_count = len(destination_files)
        if destination_files_count > 0:
            before = datetime.datetime.now()
            self.destination_chunk_count, dir_two = self.process_chunk(destination_files,
                                                                       self.destination_chunk_count, dir_two,
                                                                       dir_two_path)
            duration = datetime.datetime.now() - before
            frac = self._calc_progressbar_ratio(destination_files_count, dir_two)
            print(
                f"destination: {len(dir_two)}/{destination_files_count} {duration.microseconds / 1000:.0f} ms {frac:.0%}")
        else:
            self.pending_action = '' if self.pending_action == 'INDEX_DESTINATION' else None
        if destination_files_count == len(dir_two):
            dest_stats.set_text(f"{len(dir_two)} fichiers, {sum_mb(dir_two)}")
            update_cache(dir_two_path, dir_two)
            destination_files = []
            self.destination_chunk_count = 0
            done = True
        return frac, dir_two, destination_files, done

    def add(self, dir_two):
        frac = 0.0
        done = False
        for i in range(self.COPY_BATCH_SIZE):
            if len(self.add_actions) > 0:
                frac = (float(i+1) / float(len(self.add_actions)))
                d, dest_dir, dir_two, k = self.add_actions.pop()
                print(k)
                add_one(d, dest_dir, dir_two, k)
                dir_two = add_update_cache_one(d, dest_dir, dir_two, k)
            else:
                self.pending_action = ''
                done = True
        return frac, done, dir_two

    def update(self, dir_two):
        frac = 0.0
        done = False
        for i in range(self.COPY_BATCH_SIZE):
            if len(self.update_actions) > 0:
                frac = (float(i+1) / float(len(self.update_actions)))
                changed, destination, dir_two, k, source = self.update_actions.pop()
                print(k)
                update_one(changed, destination, dir_two, k, source)
            else:
                self.pending_action = ''
                done = True
        return frac, done, dir_two

    def restore(self, dir_one):
        frac = 0.0
        done = False
        for i in range(self.COPY_BATCH_SIZE):
            if len(self.restore_actions) > 0:
                frac = (float(i+1) / float(len(self.restore_actions)))
                changed, destination, dir_one, k, source = self.restore_actions.pop()
                print(k)
                restore_one(changed, destination, dir_one, k, source)
            else:
                self.pending_action = ''
                done = True
        return frac, done, dir_one

    def move(self, dir_two_path):
        frac = 0.0
        done = False
        for i in range(self.COPY_BATCH_SIZE):
            if len(self.move_actions) > 0:
                frac = (float(i+1) / float(len(self.move_actions)))
                d2, dest_dir, dir_one_path, dir_two, k, new_path, old_path = self.move_actions.pop()
                print(k)
                move_one(dest_dir, new_path, old_path)
                update_dir_two(d2, dir_one_path, dir_two, k, new_path)
            else:
                cleanup_empty_dirs(dir_two_path, True)
                self.pending_action = ''
                done = True
        return frac, done

    def remove(self, dir_two, dir_two_path):
        frac = 0.0
        done = False
        for i in range(self.DELETE_BATCH_SIZE):
            if len(self.remove_actions) > 0:
                frac = (float(i+1) / float(len(self.remove_actions)))
                d, dir_two, k = self.remove_actions.pop()
                print(k)
                remove_one(d, dir_two, k)
            else:
                cleanup_empty_dirs(dir_two_path, True)
                self.pending_action = ''
                done = True
        return frac, done, dir_two