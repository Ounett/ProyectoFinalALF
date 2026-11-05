"""Interfaz gráfica COMPLEMENTARIA. No sustituye la CLI obligatoria.
"""
from __future__ import annotations
import base64
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from .core import compile_regex, format_machine, grouped_alphabet, ordered_nfa_edges
from .diagram import dfa_dot, nfa_dot, png_bytes

NAVY = '#19334c'
TEAL = '#087e8b'
LIGHT = '#f3f6f9'
TEXT = '#203246'
MUTED = '#65768b'
BORDER = '#d4dee7'


class ConverterApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=0)
        self.master = master
        master.title('ER-AFD | Convertidor de expresiones regulares')
        master.geometry('1160x790')
        master.minsize(890, 610)
        master.configure(bg=LIGHT)
        self.pack(fill='both', expand=True)
        self._style()
        self.er = tk.StringVar(value='(a|b)*abb')
        self.chain = tk.StringVar(value='aabb')
        self.machine = None
        self.current_dot = ''
        self.current_kind = 'AFD'
        self.image_ref = None
        self.fit_diagram = True
        self.result_text = ''
        self.status = tk.StringVar(value='Ingrese la expresión regular y una cadena para comenzar.')
        self._build()

    def _style(self):
        style = ttk.Style(self.master)
        style.theme_use('clam')
        style.configure('Root.TFrame', background=LIGHT)
        style.configure('White.TFrame', background='white')
        style.configure('Heading.TLabel', background=NAVY, foreground='white', font=('DejaVu Sans', 21, 'bold'))
        style.configure('Subheading.TLabel', background=NAVY, foreground='#d5e6ef', font=('DejaVu Sans', 10))
        style.configure('Field.TLabel', background='white', foreground=TEXT, font=('DejaVu Sans', 10, 'bold'))
        style.configure('Info.TLabel', background=LIGHT, foreground=MUTED, font=('DejaVu Sans', 10))
        style.configure('Action.TButton', font=('DejaVu Sans', 10, 'bold'), padding=(13, 10), foreground='white', background=TEAL, borderwidth=0)
        style.map('Action.TButton', background=[('active', '#056672')])
        style.configure('Secondary.TButton', font=('DejaVu Sans', 9), padding=(11, 9))
        style.configure('App.TNotebook', background=LIGHT, tabmargins=(0, 8, 0, 0))
        style.configure('App.TNotebook.Tab', padding=(17, 11), font=('DejaVu Sans', 10))
        style.configure('Treeview', background='white', fieldbackground='white', foreground=TEXT,
                        rowheight=27, font=('DejaVu Sans', 10))
        style.configure('Treeview.Heading', font=('DejaVu Sans', 10, 'bold'), background='#e8f0f5', foreground=NAVY)
        style.map('Treeview', background=[('selected', '#d4e9ed')], foreground=[('selected', NAVY)])

    def _build(self):
        top = tk.Frame(self, bg=NAVY, height=112)
        top.pack(fill='x')
        top.pack_propagate(False)
        ttk.Label(top, text='ER-AFD', style='Heading.TLabel').pack(anchor='w', padx=26, pady=(19, 2))
        ttk.Label(top, text='Conversión de ER a AFND y AFD  |  Complemento gráfico académico', style='Subheading.TLabel').pack(anchor='w', padx=27)
        controls = ttk.Frame(self, style='White.TFrame', padding=(24, 17))
        controls.pack(fill='x', padx=20, pady=(15, 5))
        controls.columnconfigure(0, weight=3)
        controls.columnconfigure(1, weight=2)
        ttk.Label(controls, text='Expresión regular', style='Field.TLabel').grid(row=0, column=0, sticky='w', padx=(0, 16))
        ttk.Label(controls, text='Cadena para evaluar (puede ser vacía)', style='Field.TLabel').grid(row=0, column=1, sticky='w')
        er_entry = ttk.Entry(controls, textvariable=self.er, font=('DejaVu Sans Mono', 12))
        er_entry.grid(row=1, column=0, sticky='ew', padx=(0, 16), pady=(8, 13), ipady=7)
        ttk.Entry(controls, textvariable=self.chain, font=('DejaVu Sans Mono', 12)).grid(row=1, column=1, sticky='ew', pady=(8, 13), ipady=7)
        row = ttk.Frame(controls, style='White.TFrame')
        row.grid(row=2, column=0, columnspan=2, sticky='w')
        ttk.Button(row, text='Convertir y evaluar', style='Action.TButton', command=self.evaluate).pack(side='left', padx=(0, 10))
        ttk.Button(row, text='Cargar ejemplo', style='Secondary.TButton', command=self.example).pack(side='left', padx=(0, 10))
        ttk.Button(row, text='Guardar resultado .txt', style='Secondary.TButton', command=self.save_result).pack(side='left')
        er_entry.focus_set()
        self.master.bind('<Control-Return>', lambda _event: self.evaluate())
        self.master.bind('<F5>', lambda _event: self.evaluate())
        statusline = ttk.Frame(self, style='Root.TFrame')
        statusline.pack(fill='x', padx=25, pady=(4, 0))
        ttk.Label(statusline, textvariable=self.status, style='Info.TLabel', wraplength=1000).pack(anchor='w')
        self.tabs = ttk.Notebook(self, style='App.TNotebook')
        self.tabs.pack(fill='both', expand=True, padx=20, pady=(7, 17))
        self.tab_result = ttk.Frame(self.tabs, style='White.TFrame', padding=15)
        self.tab_nfa = ttk.Frame(self.tabs, style='White.TFrame', padding=15)
        self.tab_dfa = ttk.Frame(self.tabs, style='White.TFrame', padding=15)
        self.tab_graph = ttk.Frame(self.tabs, style='White.TFrame', padding=12)
        self.tab_help = ttk.Frame(self.tabs, style='White.TFrame', padding=15)
        for widget, name in [(self.tab_result, 'Evaluación'), (self.tab_nfa, 'Tabla AFND'),
                             (self.tab_dfa, 'Tabla AFD'), (self.tab_graph, 'Diagramas'), (self.tab_help, 'Ayuda')]:
            self.tabs.add(widget, text=name)
        self.result_view = self._scroll_text(self.tab_result)
        self.nfa_table = self._table(self.tab_nfa)
        self.dfa_table = self._table(self.tab_dfa)
        self._graph_panel()
        help_view = self._scroll_text(self.tab_help)
        self._put(help_view, 'ER-AFD | GUÍA RÁPIDA\n\n'
                  '1. Ingresa la expresión regular, por ejemplo (a|b)*abb.\n'
                  '2. Ingresa la cadena a evaluar, por ejemplo aabb.\n'
                  '3. Haz clic en Convertir y evaluar, o presiona F5.\n'
                  '4. Consulta la evaluación, las transiciones y los diagramas.\n'
                  '5. Para guardar diagramas, usa las opciones de la pestaña Diagramas.\n\n'
                  'Operadores: concatenación, |, *, (), ., ε, [abc], [^abc], [a-z].\n'
                  'Escapes especiales: \\N (dígitos), \\h41 (ASCII hexadecimal), \\A (mayúsculas), '
                  '\\a (minúsculas), \\z (letras).\n\n'
                  'Reconocimiento ASCII 0-127. Las cadenas se comparan completas.\n'
                  'Graphviz (dot) es opcional y solo necesario para imágenes PNG.\n'
                  'En Linux Mint: sudo apt install python3-tk graphviz\n\n'
                  'IMPORTANTE: la versión evaluable obligatoria sigue siendo ./er-afd <ER> <cadena>.\n'
                  'La interfaz gráfica no interviene en el código de salida requerido (1 o 0).')
        self._put(self.result_view, 'Convertidor listo. Usa Convertir y evaluar para iniciar.\n\n'
                  'Ejemplo: expresión (a|b)*abb y cadena aabb.')

    def _scroll_text(self, parent):
        frame = ttk.Frame(parent, style='White.TFrame')
        frame.pack(fill='both', expand=True)
        frame.rowconfigure(0, weight=1); frame.columnconfigure(0, weight=1)
        viewer = tk.Text(frame, bg='#ffffff', fg=TEXT, font=('DejaVu Sans Mono', 10),
                         wrap='none', relief='flat', padx=14, pady=12, state='disabled')
        viewer.grid(row=0, column=0, sticky='nsew')
        y = ttk.Scrollbar(frame, command=viewer.yview)
        x = ttk.Scrollbar(frame, orient='horizontal', command=viewer.xview)
        y.grid(row=0, column=1, sticky='ns'); x.grid(row=1, column=0, sticky='ew')
        viewer.configure(yscrollcommand=y.set, xscrollcommand=x.set)
        return viewer

    @staticmethod
    def _put(widget, text):
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', text)
        widget.configure(state='disabled')

    def _table(self, parent):
        panel = ttk.Frame(parent, style='White.TFrame')
        panel.pack(fill='both', expand=True)
        panel.columnconfigure(0, weight=1); panel.rowconfigure(0, weight=1)
        columns = ('actual', 'symbol', 'target')
        tree = ttk.Treeview(panel, columns=columns, show='headings')
        for column, title, width in [('actual', 'Estado actual', 210), ('symbol', 'Símbolo o clase', 340), ('target', 'Estado destino', 350)]:
            tree.heading(column, text=title)
            tree.column(column, anchor='w', width=width, stretch=True)
        tree.grid(row=0, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(panel, command=tree.yview)
        scroll.grid(row=0, column=1, sticky='ns')
        tree.configure(yscrollcommand=scroll.set)
        return tree

    def _graph_panel(self):
        bar = ttk.Frame(self.tab_graph, style='White.TFrame')
        bar.pack(fill='x', pady=(0, 9))
        ttk.Button(bar, text='Mostrar AFND', style='Secondary.TButton', command=lambda: self.show_graph('AFND')).pack(side='left', padx=(0, 8))
        ttk.Button(bar, text='Mostrar AFD', style='Secondary.TButton', command=lambda: self.show_graph('AFD')).pack(side='left', padx=(0, 8))
        ttk.Button(bar, text='Ajustar ancho / Tamaño real', style='Secondary.TButton', command=self.toggle_fit).pack(side='left', padx=(0, 8))
        ttk.Button(bar, text='Exportar DOT', style='Secondary.TButton', command=lambda: self.export_graph(False)).pack(side='left', padx=(0, 8))
        ttk.Button(bar, text='Exportar PNG', style='Secondary.TButton', command=lambda: self.export_graph(True)).pack(side='left')
        self.graph_note = tk.StringVar(value='Genera un autómata para mostrar su diagrama.')
        ttk.Label(self.tab_graph, textvariable=self.graph_note, style='Field.TLabel').pack(anchor='w', pady=(0, 8))
        holder = ttk.Frame(self.tab_graph, style='White.TFrame')
        holder.pack(fill='both', expand=True)
        holder.rowconfigure(0, weight=1); holder.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(holder, bg='white', highlightthickness=1, highlightbackground=BORDER)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        ys = ttk.Scrollbar(holder, command=self.canvas.yview)
        xs = ttk.Scrollbar(holder, orient='horizontal', command=self.canvas.xview)
        ys.grid(row=0, column=1, sticky='ns'); xs.grid(row=1, column=0, sticky='ew')
        self.canvas.configure(xscrollcommand=xs.set, yscrollcommand=ys.set)

    def example(self):
        self.er.set(r'([a-z]|\N)*[A-Z]')
        self.chain.set('abc37Z')
        self.evaluate()

    def evaluate(self):
        expression, chain = self.er.get(), self.chain.get()
        try:
            if not chain.isascii():
                raise ValueError('La cadena solo puede contener caracteres ASCII.')
            nfa, dfa = compile_regex(expression)
            accepted, steps = dfa.trace(chain)
            self.machine = (nfa, dfa)
            label = 'Cadena aceptada' if accepted else 'Cadena rechazada'
            trace = '\n'.join(steps) if steps else '(Cadena vacía: se comprueba si Q0 es final)'
            self.result_text = ('ER: ' + expression + '\nCADENA: ' + repr(chain) + '\n\n'
                                + format_machine(nfa, dfa) + '\n\nRECORRIDO DEL AFD\n'
                                + trace + '\n' + label + '\nCódigo de retorno CLI: '
                                + str(1 if accepted else 0) + '\n')
            self._put(self.result_view, self.result_text)
            self._fill_tables(nfa, dfa)
            self.status.set(f'{label}  |  AFND: {nfa.count} estados  |  AFD: {len(dfa.subsets)} estados  |  Solo ASCII')
            self.tabs.select(self.tab_result)
            self.show_graph('AFD')
        except (ValueError, RecursionError) as exc:
            self.machine = None
            self.result_text = ''
            self.status.set('Expresión inválida: ' + str(exc))
            self._put(self.result_view, 'Error de conversión:\n' + str(exc))
            self._clear_tables()
            self.current_dot = ''
            self.canvas.delete('all')
            self.image_ref = None
            self.graph_note.set('Corrige la expresión antes de visualizar diagramas.')
            self.tabs.select(self.tab_result)

    def _clear_tables(self):
        for table in (self.nfa_table, self.dfa_table):
            table.delete(*table.get_children())

    def _fill_tables(self, nfa, dfa):
        self._clear_tables()
        for (state, symbol), targets in ordered_nfa_edges(nfa):
            self.nfa_table.insert('', 'end', values=(f'q{state}', symbol, '{' + ', '.join('q'+str(i) for i in sorted(targets)) + '}'))
        for state, row in enumerate(dfa.delta):
            for label, symbols in grouped_alphabet(dfa):
                self.dfa_table.insert('', 'end', values=(f'Q{state}', label, f'Q{row[symbols[0]]}'))

    def toggle_fit(self):
        self.fit_diagram = not self.fit_diagram
        self.show_graph(self.current_kind)

    def show_graph(self, kind):
        self.current_kind = kind
        if self.machine is None:
            self.graph_note.set('Primero convierte una ER.')
            return
        nfa, dfa = self.machine
        self.current_dot = nfa_dot(nfa) if kind == 'AFND' else dfa_dot(dfa)
        self.graph_note.set(f'Diagrama {kind} | Los estados dobles son de aceptación. La flecha exterior indica el inicial.')
        self.canvas.delete('all')
        self.image_ref = None
        nodes = nfa.count if kind == 'AFND' else len(dfa.subsets)
        edges = len(nfa.edges) if kind == 'AFND' else sum(len(row) for row in dfa.delta)
        if nodes > 80 or edges > 500:
            self.graph_note.set('Diagrama grande: exporta DOT para visualizarlo con Graphviz sin saturar la interfaz.')
            self.canvas.create_text(25, 30, anchor='nw', fill=NAVY, text='Diagrama grande. Usa Exportar DOT o Exportar PNG.', font=('DejaVu Sans', 12))
            self.canvas.configure(scrollregion=(0, 0, 800, 130))
            return
        try:
            raw = png_bytes(self.current_dot)
            full = tk.PhotoImage(data=base64.b64encode(raw).decode('ascii'))
            factor = 1
            if self.fit_diagram:
                usable_w = max(400, self.canvas.winfo_width() - 35)
                factor = max(1, math.ceil(full.width() / usable_w))
            self.image_ref = full.subsample(factor) if factor > 1 else full
            self.canvas.create_image(15, 15, anchor='nw', image=self.image_ref)
            self.canvas.configure(scrollregion=(0, 0, self.image_ref.width()+35, self.image_ref.height()+35))
        except (RuntimeError, tk.TclError) as exc:
            self.graph_note.set(f'No se pudo mostrar PNG: {exc}. Puedes exportar DOT.')
            self.canvas.create_text(25, 30, anchor='nw', fill=NAVY, width=650,
                                    text='Instala Graphviz para obtener diagramas PNG.\n\n'
                                    'Linux Mint: sudo apt install graphviz\n\n'
                                    'El archivo .dot puede exportarse incluso sin Graphviz.', font=('DejaVu Sans', 12))
            self.canvas.configure(scrollregion=(0, 0, 800, 180))

    def export_graph(self, png):
        if not self.current_dot:
            messagebox.showwarning('Sin diagrama', 'Primero convierte una expresión regular.')
            return
        ext = '.png' if png else '.dot'
        filename = filedialog.asksaveasfilename(title='Guardar diagrama', initialfile=self.current_kind + ext,
                                                 defaultextension=ext, filetypes=[('Imagen PNG', '*.png')] if png else [('Graphviz DOT', '*.dot')])
        if not filename:
            return
        try:
            content = png_bytes(self.current_dot) if png else self.current_dot.encode('utf-8')
            Path(filename).write_bytes(content)
            self.status.set('Diagrama exportado: ' + filename)
        except (OSError, RuntimeError) as exc:
            messagebox.showerror('No se pudo exportar', str(exc))

    def save_result(self):
        if not self.result_text:
            messagebox.showwarning('Sin resultados', 'Primero convierte y evalúa una expresión.')
            return
        filename = filedialog.asksaveasfilename(title='Guardar resultado de consola', initialfile='resultado_er_afd.txt',
                                                 defaultextension='.txt', filetypes=[('Texto', '*.txt')])
        if filename:
            try:
                Path(filename).write_text(self.result_text, encoding='utf-8')
                self.status.set('Resultado guardado: ' + filename)
            except OSError as exc:
                messagebox.showerror('No se pudo guardar', str(exc))


def main():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print('No se pudo iniciar la interfaz. Inicia una sesión gráfica de Linux y comprueba DISPLAY:', exc)
        return 2
    ConverterApp(root)
    root.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
