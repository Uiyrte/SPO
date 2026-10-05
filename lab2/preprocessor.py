from __future__ import annotations

import re


class CodePreprocessor:
    @staticmethod
    def clean(raw_code: str) -> str:
        code = re.sub(r'/\*.*?\*/', ' ', raw_code, flags=re.DOTALL)
        code = re.sub(r'//.*', ' ', code)
        code = re.sub(r'@"(?:[^"]|"")*"', '""', code)
        code = re.sub(r'\$"(?:\\.|[^"\\])*"', '""', code)
        code = re.sub(r'"(?:\\.|[^"\\])*"', '""', code)
        code = re.sub(r"'(?:\\.|[^'\\])*'", "''", code)
        return code