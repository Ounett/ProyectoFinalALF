"""Pruebas sin regex: resultados previstos por reglas manuales."""
import itertools
import os
import subprocess
import sys
import unittest
from pathlib import Path
from erafd import compile_regex, RegexSyntaxError
from erafd.core import EPSILON, grouped_alphabet, format_machine

ROOT = Path(__file__).resolve().parents[1]


class ConversionTests(unittest.TestCase):
    def accept(self, expr, chain):
        _, dfa = compile_regex(expr)
        return dfa.trace(chain)[0]

    def test_literal_accepted(self): self.assertTrue(self.accept('abc', 'abc'))
    def test_literal_rejected(self): self.assertFalse(self.accept('abc', 'abd'))
    def test_prefix_rejected(self): self.assertFalse(self.accept('abc', 'ab'))
    def test_suffix_rejected(self): self.assertFalse(self.accept('abc', 'abcc'))
    def test_union_a(self): self.assertTrue(self.accept('a|b', 'a'))
    def test_union_b(self): self.assertTrue(self.accept('a|b', 'b'))
    def test_union_reject(self): self.assertFalse(self.accept('a|b', 'ab'))
    def test_kleene_empty(self): self.assertTrue(self.accept('a*', ''))
    def test_kleene_repeat(self): self.assertTrue(self.accept('a*', 'aaaa'))
    def test_kleene_invalid(self): self.assertFalse(self.accept('a*', 'ab'))
    def test_concat_star(self): self.assertTrue(self.accept('ab*', 'abbbb'))
    def test_concat_star_empty_b(self): self.assertTrue(self.accept('ab*', 'a'))
    def test_concat_star_reject(self): self.assertFalse(self.accept('ab*', 'b'))
    def test_parentheses(self): self.assertTrue(self.accept('(a|b)*abb', 'aabb'))
    def test_parentheses_reject(self): self.assertFalse(self.accept('(a|b)*abb', 'abaa'))
    def test_precedence(self): self.assertTrue(self.accept('ab|c', 'c'))
    def test_precedence_reject(self): self.assertFalse(self.accept('ab|c', 'ac'))
    def test_nested_parentheses(self): self.assertTrue(self.accept('((a|b)c)*', 'acbc'))
    def test_epsilon_empty(self): self.assertTrue(self.accept('ε', ''))
    def test_epsilon_nonempty(self): self.assertFalse(self.accept('ε', 'a'))
    def test_epsilon_union(self): self.assertTrue(self.accept('a|ε', ''))
    def test_epsilon_concat(self): self.assertTrue(self.accept('aεb', 'ab'))
    def test_wildcard(self): self.assertTrue(self.accept('a.b', 'a0b'))
    def test_wildcard_special(self): self.assertTrue(self.accept('a.b', 'a b'))
    def test_wildcard_reject(self): self.assertFalse(self.accept('a.b', 'ab'))
    def test_any_star(self): self.assertTrue(self.accept('.*', 'abc123'))
    def test_wildcard_overlap(self): self.assertTrue(self.accept('.|a', 'a'))
    def test_wildcard_overlap_suffix(self): self.assertTrue(self.accept('(.|a)b', 'ab'))
    def test_any_vs_literal(self): self.assertTrue(self.accept('a|.', 'a'))
    def test_character_set(self): self.assertTrue(self.accept('[abc]', 'b'))
    def test_character_set_rejected(self): self.assertFalse(self.accept('[abc]', 'd'))
    def test_character_range(self): self.assertTrue(self.accept('[a-z]', 'm'))
    def test_character_range_reject(self): self.assertFalse(self.accept('[a-z]', 'A'))
    def test_character_combined_range(self): self.assertTrue(self.accept('[a-zA-Z]', 'H'))
    def test_negative_set(self): self.assertTrue(self.accept('[^abc]', 'k'))
    def test_negative_set_reject(self): self.assertFalse(self.accept('[^abc]', 'a'))
    def test_negative_set_space(self): self.assertTrue(self.accept('[^ab]', ' '))
    def test_negative_set_zero(self): self.assertTrue(self.accept('[^ab]', '\x00'))
    def test_escaped_kleene(self): self.assertTrue(self.accept(r'\*', '*'))
    def test_escaped_union(self): self.assertTrue(self.accept(r'\|', '|'))
    def test_escaped_dot(self): self.assertTrue(self.accept(r'\.', '.'))
    def test_escaped_backslash(self): self.assertTrue(self.accept(r'\\', '\\'))
    def test_escaped_parenthesis(self): self.assertTrue(self.accept(r'\(', '('))
    def test_escaped_literal(self): self.assertTrue(self.accept(r'\p', 'p'))
    def test_escape_digits(self): self.assertTrue(self.accept(r'\N\N', '42'))
    def test_escape_digits_invalid(self): self.assertFalse(self.accept(r'\N\N', '4a'))
    def test_escape_upper(self): self.assertTrue(self.accept(r'\A*', 'ABZ'))
    def test_escape_lower(self): self.assertTrue(self.accept(r'\a*', 'hola'))
    def test_escape_letters(self): self.assertTrue(self.accept(r'\z*', 'Hola'))
    def test_escape_letters_reject(self): self.assertFalse(self.accept(r'\z*', 'Hola2'))
    def test_hex_space(self): self.assertTrue(self.accept(r'hola\h20mundo', 'hola mundo'))
    def test_hex_upper(self): self.assertTrue(self.accept(r'\h41', 'A'))
    def test_hex_null(self): self.assertTrue(self.accept(r'\h00', '\x00'))
    def test_class_escape_hex(self): self.assertTrue(self.accept(r'[\h41-Z]', 'H'))
    def test_class_escape_digits(self): self.assertTrue(self.accept(r'[\N]', '7'))
    def test_class_escape_bracket(self): self.assertTrue(self.accept(r'[\]]', ']'))
    def test_dashy_class(self): self.assertTrue(self.accept('[-a]', '-'))
    def test_space_literal(self): self.assertTrue(self.accept('hola mundo', 'hola mundo'))
    def test_empty_string_rejected(self): self.assertFalse(self.accept('a', ''))
    def test_non_ascii_input_rejected(self):
        _, dfa = compile_regex('a')
        with self.assertRaises(ValueError): dfa.trace('á')
    def test_sigma_epsilon_append(self):
        nfa, _ = compile_regex('ab')
        self.assertEqual(nfa.symbols, ['a', 'b', EPSILON])
        _, reversed_dfa = compile_regex('ba')
        self.assertEqual(reversed_dfa.alphabet, [ord('b'), ord('a')])
    def test_sigma_epsilon_position(self):
        nfa, _ = compile_regex('aεb')
        self.assertEqual(nfa.symbols, ['a', EPSILON, 'b'])
    def test_q0_both(self):
        nfa, dfa = compile_regex('(a|b)*abb')
        self.assertEqual(nfa.start, 0)
        self.assertEqual(len(dfa.subsets) > 0, True)
    def test_no_epsilon_in_dfa(self):
        _, dfa = compile_regex('a*')
        self.assertTrue(all(isinstance(k, int) for row in dfa.delta for k in row))
    def test_every_dfa_transition_deterministic(self):
        _, dfa = compile_regex('(a|b)*abb')
        for row in dfa.delta:
            self.assertEqual(len(row), len(dfa.alphabet))
    def test_no_infinite_epsilon_closure(self):
        self.assertTrue(self.accept('(ε|a)*b', 'aaab'))
    def test_complex(self):
        self.assertTrue(self.accept(r'([a-z]|\N)*[A-Z]', 'abc37Z'))
    def test_trace(self):
        _, dfa = compile_regex('ab')
        result, lines = dfa.trace('ab')
        self.assertTrue(result)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith('Q0|a|Q'))
    def test_unknown_symbol_trace(self):
        _, dfa = compile_regex('ab')
        result, lines = dfa.trace('x')
        self.assertFalse(result)
        self.assertTrue(lines[-1].endswith('∅'))
    def test_format_output(self):
        nfa, dfa = compile_regex('ab')
        output = format_machine(nfa, dfa)
        self.assertIn('AFND', output)
        self.assertIn('AFD', output)
        self.assertIn('q0|a|', output)
        self.assertIn('Q0|a|', output)


class SyntaxTests(unittest.TestCase):
    def invalid(self, value):
        with self.assertRaises(RegexSyntaxError, msg=value): compile_regex(value)

    def test_empty(self): self.invalid('')
    def test_open_paren(self): self.invalid('(ab')
    def test_close_paren(self): self.invalid('ab)')
    def test_empty_group(self): self.invalid('()')
    def test_empty_left_union(self): self.invalid('|b')
    def test_empty_right_union(self): self.invalid('a|')
    def test_double_union(self): self.invalid('a||b')
    def test_star_without_atom(self): self.invalid('*a')
    def test_double_star(self): self.invalid('a**')
    def test_empty_set(self): self.invalid('[]')
    def test_open_set(self): self.invalid('[abc')
    def test_reversed_range(self): self.invalid('[z-a]')
    def test_dangling_escape(self): self.invalid('a\\')
    def test_bad_hex(self): self.invalid(r'\hXX')
    def test_missing_hex(self): self.invalid(r'\h4')
    def test_non_ascii_hex(self): self.invalid(r'\hE1')
    def test_unicode(self): self.invalid('mañana')
    def test_unmatched_bracket(self): self.invalid('a]')


class CLITests(unittest.TestCase):
    def call(self, *args):
        return subprocess.run([sys.executable, '-m', 'erafd', *args], cwd=ROOT,
                              capture_output=True, text=True, encoding='utf-8')

    def test_accepted_returns_1(self):
        cp = self.call('ab*', 'abbb')
        self.assertEqual(cp.returncode, 1)
        self.assertIn('Cadena aceptada', cp.stdout)
    def test_rejected_returns_0(self):
        cp = self.call('ab*', 'b')
        self.assertEqual(cp.returncode, 0)
        self.assertIn('Cadena rechazada', cp.stdout)
    def test_error_returns_2(self):
        cp = self.call('(', 'a')
        self.assertEqual(cp.returncode, 2)
        self.assertIn('Error:', cp.stderr)
    def test_help_returns_0(self):
        cp = self.call('--help')
        self.assertEqual(cp.returncode, 0)
        self.assertIn('USO:', cp.stdout)
    def test_requires_two_arguments(self):
        cp = self.call('a')
        self.assertEqual(cp.returncode, 2)
    def test_space(self):
        cp = self.call('hola mundo', 'hola mundo')
        self.assertEqual(cp.returncode, 1)
    def test_epsilon(self):
        cp = self.call('ε', '')
        self.assertEqual(cp.returncode, 1)


class AccuracyTests(unittest.TestCase):
    def test_many_strings_oracle(self):
        alphabet = 'abx'
        cases = [''.join(p) for size in range(0, 7) for p in itertools.product(alphabet, repeat=size)]
        oracles = [
            ('a*', lambda s: all(ch == 'a' for ch in s)),
            ('ab*', lambda s: len(s) > 0 and s[0] == 'a' and all(c == 'b' for c in s[1:])),
            ('(a|b)*', lambda s: all(c in 'ab' for c in s)),
            ('(a|b)*abb', lambda s: all(c in 'ab' for c in s) and s.endswith('abb')),
            ('a|bx', lambda s: s in ('a', 'bx')),
            ('[^ab]*', lambda s: all(c not in 'ab' for c in s)),
            ('a.b', lambda s: len(s) == 3 and s[0] == 'a' and s[2] == 'b'),
        ]
        for expr, oracle in oracles:
            with self.subTest(expr=expr):
                _, dfa = compile_regex(expr)
                count = 0
                for text in cases:
                    self.assertEqual(dfa.trace(text)[0], oracle(text), f'ER {expr!r}, cadena {text!r}')
                    count += 1
                self.assertEqual(count, 1093)


if __name__ == '__main__': unittest.main()
