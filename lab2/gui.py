from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from analyzer import GilbMetricsAnalyzer


class GilbApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gilb Metrics Analyzer (C#)")
        self.geometry("900x650")
        self.minsize(700, 500)
        self._init_ui()

    def _init_ui(self):
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill=tk.X)

        ttk.Button(toolbar, text="Открыть файл (.cs)", command=self._on_load_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Рассчитать метрики", command=self._on_calculate).pack(side=tk.LEFT, padx=4)

        editor_box = ttk.LabelFrame(self, text="Исходный код C#", padding=6)
        editor_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.text_editor = tk.Text(editor_box, wrap=tk.NONE, font=("Consolas", 10))
        scroll_y = ttk.Scrollbar(editor_box, orient=tk.VERTICAL, command=self.text_editor.yview)
        scroll_x = ttk.Scrollbar(editor_box, orient=tk.HORIZONTAL, command=self.text_editor.xview)
        self.text_editor.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.text_editor.pack(fill=tk.BOTH, expand=True)

        results_box = ttk.LabelFrame(self, text="Результаты расчета метрик Джилба", padding=10)
        results_box.pack(fill=tk.X, padx=8, pady=8)

        self.lbl_cl = ttk.Label(results_box, text="Абсолютная сложность (CL): -", font=("Segoe UI", 10, "bold"))
        self.lbl_cl.grid(row=0, column=0, sticky=tk.W, padx=12, pady=4)

        self.lbl_rel = ttk.Label(results_box, text="Относительная сложность (cl): -", font=("Segoe UI", 10, "bold"))
        self.lbl_rel.grid(row=0, column=1, sticky=tk.W, padx=12, pady=4)

        self.lbl_cli = ttk.Label(results_box, text="Макс. уровень вложенности (CLI): -", font=("Segoe UI", 10, "bold"))
        self.lbl_cli.grid(row=1, column=0, sticky=tk.W, padx=12, pady=4)

        self.lbl_total = ttk.Label(results_box, text="Всего операторов (N): -", font=("Segoe UI", 10))
        self.lbl_total.grid(row=1, column=1, sticky=tk.W, padx=12, pady=4)

    def _on_load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("C# Source Files", "*.cs"), ("All Files", "*.*")])
        if filepath:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.text_editor.delete("1.0", tk.END)
            self.text_editor.insert(tk.END, content)

    def _on_calculate(self):
        code = self.text_editor.get("1.0", tk.END)
        if not code.strip():
            messagebox.showwarning("Внимание", "Поле ввода пусто.")
            return

        analyzer = GilbMetricsAnalyzer(code)
        res = analyzer.parse()

        self.lbl_cl.config(text=f"Абсолютная сложность (CL): {res['CL']}")
        self.lbl_rel.config(text=f"Относительная сложность (cl): {res['cl']}")
        self.lbl_cli.config(text=f"Макс. уровень вложенности (CLI): {res['CLI']}")
        self.lbl_total.config(text=f"Всего операторов (N): {res['N_total']}")