from __future__ import annotations

import re
from preprocessor import CodePreprocessor
from specs import DEFAULT_REGISTRY, OperatorRegistry


class GilbMetricsAnalyzer:
    def __init__(self, code: str, registry: OperatorRegistry = DEFAULT_REGISTRY):
        self.raw_code = code
        self.registry = registry
        self.clean_code = ""
        self.cl = 0
        self.cli = 0
        self.n_total = 0
        self.cl_rel = 0.0

    def _count_non_condition_statements(self) -> int:
        type_keywords = (
            r'int|uint|long|ulong|short|ushort|byte|sbyte|float|double|decimal|'
            r'bool|char|string|object|void|var|[A-Z][a-zA-Z0-9_]*'
        )
        decl_regex = re.compile(
            rf'^\s*(?:(?:public|private|protected|internal|static|readonly|const)\s+)*'
            rf'(?:{type_keywords})(?:<[^>]+>)?(?:\[\])*\s+[a-zA-Z_][a-zA-Z0-9_]*\s*(?:=\s*[^;]+)?$'
        )

        count = 0
        raw_statements = self.clean_code.split(';')
        for stmt in raw_statements:
            s = stmt.strip()
            if not s:
                continue
            if s.startswith('using ') or s.startswith('namespace '):
                continue
            if 'for (' in s or 'for(' in s:
                continue
            if re.search(r'\}\s*while\s*\(', s):
                continue
            if decl_regex.match(s) and not any(k in s for k in ('Add(', 'WriteLine(', 'ReadLine(')):
                continue
            count += 1
        return count

    def parse(self) -> dict[str, float | int]:
        self.clean_code = CodePreprocessor.clean(self.raw_code)

        token_pattern = re.compile(
            r'\belse\s+if\b|\b(if|for|while|do|foreach|switch|case|default)\b|'
            r'(\?)|(\{)|(\})'
        )

        tokens: list[tuple[str, int]] = []
        for match in token_pattern.finditer(self.clean_code):
            val = re.sub(r'\s+', ' ', match.group(0))
            tokens.append((val, match.start()))

        current_nesting = 0
        max_nesting = 0
        total_conditions = 0

        in_do_stack: list[bool] = []
        switch_stack: list[dict[str, int]] = []
        scope_stack: list[bool] = []
        pending_condition = False

        i = 0
        while i < len(tokens):
            token, _ = tokens[i]

            if token == '{':
                if switch_stack:
                    switch_stack[-1]["brace_depth"] += 1
                scope_stack.append(pending_condition)
                pending_condition = False

            elif token == '}':
                if switch_stack and switch_stack[-1]["brace_depth"] > 0:
                    switch_stack[-1]["brace_depth"] -= 1
                    if switch_stack[-1]["brace_depth"] == 0:
                        sw_info = switch_stack.pop()
                        current_nesting -= sw_info["case_count"]

                if scope_stack:
                    was_cond = scope_stack.pop()
                    if was_cond:
                        current_nesting -= 1

            elif token in ('for', 'foreach', 'if'):
                total_conditions += 1
                current_nesting += 1
                if current_nesting > max_nesting:
                    max_nesting = current_nesting
                pending_condition = True

            elif token == 'do':
                in_do_stack.append(True)
                total_conditions += 1
                current_nesting += 1
                if current_nesting > max_nesting:
                    max_nesting = current_nesting
                pending_condition = True

            elif token == 'while':
                if in_do_stack:
                    in_do_stack.pop()
                else:
                    total_conditions += 1
                    current_nesting += 1
                    if current_nesting > max_nesting:
                        max_nesting = current_nesting
                    pending_condition = True

            elif token == 'else if':
                total_conditions += 1
                pending_condition = False

            elif token == '?':
                total_conditions += 1
                if current_nesting + 1 > max_nesting:
                    max_nesting = current_nesting + 1

            elif token == 'switch':
                switch_stack.append({"case_count": 0, "brace_depth": 0})
                pending_condition = False

            elif token == 'case':
                total_conditions += 1
                if switch_stack:
                    count = switch_stack[-1]["case_count"]
                    if count > 0:
                        current_nesting += 1
                    switch_stack[-1]["case_count"] += 1
                    if current_nesting > max_nesting:
                        max_nesting = current_nesting

            elif token == 'default':
                pass

            i += 1

        self.cl = total_conditions
        self.cli = max_nesting

        non_cond_count = self._count_non_condition_statements()
        self.n_total = self.cl + non_cond_count
        self.cl_rel = round(self.cl / self.n_total, 4) if self.n_total > 0 else 0.0

        return {
            "CL": self.cl,
            "CLI": self.cli,
            "N_total": self.n_total,
            "cl": self.cl_rel,
        }