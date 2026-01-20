#!/usr/bin/env python3

import sys
import gi

from comparelib.actions import cleanup_empty_dirs, move, remove, restore, update, add
from comparelib.cache import get_files, update_cache, remove_cache
from comparelib.comparisons import minus, find_moved, intersection, modified
from comparelib.utilities import sum_mb, choose_first, remove_trailing_slash

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class FileChooserWindow(Gtk.Window):

    def __init__(self):
        super().__init__(title="Filesets comparer")

        set_src_btn = Gtk.Button(label="Choose Source Folder")
        set_src_btn.connect("clicked", self.on_src_btn_clicked)

        self.source = Gtk.Entry()
        self.source.set_text('')
        self.source_stats = Gtk.Entry()
        self.source_stats.set_text('')
        self.source_stats.set_editable(False)

        self.destination = Gtk.Entry()
        self.destination.set_text('')
        self.dest_stats = Gtk.Entry()
        self.dest_stats.set_text('')
        self.dest_stats.set_editable(False)

        set_dest_btn = Gtk.Button(label="Choose Destination Folder")
        set_dest_btn.connect("clicked", self.on_dest_btn_clicked)

        index_folders_btn = Gtk.Button(label="Index source and\ndestination folders")
        index_folders_btn.connect("clicked", self.on_index_folders_btn_clicked)

        self.dir_one_path = ''
        self.dir_two_path = ''
        self.dir_one = {}
        self.dir_two = {}

        self.removed = {}
        self.added = {}

        self.moved = {}

        self.moved = {}

        self.common = {}
        self.changed_in_one = {}
        self.changed_in_two = {}
        self.unchanged = {}

        self.confirm = None
        simulate = Gtk.CheckButton(label="Simulation")
        simulate.connect("toggled", self.on_simulate_button_toggled, "1")
        simulate.set_active(True)

        help_btn = Gtk.Button(label='help')
        help_btn.connect("clicked", self.on_help_btn_clicked)

        move_btn = Gtk.Button(label='move')
        move_btn.connect("clicked", self.on_move_btn_clicked)

        add_btn = Gtk.Button(label='add')
        add_btn.connect("clicked", self.on_add_btn_clicked)

        update_btn = Gtk.Button(label='update')
        update_btn.connect("clicked", self.on_update_btn_clicked)

        restore_btn = Gtk.Button(label='restore')
        restore_btn.connect("clicked", self.on_restore_btn_clicked)

        remove_btn = Gtk.Button(label='remove')
        remove_btn.connect("clicked", self.on_remove_btn_clicked)

        cleanup_btn = Gtk.Button(label='cleanup')
        cleanup_btn.connect("clicked", self.on_cleanup_btn_clicked)

        quit_btn = Gtk.Button(label='Quit')
        quit_btn.connect("clicked", Gtk.main_quit)

        unchanged_lbl = Gtk.Label(label="unchanged")
        added_lbl = Gtk.Label(label="added")
        moved_lbl = Gtk.Label(label="moved")
        changed_in_src_lbl = Gtk.Label(label="changed in source")
        changed_in_dest_lbl = Gtk.Label(label="changed in destination")
        removed_lbl = Gtk.Label(label="removed")

        self.unchanged_stats = Gtk.Entry()
        self.unchanged_stats.set_text('')
        self.unchanged_stats.set_editable(False)

        self.added_stats = Gtk.Entry()
        self.added_stats.set_text('')
        self.added_stats.set_editable(False)

        self.moved_stats = Gtk.Entry()
        self.moved_stats.set_text('')
        self.moved_stats.set_editable(False)

        self.changed_in_src_stats = Gtk.Entry()
        self.changed_in_src_stats.set_text('')
        self.changed_in_src_stats.set_editable(False)

        self.changed_in_dest_stats = Gtk.Entry()
        self.changed_in_dest_stats.set_text('')
        self.changed_in_dest_stats.set_editable(False)

        self.removed_stats = Gtk.Entry()
        self.removed_stats.set_text('')
        self.removed_stats.set_editable(False)

        grid = Gtk.Grid()
        grid.add(set_src_btn)
        grid.attach(self.source,1, 0, 5, 1)
        grid.attach_next_to(self.source_stats, self.source, Gtk.PositionType.RIGHT, 1, 1)
        grid.attach_next_to(set_dest_btn, set_src_btn, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.destination, set_dest_btn, Gtk.PositionType.RIGHT, 5, 1)
        grid.attach_next_to(self.dest_stats, self.destination, Gtk.PositionType.RIGHT, 1, 1)

        grid.attach_next_to(index_folders_btn,set_dest_btn,Gtk.PositionType.BOTTOM, 1, 2)

        grid.attach_next_to(unchanged_lbl, index_folders_btn,Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.unchanged_stats, unchanged_lbl,Gtk.PositionType.RIGHT, 1, 2)

        grid.attach_next_to(added_lbl, unchanged_lbl, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.added_stats, added_lbl,Gtk.PositionType.RIGHT, 1, 2)

        grid.attach_next_to(moved_lbl, added_lbl, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.moved_stats, moved_lbl,Gtk.PositionType.RIGHT, 1, 2)

        grid.attach_next_to(changed_in_src_lbl, moved_lbl, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.changed_in_src_stats, changed_in_src_lbl,Gtk.PositionType.RIGHT, 1, 2)

        grid.attach_next_to(changed_in_dest_lbl, changed_in_src_lbl, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.changed_in_dest_stats, changed_in_dest_lbl,Gtk.PositionType.RIGHT, 1, 2)

        grid.attach_next_to(removed_lbl, changed_in_dest_lbl,Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.removed_stats, removed_lbl,Gtk.PositionType.RIGHT, 1, 2)

        grid.attach_next_to(simulate, removed_lbl, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(help_btn, simulate, Gtk.PositionType.BOTTOM, 1, 2)

        grid.attach_next_to(move_btn, help_btn,Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(add_btn, move_btn,Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(update_btn, add_btn,Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(restore_btn, update_btn,Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(remove_btn, restore_btn,Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(cleanup_btn, remove_btn,Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(quit_btn, cleanup_btn, Gtk.PositionType.BOTTOM, 1, 2)

        self.add(grid)

    def on_simulate_button_toggled(self, button, name):
        if button.get_active():
            self.confirm = None
            print("Actions are simulated")

        else:
            self.confirm = True
            print("Actions are effective")

    def on_help_btn_clicked(self, widget):
        help_text = """
help: show this text
move: move files inside destination according to changes in source
add: copy files from source to destination when not found in destination
update: copy files from source to destination when modified in source later than in destination
restore: restore files from destination back to source when modified in destination later than in source
remove: remove files from destination when not found in source
cleanup: remove cache files for source and destination
        """

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Compare content of a source and a destination directory, and provide actions to update destination.",
        )
        dialog.format_secondary_text(
            help_text
        )
        dialog.run()
        print("INFO dialog closed")

        dialog.destroy()

    def on_src_btn_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a source folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, "Select", Gtk.ResponseType.OK
        )
        dialog.set_default_size(800, 400)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("Select clicked")
            print("Folder selected: " + dialog.get_filename())
            self.source.set_text(dialog.get_filename())
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")

        dialog.destroy()

    def on_dest_btn_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a destination folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, "Select", Gtk.ResponseType.OK
        )
        dialog.set_default_size(800, 400)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("Select clicked")
            print("Folder selected: " + dialog.get_filename())
            self.destination.set_text(dialog.get_filename())
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")

        dialog.destroy()

    def on_index_folders_btn_clicked(self, widget):
        if self.source.get_text() != '' and self.destination.get_text != '':
            self.index()
            self.compare()

    def on_move_btn_clicked(self, widget):
        move(self.moved, self.dir_one_path, self.dir_two_path, self.dir_two, self.confirm)
        cleanup_empty_dirs(self.dir_two_path, self.confirm)
        if self.confirm is not None:
            update_cache(self.dir_two_path, self.dir_two)
            self.index_destination()

    def on_add_btn_clicked(self, widget):
        add(self.added, self.dir_one_path, self.dir_two_path, self.dir_two, self.confirm)
        if self.confirm is not None:
            update_cache(self.dir_two_path, self.dir_two)
            self.index_destination()

    def on_update_btn_clicked(self, widget):
        update(self.changed_in_one, self.dir_two, self.confirm)
        if self.confirm is not None:
            update_cache(self.dir_two_path, self.dir_two)
            self.index_destination()

    def on_restore_btn_clicked(self, widget):
        restore(self.changed_in_two, self.confirm)
        if self.confirm is not None:
            update_cache(self.dir_one_path, self.dir_one)
            self.index_source()

    def on_cleanup_btn_clicked(self, widget):
        remove_cache(self.dir_one_path)
        remove_cache(self.dir_two_path)
        self.cleanup_stats()


    def on_remove_btn_clicked(self, widget):
        remove(self.removed, self.dir_two, self.confirm)
        cleanup_empty_dirs(self.dir_two_path, self.confirm)
        if self.confirm is not None:
            update_cache(self.dir_two_path, self.dir_two)
            self.index_destination()

    def index(self):
        self.dir_one_path = self.source.get_text()
        self.dir_two_path = self.destination.get_text()
        print(f"indexing {self.source.get_text()} and {self.destination.get_text()}")
        self.index_source()
        self.index_destination()

    def index_source(self):
        self.dir_one_path = self.source.get_text()
        dir_one = get_files(self.dir_one_path)
        print('dir_one:', len(dir_one), sum_mb(dir_one))
        self.source_stats.set_text(f"{len(dir_one)} {sum_mb(dir_one)}")
        self.dir_one = dir_one

    def index_destination(self):
        dir_two = get_files(self.dir_two_path)
        print('dir_two:', len(dir_two), sum_mb(dir_two), "\n")
        self.dest_stats.set_text(f"{len(dir_two)} {sum_mb(dir_two)}")
        self.dir_two = dir_two

    def compare(self):
        self.removed = minus(self.dir_two, self.dir_one)
        self.added = minus(self.dir_one, self.dir_two)

        self.moved = find_moved(self.removed, self.added)

        self.common = intersection(self.dir_one, self.dir_two)
        self.changed_in_one, self.changed_in_two, self.unchanged = modified(self.common)

        print('unchanged:', len(self.unchanged), sum_mb(choose_first(self.unchanged)))
        self.unchanged_stats.set_text(f"{len(self.unchanged)} {sum_mb(choose_first(self.unchanged))}")

        print('added:', len(self.added), sum_mb(self.added))
        self.added_stats.set_text(f"{len(self.added)} {sum_mb(self.added)}")

        print('moved:', len(self.moved), sum_mb(choose_first(self.moved)))
        self.moved_stats.set_text(f"{len(self.moved)} {sum_mb(self.moved)}")

        print('changed in source:', len(self.changed_in_one), sum_mb(choose_first(self.changed_in_one)))
        self.changed_in_src_stats.set_text(f"{len(self.changed_in_one)} {sum_mb(choose_first(self.changed_in_one))}")

        print('changed in destination:', len(self.changed_in_two), sum_mb(choose_first(self.changed_in_two)))
        self.changed_in_dest_stats.set_text(f"{len(self.changed_in_two)} {sum_mb(choose_first(self.changed_in_two))}")

        print('removed:', len(self.removed), sum_mb(self.removed), "\n")
        self.removed_stats.set_text(f"{len(self.removed)} {sum_mb(self.removed)}")

    def cleanup_stats(self):
        self.source_stats.set_text('')
        self.dest_stats.set_text('')
        self.unchanged_stats.set_text('')
        self.added_stats.set_text('')
        self.moved_stats.set_text('')
        self.changed_in_src_stats.set_text('')
        self.changed_in_dest_stats.set_text('')
        self.removed_stats.set_text('')

win = FileChooserWindow()
if sys.argv[1] is not None:
    win.source.set_text(remove_trailing_slash(sys.argv[1]))
if sys.argv[2] is not None:
    win.destination.set_text(remove_trailing_slash(sys.argv[2]))
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()