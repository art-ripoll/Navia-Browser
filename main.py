import os
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, WebKit2, Gio, Gdk, GLib

class BrowserTab(Gtk.Box):
    def __init__(self, browser, url="https://duckduckgo.com"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.browser = browser

        # Configurar proxy si está definido
        self.webview = WebKit2.WebView()
        proxy_uri = browser.data.get("proxy", "").strip()
        if proxy_uri:
            context = self.webview.get_context()
            settings = context.get_settings()
            # Configuración de proxy para WebKit2GTK
            # Solo funciona si se usa GIO y el entorno soporta la variable
            os.environ["http_proxy"] = proxy_uri
            os.environ["https_proxy"] = proxy_uri
        self.webview.load_uri(url)
        self.pack_start(self.webview, True, True, 0)
        self.show_all()

import json
import threading
import requests


CONFIG_FILE = os.path.expanduser("~/.foxgtk_config.json")
DATA_FILE = os.path.expanduser("~/.foxgtk_data.json")

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"history": [], "bookmarks": [], "homepage": "https://duckduckgo.com", "proxy": ""}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error guardando datos: {e}")

class Navia(Gtk.Window):
    def __init__(self):
        super().__init__(title="Navia Browser")
        # Leer tamaño guardado
        width, height = self.load_window_size()
        # Establecer tamaño mínimo permitido usando geometry hints correctamente
        geometry = Gdk.Geometry()
        geometry.min_width = 400
        geometry.min_height = 300
        self.set_geometry_hints(None, geometry, Gdk.WindowHints.MIN_SIZE)
        self.resize(width, height)
        self.set_icon_name("icons/icon.png")
        self.connect("destroy", self.on_destroy)
        self.connect("configure-event", self.on_configure_event)
        self._last_size = (width, height)

        self.header = Gtk.HeaderBar(show_close_button=True)
        self.set_titlebar(self.header)

        self.toolbar = Gtk.Box(spacing=5)

        self.btn_new_tab = self.make_button("icons/new_tab.png", self.create_tab)
        self.btn_home = self.make_button("icons/home.png", self.go_home)
        self.btn_back = self.make_button("icons/back.png", self.go_back)
        self.btn_forward = self.make_button("icons/forward.png", self.go_forward)
        self.btn_reload = self.make_button("icons/reload.png", self.reload)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Buscar o escribir URL")
        self.entry.set_width_chars(100)
        self.entry.connect("activate", self.load_url)

        self.btn_go = self.make_button("icons/go.svg", self.load_url)
        self.btn_fav = self.make_button("icons/star.png", self.save_favorite)
        self.btn_menu = self.make_button("icons/menu.png", self.open_menu)

        self.header.pack_end(self.btn_menu)

        # Agregar botones a la toolbar
        self.toolbar.pack_start(self.btn_new_tab, False, False, 0)
        for btn in [self.btn_home, self.btn_back, self.btn_forward, self.btn_reload]:
            self.toolbar.pack_start(btn, False, False, 0)

        self.toolbar.pack_start(self.entry, True, True, 0)
        self.toolbar.pack_start(self.btn_go, False, False, 0)
        self.toolbar.pack_start(self.btn_fav, False, False, 0)

        self.header.pack_start(self.toolbar)

        self.notebook = Gtk.Notebook()
        self.add(self.notebook)

        self.data = load_data()
        # Forzar DuckDuckGo como página principal si no está configurada
        if self.data.get("homepage", "") != "https://duckduckgo.com":
            self.data["homepage"] = "https://duckduckgo.com"
            save_data(self.data)
        self.create_tab()

        # Sugerencias como popup
        self.suggest_popup = Gtk.Window(type=Gtk.WindowType.POPUP)
        self.suggest_popup.set_decorated(False)
        self.suggest_popup.set_transient_for(self)
        self.suggest_popup.set_resizable(False)
        self.suggest_popup.set_border_width(0)
        self.suggest_list = Gtk.ListBox()
        self.suggest_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.suggest_popup.add(self.suggest_list)
        self.suggest_popup.set_visible(False)

        self.entry.connect("changed", self.on_entry_changed)
        self.entry.connect("focus-out-event", self.hide_suggestions)
        self.suggest_list.connect("row-activated", self.on_suggestion_clicked)

    def make_button(self, icon_path, callback):
        if os.path.exists(icon_path):
            img = Gtk.Image.new_from_file(icon_path)
            btn = Gtk.Button()
            btn.set_image(img)
        else:
            btn = Gtk.Button(label="+")
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.connect("clicked", callback)
        return btn

    def get_current_webview(self):
        current_tab = self.notebook.get_nth_page(self.notebook.get_current_page())
        return current_tab.webview if current_tab else None

    def load_url(self, widget=None):
        url = self.entry.get_text()
        if not url.startswith("http"):
            url = "https://duckduckgo.com/?q=" + url.replace(" ", "+")
        self.get_current_webview().load_uri(url)
        # Guardar en historial si es diferente al último
        if url:
            history = self.data.get("history", [])
            if not history or history[-1] != url:
                history.append(url)
                # Limitar historial a 100 entradas
                if len(history) > 100:
                    history = history[-100:]
                self.data["history"] = history
                save_data(self.data)

    def go_home(self, widget):
        homepage = self.data.get("homepage", "https://duckduckgo.com")
        self.get_current_webview().load_uri(homepage)

    def go_back(self, widget):
        web = self.get_current_webview()
        if web.can_go_back():
            web.go_back()

    def go_forward(self, widget):
        web = self.get_current_webview()
        if web.can_go_forward():
            web.go_forward()

    def reload(self, widget):
        self.get_current_webview().reload()

    def save_favorite(self, widget):
        web = self.get_current_webview()
        uri = web.get_uri()
        if uri:
            bookmarks = self.data.get("bookmarks", [])
            if uri not in bookmarks:
                bookmarks.append(uri)
                self.data["bookmarks"] = bookmarks
                save_data(self.data)
                print(f"Favorito guardado: {uri}")
            else:
                print("La página ya está en marcadores.")

    def open_menu(self, widget):
        menu = Gtk.Menu()
        items = {
            "Historial": self.show_history,
            "Marcadores": self.show_bookmarks,
            "Guardar como PDF": self.save_pdf,
            "Ajustes": self.open_settings,
            "Acerca de": self.show_about
        }
        for label, action in items.items():
            item = Gtk.MenuItem(label=label)
            item.connect("activate", action)
            menu.append(item)

        menu.show_all()
        menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())

    def show_history(self, widget):
        dialog = Gtk.Dialog(title="Historial", transient_for=self, flags=0)
        dialog.set_default_size(500, 350)
        dialog.add_button("Cerrar", Gtk.ResponseType.CLOSE)
        box = dialog.get_content_area()
        listbox = Gtk.ListBox()
        box.pack_start(listbox, True, True, 0)
        history = self.data.get("history", [])
        if not history:
            listbox.add(Gtk.Label(label="No hay historial."))
        else:
            for url in history:
                row = Gtk.ListBoxRow()
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                lbl = Gtk.Label(label=url, xalign=0)
                hbox.pack_start(lbl, True, True, 0)
                row.add(hbox)
                listbox.add(row)
        listbox.show_all()

        def on_row_activated(listbox, row):
            if row:
                url = row.get_child().get_children()[0].get_text()
                self.load_url_from_history_or_bookmark(url)
                dialog.response(Gtk.ResponseType.CLOSE)
        listbox.connect("row-activated", on_row_activated)
        dialog.run()
        dialog.destroy()

    def show_bookmarks(self, widget):
        dialog = Gtk.Dialog(title="Marcadores", transient_for=self, flags=0)
        dialog.set_default_size(500, 350)
        dialog.add_button("Cerrar", Gtk.ResponseType.CLOSE)
        box = dialog.get_content_area()
        listbox = Gtk.ListBox()
        box.pack_start(listbox, True, True, 0)
        bookmarks = self.data.get("bookmarks", [])
        if not bookmarks:
            listbox.add(Gtk.Label(label="No hay marcadores."))
        else:
            for url in bookmarks:
                row = Gtk.ListBoxRow()
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                lbl = Gtk.Label(label=url, xalign=0)
                hbox.pack_start(lbl, True, True, 0)
                row.add(hbox)
                listbox.add(row)
        listbox.show_all()

        def on_row_activated(listbox, row):
            if row:
                url = row.get_child().get_children()[0].get_text()
                self.load_url_from_history_or_bookmark(url)
                dialog.response(Gtk.ResponseType.CLOSE)
        listbox.connect("row-activated", on_row_activated)
        dialog.run()
        dialog.destroy()

    def load_url_from_history_or_bookmark(self, url):
        self.entry.set_text(url)
        self.load_url()

    def save_pdf(self, widget):
        web = self.get_current_webview()
        dialog = Gtk.FileChooserDialog(
            title="Guardar como PDF",
            action=Gtk.FileChooserAction.SAVE,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                     Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )
        dialog.set_current_name("pagina.pdf")
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()
            web.print_to_pdf(file_path, None, None)
            print(f"Guardado como PDF: {file_path}")

        dialog.destroy()

    def open_settings(self, widget):
        # Diálogo de configuración mejorado con pestañas
        dialog = Gtk.Dialog(title="Ajustes", transient_for=self, flags=0)
        dialog.set_default_size(400, 300)
        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        dialog.add_button("Guardar", Gtk.ResponseType.OK)
        box = dialog.get_content_area()

        notebook = Gtk.Notebook()
        box.pack_start(notebook, True, True, 0)

        # --- Pestaña Página Principal ---
        page_home = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page_home.set_border_width(10)
        lbl_home = Gtk.Label(label="Página principal:")
        entry_home = Gtk.Entry()
        entry_home.set_text(self.data.get("homepage", "https://duckduckgo.com"))
        page_home.pack_start(lbl_home, False, False, 5)
        page_home.pack_start(entry_home, False, False, 5)
        notebook.append_page(page_home, Gtk.Label(label="Página Principal"))

        # --- Pestaña Limpiar Datos ---
        page_data = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page_data.set_border_width(10)
        btn_clear_history = Gtk.Button(label="Limpiar historial")
        btn_clear_history.connect("clicked", self.clear_history)
        btn_clear_bookmarks = Gtk.Button(label="Limpiar marcadores")
        btn_clear_bookmarks.connect("clicked", self.clear_bookmarks)
        page_data.pack_start(btn_clear_history, False, False, 5)
        page_data.pack_start(btn_clear_bookmarks, False, False, 5)
        notebook.append_page(page_data, Gtk.Label(label="Limpiar Datos"))

        # --- Pestaña Proxy ---
        page_proxy = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page_proxy.set_border_width(10)
        lbl_proxy = Gtk.Label(label="Proxy (ej: http://127.0.0.1:8080):")
        entry_proxy = Gtk.Entry()
        entry_proxy.set_text(self.data.get("proxy", ""))
        btn_clear_proxy = Gtk.Button(label="Borrar proxy")
        def clear_proxy(_):
            entry_proxy.set_text("")
        btn_clear_proxy.connect("clicked", clear_proxy)
        page_proxy.pack_start(lbl_proxy, False, False, 5)
        page_proxy.pack_start(entry_proxy, False, False, 5)
        page_proxy.pack_start(btn_clear_proxy, False, False, 5)
        notebook.append_page(page_proxy, Gtk.Label(label="Proxy"))

        box.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.data["homepage"] = entry_home.get_text()
            self.data["proxy"] = entry_proxy.get_text()
            save_data(self.data)
            print("Ajustes guardados")
        dialog.destroy()

    def clear_history(self, widget):
        self.data["history"] = []
        save_data(self.data)
        print("Historial limpiado")

    def clear_bookmarks(self, widget):
        self.data["bookmarks"] = []
        save_data(self.data)
        print("Marcadores limpiados")

    def show_about(self, widget):
        about = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Navia Browser",
        )
        about.format_secondary_text("Navegador ligero usando GTK y WebKit y diseñado con IA.")
        about.run()
        about.destroy()


    def create_tab(self, widget=None, url=None):
        if url is None:
            url = self.data.get("homepage", "https://duckduckgo.com")
        tab = BrowserTab(self, url)

        label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        label = Gtk.Label(label="Nueva Pestaña")
        label.set_width_chars(18)  # Mantener tamaño fijo y más espacio para texto
        btn_close = Gtk.Button(label="✕")
        btn_close.set_relief(Gtk.ReliefStyle.NONE)
        btn_close.set_focus_on_click(False)
        btn_close.set_size_request(16, 16)

        def close_tab(button):
            page_num = self.notebook.page_num(tab)
            if page_num != -1:
                self.notebook.remove_page(page_num)

        btn_close.connect("clicked", close_tab)
        label_box.pack_start(label, False, False, 0)
        label_box.pack_start(btn_close, False, False, 0)
        label_box.show_all()

        self.notebook.append_page(tab, label_box)
        self.notebook.set_current_page(-1)
        tab.webview.connect("notify::title", lambda webview, _: self.update_tab_label(label, webview))
        tab.webview.connect("notify::uri", lambda webview, _: self.update_tab_label(label, webview))
        tab.webview.connect("notify::uri", self.update_url_entry)
        self.show_all()

    def update_tab_label(self, label, webview):
        max_len = 18
        def truncate(text):
            text = text.strip()
            return text[:max_len-3] + '...' if len(text) > max_len else text

        title = webview.get_title()
        if title and title.strip():
            label.set_text(truncate(title))
        else:
            uri = webview.get_uri()
            if uri:
                from urllib.parse import urlparse
                parsed = urlparse(uri)
                host = parsed.netloc or uri
                label.set_text(truncate(host if host else uri))


    def update_url_entry(self, webview, _):
        if webview == self.get_current_webview():
            uri = webview.get_uri()
            if uri:
                self.entry.set_text(uri)
                # Guardar en historial si es diferente al último
                history = self.data.get("history", [])
                if not history or history[-1] != uri:
                    history.append(uri)
                    # Limitar historial a 100 entradas
                    if len(history) > 100:
                        history = history[-100:]
                    self.data["history"] = history
                    save_data(self.data)

    def on_destroy(self, widget):
        # Guardar el último tamaño conocido
        width, height = self._last_size
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"width": width, "height": height}, f)
        except Exception as e:
            print(f"Error guardando tamaño de ventana: {e}")
        Gtk.main_quit()

    def on_configure_event(self, widget, event):
        # Guardar el tamaño cada vez que se cambia
        width = event.width
        height = event.height
        self._last_size = (width, height)
        return False

    def load_window_size(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                width = int(data.get("width", 1024))
                height = int(data.get("height", 720))
                return width, height
        except Exception:
            return 1024, 720

    def on_entry_changed(self, entry, *args):
        # Solo mostrar sugerencias si el entry tiene el foco
        if not entry.is_focus():
            self.hide_suggestions()
            return
        text = entry.get_text().strip()
        if not text:
            self.hide_suggestions()
            return

        def fetch_suggestions():
            try:
                res = requests.get(f"https://duckduckgo.com/ac/?q={requests.utils.quote(text)}", timeout=2)
                data = res.json()
                GLib.idle_add(self.show_suggestions, data)
            except Exception:
                GLib.idle_add(self.hide_suggestions)

        threading.Thread(target=fetch_suggestions, daemon=True).start()

    def show_suggestions(self, data):
        self.suggest_list.foreach(lambda row: self.suggest_list.remove(row))
        if not isinstance(data, list) or not data:
            self.hide_suggestions()
            return
        for item in data:
            phrase = item.get("phrase")
            if phrase:
                row = Gtk.ListBoxRow()
                label = Gtk.Label(label=phrase, xalign=0)
                row.add(label)
                self.suggest_list.add(row)
        self.suggest_list.show_all()
        self.position_suggestions()
        self.suggest_popup.set_visible(True)

    def on_suggestion_clicked(self, listbox, row):
        phrase = row.get_child().get_text()
        self.entry.set_text(phrase)
        self.hide_suggestions()
        self.load_url()

    def hide_suggestions(self, *args):
        self.suggest_popup.set_visible(False)

    def position_suggestions(self):
        # Posiciona el popup justo debajo del Gtk.Entry
        entry_allocation = self.entry.get_allocation()
        window = self.get_window()
        if window:
            origin = window.get_origin()
            x = origin.x + entry_allocation.x
            y = origin.y + entry_allocation.y + entry_allocation.height
            self.suggest_popup.move(x, y)
            self.suggest_popup.set_size_request(entry_allocation.width, -1)

if __name__ == "__main__":
    app = Navia()
    Gtk.main()
