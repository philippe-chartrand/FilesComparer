#!/usr/bin/env python3
import datetime
import sys
import gi

from comparelib.actions import move, remove, restore, update, add
from comparelib.batch_actions import BatchActions
from comparelib.cache import get_files, remove_cache, scan_directories, \
    can_read_from_cache, update_cache_and_reload
from comparelib.comparisons import minus, find_moved, intersection, modified
from comparelib.utilities import sum_mb, choose_first, remove_trailing_slash, make_path_absolute

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class FileChooserWindow(Gtk.Window):
    TIMEOUT = 1000
    def __init__(self, batch):
        super().__init__()
        self.batch = batch
        self.set_title("Comparaison d'ensembles de fichiers")
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

    def _calc_progressbar_ratio(self, count, dir):
        frac = float(len(dir)) / float(count)
        return frac

    def on_timeout(self, user_data):
        pending_action = self.batch.pending_action
        if pending_action == '':
            self.spinner.stop()

        if pending_action == 'INDEX_SOURCE':
            self.spinner.start()
            print(pending_action)
            frac, self.dir_one, self.source_files, done = self.batch.index_source(self.source_files, self.dir_one, self.dir_one_path, self.source_stats, len(self.dir_two))
            self.progressbar.set_fraction(frac)
            if done:
                self.index_destination()

        elif pending_action == 'INDEX_DESTINATION':
            self.spinner.start()
            print(pending_action)
            frac, self.dir_two, self.destination_files, done = self.batch.index_destination(self.destination_files, self.dir_two, self.dir_two_path, self.dest_stats)
            self.progressbar.set_fraction(frac)
            if done:
                self.batch.pending_action = 'COMPARE'
                self.on_simulate_button_toggled(self.simulate_checkbox, "1")
                self.simulate_checkbox.set_active(True)

        elif pending_action == 'COMPARE':
            print(pending_action)
            self.compare()

        elif pending_action == 'ADD':
            self.spinner.start()
            print(pending_action)
            frac, done, _ = self.batch.add(self.dir_two)
            self.progressbar.set_fraction(frac)
            if done:
                self._update_second_cache_and_compare()


        elif pending_action == 'UPDATE':
            self.spinner.start()
            print(pending_action)
            frac, done, self.dir_two = self.batch.update(self.dir_two)
            self.progressbar.set_fraction(frac)
            if done:
                self._update_second_cache_and_compare()

        elif pending_action == 'RESTORE':
            self.spinner.start()
            print(pending_action)
            frac, done, self.dir_one = self.batch.restore(self.dir_one)
            self.progressbar.set_fraction(frac)
            if done:
                self._update_first_cache_and_compare()

        elif pending_action == 'MOVE':
            self.spinner.start()
            print(pending_action)
            frac, done = self.batch.move(self.dir_two_path)
            self.progressbar.set_fraction(frac)
            if done:
                self._update_second_cache_and_compare()

        elif pending_action == 'REMOVE':
            self.spinner.start()
            print(pending_action)
            frac, done, self.dir_two = self.batch.remove(self.dir_two, self.dir_two_path)
            self.progressbar.set_fraction(frac)
            if done:
                self._update_second_cache_and_compare()

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
        if self.source_stats.get_text() != '' \
            and self.dest_stats.get_text() != '' \
            and len(self.dir_one) > 0 \
            and len(self.dir_two) > 0:
                self.compare()
        elif self.source.get_text() != '':
            self.index_source()

    def _chk_print_to_file(self, file_descriptor):
        if self.simulate_checkbox.get_active():
            sys.stdout = file_descriptor

    def _update_first_cache_and_compare(self):
        if not self.simulate_checkbox.get_active():
            update_cache_and_reload(self.dir_one_path, self.dir_one)
            self.source_stats.set_text(f"{len(self.dir_one)} fichiers, {sum_mb(self.dir_one)}")
            self.batch.pending_action = 'COMPARE'

    def _update_second_cache_and_compare(self):
        if not self.simulate_checkbox.get_active():
            update_cache_and_reload(self.dir_two_path, self.dir_two)
            self.dest_stats.set_text(f"{len(self.dir_two)} fichiers, {sum_mb(self.dir_two)}")
            self.batch.pending_action = 'COMPARE'

    def _print_script_location(self, file):
        if self.simulate_checkbox.get_active():
            print(f"script will be in file {file}")

    def on_move_btn_clicked(self, widget):
        execute = False
        print_to_file = self.simulate_checkbox.get_active()
        if len(self.moved) > 0:
            self._print_script_location("move.sh")
            original_stdout = sys.stdout
            with open('move.sh', 'w') as f:
                self._chk_print_to_file(f)
                actions = move(self.moved, self.dir_one_path, self.dir_two_path, self.dir_two, execute, print_to_file)
            self._chk_print_to_file(original_stdout)
            if not self.simulate_checkbox.get_active():
                self.batch.move_actions = actions
                self.batch.pending_action = 'MOVE'

    def on_add_btn_clicked(self, widget):
        execute = False
        print_to_file = self.simulate_checkbox.get_active()
        if len(self.added) > 0:
            self._print_script_location("add.sh")
            original_stdout = sys.stdout
            with open('add.sh', 'w') as f:
                self._chk_print_to_file(f)
                actions = add(self.added, self.dir_one_path, self.dir_two_path, self.dir_two, execute, print_to_file)
            self._chk_print_to_file(original_stdout)
            if not self.simulate_checkbox.get_active():
                self.batch.add_actions = actions
                self.batch.pending_action = 'ADD'

    def on_update_btn_clicked(self, widget):
        execute = False
        print_to_file = self.simulate_checkbox.get_active()
        if len(self.changed_in_one) > 0:
            self._print_script_location("update.sh")
            original_stdout = sys.stdout
            with open('update.sh', 'w') as f:
                self._chk_print_to_file(f)
                actions = update(self.changed_in_one, self.dir_two,  execute, print_to_file)
            self._chk_print_to_file(original_stdout)
            if not self.simulate_checkbox.get_active():
                self.batch.update_actions = actions
                self.batch.pending_action = 'UPDATE'

    def on_restore_btn_clicked(self, widget):
        execute = False
        print_to_file = self.simulate_checkbox.get_active()
        if len(self.changed_in_two) > 0:
            self._print_script_location("restore.sh")
            original_stdout = sys.stdout
            with open('restore.sh', 'w') as f:
                self._chk_print_to_file(f)
                actions = restore(self.changed_in_two, self.dir_one,  execute, print_to_file)
            self._chk_print_to_file(original_stdout)
            if not self.simulate_checkbox.get_active():
                self.batch.restore_actions = actions
                self.batch.pending_action = 'RESTORE'

    def on_remove_btn_clicked(self, widget):
        execute = False
        print_to_file = self.simulate_checkbox.get_active()
        if len(self.removed) > 0:
            self._print_script_location("remove.sh")
            original_stdout = sys.stdout
            with open('remove.sh', 'w') as f:
                self._chk_print_to_file(f)
                actions = remove(self.removed, self.dir_two,  execute, print_to_file)
            self._chk_print_to_file(original_stdout)
            if not self.simulate_checkbox.get_active():
                self.batch.remove_actions = actions
                self.batch.pending_action = 'REMOVE'

    def on_cleanup_indices_btn_clicked(self, widget):
        source_cache = self.dir_one_path if self.dir_one_path else self.source.get_text()
        remove_cache(source_cache)
        destination_cache = self.dir_two_path if self.dir_two_path else self.destination.get_text()
        remove_cache(destination_cache)
        self.source_files=[]
        self.destination_files=[]
        self.dir_one = {}
        self.dir_two = {}
        self.cleanup_stats()

    def index_source(self):
        self.dir_one_path = self.source.get_text()
        if can_read_from_cache(self.dir_one_path):
            self.dir_one = get_files(self.dir_one_path)
            print('dir_one:', len(self.dir_one))
            self.source_stats.set_text(f"{len(self.dir_one)} fichiers, {sum_mb(self.dir_one)}")
            self.index_destination()
        else:
            self.batch.pending_action = 'INDEX_SOURCE'
            self.source_files = scan_directories(self.dir_one_path)
            print('dir_one:', len( self.source_files))

    def index_destination(self):
        self.dir_two_path = self.destination.get_text()
        if can_read_from_cache(self.dir_two_path):
            self.dir_two = get_files(self.dir_two_path)
            print('dir_two:', len(self.dir_two))
            self.dest_stats.set_text(f"{len(self.dir_two)} fichiers, {sum_mb(self.dir_two)}")
        else:
            self.batch.pending_action = 'INDEX_DESTINATION'
            self.destination_files = scan_directories(self.dir_two_path)
            print('dir_two:', len(self.destination_files), "\n")

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
        self.batch.pending_action = ''

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
    batch = BatchActions()
    win = FileChooserWindow(batch)
    if len(sys.argv) > 1 and sys.argv[1] is not None:
        cleanup_and_make_path_absolute(win.source,sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] is not None:
        cleanup_and_make_path_absolute(win.destination, sys.argv[2])
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
