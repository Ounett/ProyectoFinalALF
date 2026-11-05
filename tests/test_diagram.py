"""Comprobación de diagramas y CLI complementaria, sin GUI real requerida."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from erafd.core import compile_regex
from erafd.diagram import nfa_dot, dfa_dot, png_bytes, write_diagrams


class DiagramTests(unittest.TestCase):
    def setUp(self):
        self.nfa, self.dfa = compile_regex('(a|b)*abb')

    def test_dot_contains_initial_and_final(self):
        dot = nfa_dot(self.nfa)
        self.assertIn('inicio -> q0;', dot)
        self.assertIn('doublecircle', dot)
        self.assertIn('ε', dot)

    def test_dfa_dot_has_initial_and_acceptance(self):
        dot = dfa_dot(self.dfa)
        self.assertIn('inicio -> Q0;', dot)
        self.assertIn('doublecircle', dot)
        self.assertIn('Q0 ->', dot)

    def test_dot_escape_quotes_and_backslash(self):
        nfa, dfa = compile_regex(r'("|\\)*')
        dot = nfa_dot(nfa) + dfa_dot(dfa)
        self.assertIn('inicio ->', dot)
        self.assertIn('\\"', dot)

    def test_epsilon_dfa_valid(self):
        nfa, dfa = compile_regex('ε')
        self.assertIn('Q0', dfa_dot(dfa))
        self.assertIn('q0', nfa_dot(nfa))

    def test_ascii_class_label(self):
        nfa, dfa = compile_regex(r'\N*')
        self.assertIn('label="0, 1, 2, 3, 4, 5, 6, 7, 8, 9"', dfa_dot(dfa))

    def test_export_dot_without_graphviz(self):
        with tempfile.TemporaryDirectory() as td:
            paths = write_diagrams('ab*', td, False)
            self.assertEqual(len(paths), 2)
            self.assertTrue(all(p.suffix == '.dot' and p.stat().st_size > 100 for p in paths))

    @unittest.skipUnless(shutil.which('dot'), 'Graphviz no instalado')
    def test_png_graphviz(self):
        raw = png_bytes(dfa_dot(self.dfa))
        self.assertTrue(raw.startswith(b'\x89PNG'))

    @unittest.skipUnless(shutil.which('dot'), 'Graphviz no instalado')
    def test_export_pngs(self):
        with tempfile.TemporaryDirectory() as td:
            paths = write_diagrams('ab*', td)
            self.assertEqual(len(paths), 4)
            self.assertTrue(all(p.exists() for p in paths))

    def test_gui_module_importable(self):
        # Importación no crea ventana; no exige escritorio en la prueba.
        import erafd.gui
        self.assertTrue(hasattr(erafd.gui, 'ConverterApp'))

    def test_diagram_cli_dot(self):
        with tempfile.TemporaryDirectory() as td:
            result = subprocess.run([sys.executable, '-m', 'erafd.diagram', 'ab*', '--solo-dot', '--salida', td],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(td) / 'AFD.dot').exists())


if __name__ == '__main__':
    unittest.main()
