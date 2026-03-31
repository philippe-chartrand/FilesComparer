#!/usr/bin/env python3
import datetime
import os
import sys
import gi
from Xlib.Xcursorfont import spider

from comparelib.actions import cleanup_empty_dirs, move, remove, restore, update, add, add_one, update_one, restore_one, \
    move_one, update_dir_two, remove_one
from comparelib.cache import get_files, update_cache, remove_cache, scan_directories, \
    can_read_from_cache, get_files_paginated, update_cache_and_reload
from comparelib.comparisons import minus, find_moved, intersection, modified
from comparelib.utilities import sum_mb, choose_first, remove_trailing_slash, make_path_absolute

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class FileChooserWindow(Gtk.Window):
    TIMEOUT = 3000
    BATCH_SIZE = 90
    def __init__(self):
        super().__init__(title="Comparaison d'ensembles de fichiers")

        set_src_btn = Gtk.Button(label="Choisissez le répertoire source")
        set_src_btn.connect("clicked", self.on_src_btn_clicked)

        self.spinner = Gtk.Spinner()

        self.source = Gtk.Entry()
        self.source.set_text('')
        self.source_stats = Gtk.Entry()
        self.source_stats.set_text('')
        self.source_stats.set_editable(False)
        self.source_files = []
        self.source_chunk_count = 0

        self.destination = Gtk.Entry()
        self.destination.set_text('')
        self.dest_stats = Gtk.Entry()
        self.dest_stats.set_text('')
        self.dest_stats.set_editable(False)
        self.destination_files = []
        self.destination_chunk_count = 0
        set_dest_btn = Gtk.Button(label="Choisissez le répertoire de destination")
        set_dest_btn.connect("clicked", self.on_dest_btn_clicked)

        index_folders_btn = Gtk.Button(label="Indexation des répertoires")
        index_folders_btn.connect("clicked", self.on_index_folders_btn_clicked)
        self.progressbar = Gtk.ProgressBar()
        self.timeout_id = GLib.timeout_add(self.TIMEOUT, self.on_timeout, None)
        self.dir_one_path = ''
        self.dir_two_path = ''
        self.dir_one = {}
        self.dir_two = {}

        self.removed = {}
        self.added = {}

        self.moved = {}

        self.common = {}
        self.changed_in_one = {}
        self.changed_in_two = {}
        self.unchanged = {}

        self.add_actions = []
        self.update_actions = []
        self.restore_actions = []
        self.move_actions = []
        self.remove_actions = []
        self.pending_action = ''

        add_btn, cleanup_btn, help_btn, move_btn, quit_btn, remove_btn, restore_btn, update_btn = self._buttons()

        added_lbl, changed_in_dest_lbl, changed_in_src_lbl, moved_lbl, removed_lbl, unchanged_lbl = self._fields()

        self._layout(add_btn, added_lbl, changed_in_dest_lbl, changed_in_src_lbl, cleanup_btn,
                     help_btn, index_folders_btn, move_btn, moved_lbl, quit_btn, remove_btn, removed_lbl,
                     restore_btn, set_dest_btn, set_src_btn, unchanged_lbl, update_btn)

    def _fields(self):
        unchanged_lbl = Gtk.Label(label="Sans changement")
        added_lbl = Gtk.Label(label="Ajouté")
        moved_lbl = Gtk.Label(label="Déplacé")
        changed_in_src_lbl = Gtk.Label(label="Source modifiée")
        changed_in_dest_lbl = Gtk.Label(label="Destination modifiée")
        removed_lbl = Gtk.Label(label="Supprimé")
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
        return added_lbl, changed_in_dest_lbl, changed_in_src_lbl, moved_lbl, removed_lbl, unchanged_lbl

    def _buttons(self):
        self.simulate_checkbox = Gtk.CheckButton(label="Simulation des actions")
        self.simulate_checkbox.connect("toggled", self.on_simulate_button_toggled, "1")
        self.simulate_checkbox.set_active(True)
        help_btn = Gtk.Button(label='Aide')
        help_btn.connect("clicked", self.on_help_btn_clicked)
        move_btn = Gtk.Button(label='Déplacer')
        move_btn.connect("clicked", self.on_move_btn_clicked)
        add_btn = Gtk.Button(label='Ajouter')
        add_btn.connect("clicked", self.on_add_btn_clicked)
        update_btn = Gtk.Button(label='Mettre à jour')
        update_btn.connect("clicked", self.on_update_btn_clicked)
        restore_btn = Gtk.Button(label='Restaurer')
        restore_btn.connect("clicked", self.on_restore_btn_clicked)
        remove_btn = Gtk.Button(label='Enlever')
        remove_btn.connect("clicked", self.on_remove_btn_clicked)
        cleanup_indices_btn = Gtk.Button(label='Supprimer les indexs')
        cleanup_indices_btn.connect("clicked", self.on_cleanup_indices_btn_clicked)
        quit_btn = Gtk.Button(label='Quitter')
        quit_btn.connect("clicked", Gtk.main_quit)
        return add_btn, cleanup_indices_btn, help_btn, move_btn, quit_btn, remove_btn, restore_btn, update_btn

    def _layout(self, add_btn, added_lbl, changed_in_dest_lbl, changed_in_src_lbl, cleanup_btn,
                help_btn, index_folders_btn, move_btn, moved_lbl, quit_btn, remove_btn, removed_lbl,
                restore_btn, set_dest_btn, set_src_btn, unchanged_lbl, update_btn):
        grid = Gtk.Grid()
        grid.add(set_src_btn)
        grid.attach(self.source, 1, 0, 5, 1)
        grid.attach_next_to(self.source_stats, self.source, Gtk.PositionType.RIGHT, 1, 1)
        grid.attach_next_to(set_dest_btn, set_src_btn, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.destination, set_dest_btn, Gtk.PositionType.RIGHT, 5, 1)
        grid.attach_next_to(self.dest_stats, self.destination, Gtk.PositionType.RIGHT, 1, 1)
        grid.attach_next_to(index_folders_btn, set_dest_btn, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.progressbar, index_folders_btn, Gtk.PositionType.RIGHT, 6, 1)
        grid.attach_next_to(cleanup_btn, index_folders_btn, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.spinner, cleanup_btn, Gtk.PositionType.RIGHT, 1, 1)
        grid.attach_next_to(unchanged_lbl, self.spinner, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.unchanged_stats, unchanged_lbl, Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(added_lbl, unchanged_lbl, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.added_stats, added_lbl, Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(moved_lbl, added_lbl, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.moved_stats, moved_lbl, Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(changed_in_src_lbl, moved_lbl, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.changed_in_src_stats, changed_in_src_lbl, Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(changed_in_dest_lbl, changed_in_src_lbl, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.changed_in_dest_stats, changed_in_dest_lbl, Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(removed_lbl, changed_in_dest_lbl, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(self.removed_stats, removed_lbl, Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(self.simulate_checkbox, removed_lbl, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(help_btn, self.simulate_checkbox, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(move_btn, help_btn, Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(add_btn, move_btn, Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(update_btn, add_btn, Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(restore_btn, update_btn, Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(remove_btn, restore_btn, Gtk.PositionType.RIGHT, 1, 2)
        grid.attach_next_to(quit_btn, remove_btn, Gtk.PositionType.RIGHT, 1, 2)
        self.add(grid)

    def on_simulate_button_toggled(self, button, name):
        if button.get_active():
            print("Actions are simulated")
        else:
            print("Actions are effective")

    def _calc_progressbar_ratio(self, destination_files_count, source_files_count):
        if source_files_count > 0 and destination_files_count == 0:
            numer = len(self.dir_one)
            denom = source_files_count
        elif source_files_count == 0 and destination_files_count > 0:
            numer = len(self.dir_two)
            denom = destination_files_count
        else:
            numer = len(self.dir_one) + len(self.dir_two)
            denom = source_files_count + destination_files_count
        frac = float(numer) / float(denom)
        return frac

    def batch_index(self):
        source_files_count = len(self.source_files)
        destination_files_count = len(self.destination_files)
        size = self.BATCH_SIZE
        if source_files_count > 0:
            before = datetime.datetime.now()
            self.source_chunk_count, self.dir_one = self.process_chunk(size, self.source_files, self.source_chunk_count,
                                                                       self.dir_one, self.dir_one_path)
            duration = datetime.datetime.now() - before
            frac = self._calc_progressbar_ratio(destination_files_count, source_files_count)
            self.progressbar.set_fraction(frac)
            print(
                f"     source: {len(self.dir_one)}/{source_files_count} {duration.microseconds / 1000:.0f} ms {frac:.0%}")
        if destination_files_count > 0:
            before = datetime.datetime.now()
            self.destination_chunk_count, self.dir_two = self.process_chunk(size, self.destination_files,
                                                                            self.destination_chunk_count, self.dir_two,
                                                                            self.dir_two_path)
            duration = datetime.datetime.now() - before
            frac = self._calc_progressbar_ratio(destination_files_count, source_files_count)
            print(
                f"destination: {len(self.dir_two)}/{destination_files_count} {duration.microseconds / 1000:.0f} ms {frac:.0%}\n")
        if source_files_count == len(self.dir_one):
            self.source_stats.set_text(f"{len(self.dir_one)} fichiers, {sum_mb(self.dir_one)}")
            update_cache(self.dir_one_path, self.dir_one)
            self.source_files = []
            self.source_chunk_count = 0
        if destination_files_count == len(self.dir_two):
            self.dest_stats.set_text(f"{len(self.dir_two)} fichiers, {sum_mb(self.dir_two)}")
            update_cache(self.dir_two_path, self.dir_two)
            self.destination_files = []
            self.destination_chunk_count = 0
        if source_files_count == len(self.dir_one) and destination_files_count == len(self.dir_two):
            self.compare()
            self.on_simulate_button_toggled(self.simulate_checkbox, "1")
            self.simulate_checkbox.set_active(True)

    def batch_add(self):
        if self.simulate_checkbox.get_active():
            return
        if len(self.add_actions) > 0:
            self.progressbar.set_fraction(1.0/ float(len(self.add_actions)))
            d, dest_dir, dir_two, k = self.add_actions.pop()
            add_one(d, dest_dir, dir_two, k)
        else:
            self._update_second_cache_and_compare()
            self.pending_action = ''

    def batch_update(self):
        if self.simulate_checkbox.get_active():
            return
        if len(self.update_actions) > 0:
            self.progressbar.set_fraction(1.0/ float(len(self.update_actions)))
            changed, destination, dir_two, k, source = self.update_actions.pop()
            update_one(changed, destination, dir_two, k, source)
        else:
            self._update_second_cache_and_compare()
            self.pending_action = ''

    def batch_restore(self):
        if self.simulate_checkbox.get_active():
            return
        if len(self.restore_actions) > 0:
            self.progressbar.set_fraction(1.0/ float(len(self.restore_actions)))
            changed, destination, dir_one, k, source = self.restore_actions.pop()
            restore_one(changed, destination, dir_one, k, source)
        else:
            self._update_first_cache_and_compare()
            self.pending_action = ''

    def batch_move(self):
        if self.simulate_checkbox.get_active():
            return
        if len(self.move_actions) > 0:
            self.progressbar.set_fraction(1.0/ float(len(self.move_actions)))
            d2, dest_dir, dir_one_path, dir_two, k, new_path, old_path = self.move_actions.pop()
            move_one(dest_dir, new_path, old_path)
            update_dir_two(d2, dir_one_path, self.dir_two, k, new_path)
        else:
            cleanup_empty_dirs(self.dir_two_path, True)
            self._update_second_cache_and_compare()
            self.pending_action = ''

    def batch_remove(self):
        if self.simulate_checkbox.get_active():
            return
        if len(self.remove_actions) > 0:
            self.progressbar.set_fraction(1.0/ float(len(self.remove_actions)))
            d, dir_two, k = self.remove_actions.pop()
            remove_one(d, dir_two, k)
        else:
            cleanup_empty_dirs(self.dir_two_path, True)
            self._update_second_cache_and_compare()
            self.pending_action = ''

    def on_timeout(self, user_data):
        if self.pending_action == '':
            self.spinner.stop()
        if self.pending_action == 'INDEX':
            self.spinner.start()
            self.batch_index()
        elif self.pending_action == 'ADD':
            self.spinner.start()
            self.batch_add()
        elif self.pending_action == 'UPDATE':
            self.spinner.start()
            self.batch_update()
        elif self.pending_action == 'RESTORE':
            self.spinner.start()
            self.batch_restore()
        elif self.pending_action == 'MOVE':
            self.spinner.start()
            self.batch_move()
        elif self.pending_action == 'REMOVE':
            self.spinner.start()
            self.batch_remove()
        else:
            self.progressbar.set_fraction(0.0)
        return True

    def on_help_btn_clicked(self, widget):
        help_text = """
Identifie le nombre et la masse des fichiers communs, ajoutés, déplacés, modifiés (dans la source ou dans la destination) ou absents.

Mode:
-----
L'application peut indiquer les actions qu'elle compte entreprendre sans les effectuer (mode Simulation des actions). 
La sortie se trouve alors sur la console sous forme de script. C'est le comportement par défaut.
Elle peut également exécuter les actions directement. (mode effectif). Dans ce cas les indexs sont mis à jour en conséquence.

Actions:
--------

Choisissez le répertoire (source/destination): Il faut d'abord indiquer quels sont ces répertoires en utilisant les deux premiers boutons ou en passant les chemins via la ligne de commande au moment de l'appel de l'application.

Indexation des répertoires: Analyse des fichiers dans les répertoires (taille, md5, date). Indique le nombre et la masse de fichiers selon l'état.

Supprimer les indexs: Supprimer les informations d'analyse si les répertoires source ou destination  ont changé entre temps.

Déplacer: Déplace des fichiers se trouvant dans la destination pour correspondre à leur position dans la source.

Ajouter: Copier depuis la source les fichiers ne se trouvant pas dans la destination.

Mettre à jour: Mettre à jour depuis la source les fichiers se trouvant dans la destination.

Restaurer: Récupérer vers la source des fichiers modifiés dans la destination.

Enlever: supprimer de la destination des fichiers ne se trouvant plus dans ls source.

Quitter: quitter l'application.
        """

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Comparaison des fichiers entre deux répertoires appelés source et destination.\nSert à s'assurer que la synchronisation entre les deux est complète.",
        )
        dialog.format_secondary_text(
            help_text
        )
        dialog.run()
        print("INFO dialog closed")

        dialog.destroy()

    def on_src_btn_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Choisissez un répertoire source",
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
            title="Choisissez un répertoire destination",
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

    def _chk_print_to_file(self, file_descriptor):
        if self.simulate_checkbox.get_active():
            sys.stdout = file_descriptor

    def _update_first_cache_and_compare(self):
        if not self.simulate_checkbox.get_active():
            self.dir_one = update_cache_and_reload(self.dir_one_path, self.dir_one)
            self.index_source()
            self.compare()

    def _update_second_cache_and_compare(self):
        if not self.simulate_checkbox.get_active():
            self.dir_two = update_cache_and_reload(self.dir_two_path, self.dir_two)
            self.index_destination()
            self.compare()

    def _print_script_location(self, file):
        if self.simulate_checkbox.get_active():
            print(f"script will be in file {file}")

    def on_move_btn_clicked(self, widget):
        if len(self.moved) > 0:
            self._print_script_location("move.sh")
            original_stdout = sys.stdout
            with open('move.sh', 'w') as f:
                self._chk_print_to_file(f)
                actions = move(self.moved, self.dir_one_path, self.dir_two_path, self.dir_two, self.simulate_checkbox)
                self._chk_print_to_file(original_stdout)
            if not self.simulate_checkbox.get_active():
                self.move_actions = actions
                self.pending_action = 'MOVE'

    def on_add_btn_clicked(self, widget):
        if len(self.added) > 0:
            self._print_script_location("add.sh")
            original_stdout = sys.stdout
            with open('add.sh', 'w') as f:
                self._chk_print_to_file(f)
                actions = add(self.added, self.dir_one_path, self.dir_two_path, self.dir_two, False)
                self._chk_print_to_file(original_stdout)
            if not self.simulate_checkbox.get_active():
                self.add_actions = actions
                self.pending_action = 'ADD'

    def on_update_btn_clicked(self, widget):
        if len(self.changed_in_one) > 0:
            self._print_script_location("update.sh")
            original_stdout = sys.stdout
            with open('update.sh', 'w') as f:
                self._chk_print_to_file(f)
                actions = update(self.changed_in_one, self.dir_two, False)
                self._chk_print_to_file(original_stdout)
            if not self.simulate_checkbox.get_active():
                self.update_actions = actions
                self.pending_action = 'UPDATE'

    def on_restore_btn_clicked(self, widget):
        if len(self.changed_in_two) > 0:
            self._print_script_location("restore.sh")
            original_stdout = sys.stdout
            with open('restore.sh', 'w') as f:
                self._chk_print_to_file(f)
                actions = restore(self.changed_in_two, self.dir_one, False)
                self._chk_print_to_file(original_stdout)
            if not self.simulate_checkbox.get_active():
                self.restore_actions = actions
                self.pending_action = 'RESTORE'

    def on_remove_btn_clicked(self, widget):
        if len(self.removed) > 0:
            self._print_script_location("remove.sh")
            original_stdout = sys.stdout
            with open('remove.sh', 'w') as f:
                self._chk_print_to_file(f)
                actions = remove(self.removed, self.dir_two, False)
                self._chk_print_to_file(original_stdout)
            if not self.simulate_checkbox.get_active():
                self.remove_actions = actions
                self.pending_action = 'REMOVE'

    def on_cleanup_indices_btn_clicked(self, widget):
        remove_cache(self.dir_one_path)
        remove_cache(self.dir_two_path)
        self.source_files=[]
        self.destination_files=[]
        self.dir_one = {}
        self.dir_two = {}
        self.cleanup_stats()

    def index(self):
        self.dir_one_path = self.source.get_text()
        self.dir_two_path = self.destination.get_text()
        self.index_source()
        self.index_destination()
        if len(self.dir_one) > 0 and len(self.dir_two) > 0:
            self.compare()

    def index_source(self):
        self.dir_one_path = self.source.get_text()
        if can_read_from_cache(self.dir_one_path):
            self.dir_one = get_files(self.dir_one_path)
            print('dir_one:', len(self.dir_one))
            self.source_stats.set_text(f"{len(self.dir_one)} fichiers, {sum_mb(self.dir_one)}")
        else:
            self.pending_action = 'INDEX'
            self.source_files = scan_directories(self.dir_one_path)
            print('dir_one:', len( self.source_files))
            #self.source_stats.set_text(f"{len(self.source_files)} fichiers")

    def index_destination(self):
        self.dir_two_path = self.destination.get_text()
        if can_read_from_cache(self.dir_two_path):
            self.dir_two = get_files(self.dir_two_path)
            print('dir_two:', len(self.dir_two))
            self.dest_stats.set_text(f"{len(self.dir_two)} fichiers, {sum_mb(self.dir_two)}")
        else:
            self.pending_action = 'INDEX'
            self.destination_files = scan_directories(self.dir_two_path)
            print('dir_two:', len(self.destination_files), "\n")
            #self.dest_stats.set_text(f"{len(self.destination_files)} fichiers")

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

    def compare(self):
        self.removed = minus(self.dir_two, self.dir_one)
        self.added = minus(self.dir_one, self.dir_two)

        self.moved = find_moved(self.removed, self.added)

        self.common = intersection(self.dir_one, self.dir_two)
        self.changed_in_one, self.changed_in_two, self.unchanged = modified(self.common)

        print('unchanged:', len(self.unchanged), sum_mb(choose_first(self.unchanged)))
        self.unchanged_stats.set_text(f"{len(self.unchanged)} fichiers, {sum_mb(choose_first(self.unchanged))}")

        print('added:', len(self.added), sum_mb(self.added))
        self.added_stats.set_text(f"{len(self.added)} fichiers, {sum_mb(self.added)}")

        print('moved:', len(self.moved), sum_mb(choose_first(self.moved)))
        self.moved_stats.set_text(f"{len(self.moved)} fichiers, {sum_mb(choose_first(self.moved))}")

        print('changed in source:', len(self.changed_in_one), sum_mb(choose_first(self.changed_in_one)))
        self.changed_in_src_stats.set_text(f"{len(self.changed_in_one)} fichiers, {sum_mb(choose_first(self.changed_in_one))}")

        print('changed in destination:', len(self.changed_in_two), sum_mb(choose_first(self.changed_in_two)))
        self.changed_in_dest_stats.set_text(f"{len(self.changed_in_two)} fichiers, {sum_mb(choose_first(self.changed_in_two))}")

        print('removed:', len(self.removed), sum_mb(self.removed), "\n")
        self.removed_stats.set_text(f"{len(self.removed)} fichiers, {sum_mb(self.removed)}")

    def cleanup_stats(self):
        self.source_stats.set_text('')
        self.dest_stats.set_text('')
        self.unchanged_stats.set_text('')
        self.added_stats.set_text('')
        self.moved_stats.set_text('')
        self.changed_in_src_stats.set_text('')
        self.changed_in_dest_stats.set_text('')
        self.removed_stats.set_text('')

    def _cleanup_comparisons(self):
        self.removed = {}
        self.added = {}
        self.moved = {}
        self.common = {}
        self.changed_in_one = {}
        self.changed_in_two = {}
        self.unchanged = {}

def cleanup_and_make_path_absolute(field, path):
    path = make_path_absolute(path)
    cleaned = remove_trailing_slash(path)
    field.set_text(cleaned)

if __name__ == '__main__':
    win = FileChooserWindow()
    if len(sys.argv) > 1 and sys.argv[1] is not None:
        cleanup_and_make_path_absolute(win.source,sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] is not None:
        cleanup_and_make_path_absolute(win.destination, sys.argv[2])
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
