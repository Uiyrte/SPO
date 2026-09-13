from __future__ import annotations

import tkinter as tk
from itertools import zip_longest
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from halstead import HalsteadMetrics, compute_metrics
from tokenizer import tokenize

_COLUMNS = ("j", "Оператор", "f1j", "i", "Операнд", "f2i")


class HalsteadApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Метрики Холстеда — C#")
        self.geometry("900x600")

        self._current_path: str | None = None
        self._scope = tk.StringVar(value="all")
        self._build_widgets()

    def _build_widgets(self) -> None:
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Button(top, text="Открыть файл .cs", command=self._on_open).pack(side="left")
        self._path_label = ttk.Label(top, text="Файл не выбран")
        self._path_label.pack(side="left", padx=10)
        ttk.Button(top, text="Анализировать", command=self._on_analyze).pack(side="right")

        scope_bar = ttk.Frame(self, padding=(8, 0, 8, 8))
        scope_bar.pack(fill="x")
        ttk.Label(scope_bar, text="Область анализа:").pack(side="left")
        ttk.Radiobutton(
            scope_bar, text="Весь файл", variable=self._scope, value="all"
        ).pack(side="left", padx=(6, 0))
        ttk.Radiobutton(
            scope_bar, text="Только раздел операторов (тела методов)", variable=self._scope, value="bodies"
        ).pack(side="left", padx=(6, 0))

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self._source_text = self._make_text_tab(notebook, "Исходный код")
        self._table, self._summary_labels = self._make_table_tab(notebook, "Таблица 2")

    def _make_text_tab(self, notebook: ttk.Notebook, title: str) -> tk.Text:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        text = tk.Text(frame, wrap="none")
        text.pack(fill="both", expand=True)
        return text

    def _make_table_tab(self, notebook: ttk.Notebook, title: str) -> tuple[ttk.Treeview, dict[str, ttk.Label]]:
        frame = ttk.Frame(notebook, padding=8)
        notebook.add(frame, text=title)

        tree = ttk.Treeview(frame, columns=_COLUMNS, show="headings")
        for col in _COLUMNS:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=110)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        summary = ttk.Frame(frame, padding=(0, 10, 0, 0))
        summary.grid(row=1, column=0, columnspan=2, sticky="w")

        labels: dict[str, ttk.Label] = {}
        for key, row in (("vocab", 0), ("length", 1), ("volume", 2)):
            label = ttk.Label(summary, text="", font=("TkDefaultFont", 11))
            label.grid(row=row, column=0, sticky="w", pady=2)
            labels[key] = label

        return tree, labels

    def _on_open(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите файл C#",
            filetypes=[("C# файлы", "*.cs"), ("Все файлы", "*.*")],
        )
        if not path:
            return

        try:
            source = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Ошибка чтения файла", str(exc))
            return

        self._current_path = path
        self._path_label.config(text=path)
        self._source_text.delete("1.0", "end")
        self._source_text.insert("1.0", source)

    def _on_analyze(self) -> None:
        if self._current_path is None:
            messagebox.showwarning("Нет файла", "Сначала выберите файл .cs")
            return

        source = self._source_text.get("1.0", "end")
        tokens = tokenize(source, scope=self._scope.get())
        metrics = compute_metrics(tokens)
        self._show_metrics(metrics)

    def _show_metrics(self, m: HalsteadMetrics) -> None:
        self._table.delete(*self._table.get_children())

        operators = sorted(m.f1j.items(), key=lambda kv: -kv[1])
        operands = sorted(m.f2i.items(), key=lambda kv: -kv[1])

        for row_num, (op_row, nd_row) in enumerate(zip_longest(operators, operands), start=1):
            j = row_num if op_row else ""
            operator, f1j = op_row if op_row else ("", "")
            i = row_num if nd_row else ""
            operand, f2i = nd_row if nd_row else ("", "")
            self._table.insert("", "end", values=(j, operator, f1j, i, operand, f2i))

        self._table.insert(
            "", "end",
            values=(f"η1 = {m.n1}", "", f"N1 = {m.N1}", f"η2 = {m.n2}", "", f"N2 = {m.N2}"),
        )

        self._summary_labels["vocab"].config(
            text=f"Словарь программы η = η1 + η2 = {m.n1} + {m.n2} = {m.vocabulary}"
        )
        self._summary_labels["length"].config(
            text=f"Длина программы N = N1 + N2 = {m.N1} + {m.N2} = {m.length}"
        )
        self._summary_labels["volume"].config(
            text=f"Объём программы V = N·log2(η) = {m.length}·log2({m.vocabulary}) = {m.volume:.2f}"
        )


if __name__ == "__main__":
    HalsteadApp().mainloop()
