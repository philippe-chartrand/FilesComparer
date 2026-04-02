import datetime
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from comparelib.actions import add_one, update_one, restore_one, move_one, update_dir_two, cleanup_empty_dirs, \
    remove_one
from comparelib.cache import get_files_paginated, update_cache
from comparelib.utilities import sum_mb


class BatchActions(object):
    BATCH_SIZE = 30

    def __init__(self):
        self.source_chunk_count = 0
        self.destination_chunk_count = 0

        self.progressbar = None
        self.simulate_checkbox = None

        self.add_actions = []
        self.update_actions = []
        self.restore_actions = []
        self.move_actions = []
        self.remove_actions = []
        self.pending_action = ''

    def index_source(self):
        pass

    def index_destination(self):
        pass

    def compare(self):
        pass

    def on_simulate_button_toggled(self, button, name):
        pass

    def _update_first_cache_and_compare(self):
        pass

    def _update_second_cache_and_compare(self):
        pass

    def _calc_progressbar_ratio(self, count, dir):
        frac = float(len(dir)) / float(count)
        return frac

    def process_chunk(self, size, files, chunk_count, dir, path):
        if len(files) > 0:
            offset = chunk_count * size
            if len(files) < size:
                    size = len(files)

            chunk = get_files_paginated(path, files, offset, size)
            dir = {**dir, **chunk}

            if len(files) > len(dir):
                chunk_count = chunk_count + 1
            # print(path, len(dir))

        return chunk_count, dir

    def index_source(self, source_files, dir_one, dir_one_path, source_stats):
        size = self.BATCH_SIZE
        source_files_count = len(source_files)

        if source_files_count > 0:
            before = datetime.datetime.now()
            self.source_chunk_count, dir_one = self.process_chunk(size, source_files, self.source_chunk_count,
                                                                       dir_one, dir_one_path)
            duration = datetime.datetime.now() - before
            frac = self._calc_progressbar_ratio(source_files_count, dir_one)
            self.progressbar.set_fraction(frac)
            print(
                f"     source: {len(self.dir_one)}/{source_files_count} {duration.microseconds / 1000:.0f} ms {frac:.0%}")
        else:
            self.pending_action = '' if self.pending_action == 'INDEX_SOURCE' else None

        if source_files_count == len(dir_one) and len(self.dir_two) == 0:
            source_stats.set_text(f"{len(dir_one)} fichiers, {sum_mb(dir_one)}")
            update_cache(dir_one_path, dir_one)
            self.source_files = []
            self.source_chunk_count = 0
            self.index_destination()

    def index_destination(self):
        size = self.BATCH_SIZE
        destination_files_count = len(self.destination_files)
        if destination_files_count > 0:
            before = datetime.datetime.now()
            self.destination_chunk_count, self.dir_two = self.process_chunk(size, self.destination_files,
                                                                            self.destination_chunk_count, self.dir_two,
                                                                            self.dir_two_path)
            duration = datetime.datetime.now() - before
            frac = self._calc_progressbar_ratio(destination_files_count, self.dir_two)
            self.progressbar.set_fraction(frac)
            print(
                f"destination: {len(self.dir_two)}/{destination_files_count} {duration.microseconds / 1000:.0f} ms {frac:.0%}")
        else:
            self.pending_action = '' if self.pending_action == 'INDEX_DESTINATION' else None
        if destination_files_count == len(self.dir_two):
            self.dest_stats.set_text(f"{len(self.dir_two)} fichiers, {sum_mb(self.dir_two)}")
            update_cache(self.dir_two_path, self.dir_two)
            self.destination_files = []
            self.destination_chunk_count = 0
        if destination_files_count == len(self.dir_two):
            self.compare()
            self.on_simulate_button_toggled(self.simulate_checkbox, "1")
            self.simulate_checkbox.set_active(True)

    def add(self):
        if self.simulate_checkbox.get_active():
            return
        if len(self.add_actions) > 0:
            self.progressbar.set_fraction(1.0 / float(len(self.add_actions)))
            d, dest_dir, dir_two, k = self.add_actions.pop()
            add_one(d, dest_dir, dir_two, k)
        else:
            self._update_second_cache_and_compare()
            self.pending_action = ''

    def update(self):
        if self.simulate_checkbox.get_active():
            return
        if len(self.update_actions) > 0:
            self.progressbar.set_fraction(1.0 / float(len(self.update_actions)))
            changed, destination, dir_two, k, source = self.update_actions.pop()
            update_one(changed, destination, dir_two, k, source)
        else:
            self._update_second_cache_and_compare()
            self.pending_action = ''

    def restore(self):
        if self.simulate_checkbox.get_active():
            return
        if len(self.restore_actions) > 0:
            self.progressbar.set_fraction(1.0 / float(len(self.restore_actions)))
            changed, destination, dir_one, k, source = self.restore_actions.pop()
            restore_one(changed, destination, dir_one, k, source)
        else:
            self._update_first_cache_and_compare()
            self.pending_action = ''

    def move(self):
        if self.simulate_checkbox.get_active():
            return
        if len(self.move_actions) > 0:
            self.progressbar.set_fraction(1.0 / float(len(self.move_actions)))
            d2, dest_dir, dir_one_path, dir_two, k, new_path, old_path = self.move_actions.pop()
            move_one(dest_dir, new_path, old_path)
            update_dir_two(d2, dir_one_path, self.dir_two, k, new_path)
        else:
            cleanup_empty_dirs(self.dir_two_path, True)
            self._update_second_cache_and_compare()
            self.pending_action = ''

    def remove(self):
        if self.simulate_checkbox.get_active():
            return
        if len(self.remove_actions) > 0:
            self.progressbar.set_fraction(1.0 / float(len(self.remove_actions)))
            d, dir_two, k = self.remove_actions.pop()
            remove_one(d, dir_two, k)
        else:
            cleanup_empty_dirs(self.dir_two_path, True)
            self._update_second_cache_and_compare()
            self.pending_action = ''