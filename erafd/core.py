"""Motor ER -> AFND (Thompson) -> AFD (subconjuntos).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

ASCII = tuple(range(128))
ALL_ASCII = (1 << 128) - 1
EPSILON = 'ε'
MAX_DFA_STATES = 2048


class RegexSyntaxError(ValueError):
    """Expresión regular inválida (incluye posición aproximada)."""


@dataclass(frozen=True)
class Node:
    kind: str
    children: tuple['Node', ...] = ()
    mask: int = 0
    label: str = ''


def mask_of(chars):
    result = 0
    for char in chars:
        result |= 1 << ord(char)
    return result


def ascii_label(ch: str) -> str:
    value = ord(ch)
    if ch == ' ': return r'\h20'
    if ch == '\\': return r'\\'
    if ch == '|': return r'\|'
    if ch == '*': return r'\*'
    if ch == '.': return r'\.'
    if ch in '()[]': return '\\' + ch
    if value < 32 or value == 127: return f'\\h{value:02X}'
    return ch


class Parser:
    """Parser descendente recursivo: unión < concatenación < Kleene."""
    def __init__(self, source: str):
        self.text = source
        self.pos = 0
        self.symbol_order: list[str] = []
        self.atom_masks: list[int] = []
        for index, char in enumerate(source):
            if ord(char) > 127 and char != EPSILON:
                raise RegexSyntaxError(f'ER: símbolo no ASCII en posición {index + 1}: {char!r}')

    def fail(self, message):
        raise RegexSyntaxError(f'{message} (posición {self.pos + 1})')

    def peek(self):
        return self.text[self.pos] if self.pos < len(self.text) else ''

    def read(self):
        if self.pos == len(self.text): self.fail('Fin inesperado de ER')
        ch = self.text[self.pos]
        self.pos += 1
        return ch

    def record(self, label, mask=None):
        if label not in self.symbol_order:
            self.symbol_order.append(label)
        if mask is not None:
            self.atom_masks.append(mask)

    def parse(self):
        if not self.text: self.fail('La ER está vacía; usa ε para representar vacío')
        ast = self.union()
        if self.pos != len(self.text): self.fail(f'Símbolo no esperado: {self.peek()!r}')
        return ast

    def union(self):
        lhs = self.concat()
        while self.peek() == '|':
            self.read()
            rhs = self.concat()
            lhs = Node('union', (lhs, rhs))
        return lhs

    def concat(self):
        parts = []
        while self.peek() and self.peek() not in ')|':
            parts.append(self.repeat())
        if not parts: self.fail('Falta una expresión (unión o paréntesis vacío)')
        if len(parts) == 1: return parts[0]
        return Node('concat', tuple(parts))

    def repeat(self):
        node = self.atom()
        if self.peek() == '*':
            self.read()
            node = Node('star', (node,))
            if self.peek() == '*': self.fail('No se permiten dos operadores * consecutivos')
        return node

    def atom(self):
        start = self.pos
        char = self.read()
        if char == '(':
            nested = self.union()
            if self.peek() != ')': self.fail('Falta cerrar el paréntesis')
            self.read()
            return nested
        if char == ')': self.fail('Paréntesis de cierre sin apertura')
        if char in '*|': self.fail(f'Operador sin operando: {char}')
        if char == '[':
            mask = self.character_class()
            label = self.text[start:self.pos]
            self.record(label, mask)
            return Node('symbol', mask=mask, label=label)
        if char == EPSILON:
            self.record(EPSILON)
            return Node('epsilon')
        if char == '.':
            self.record('.', ALL_ASCII)
            return Node('symbol', mask=ALL_ASCII, label='.')
        if char == '\\':
            mask, literal = self.escape()
            label = self.text[start:self.pos]
            self.record(label, mask)
            return Node('symbol', mask=mask, label=label)
        if char == ']': self.fail('Corchete de cierre fuera de conjunto')
        self.record(ascii_label(char), 1 << ord(char))
        return Node('symbol', mask=1 << ord(char), label=ascii_label(char))

    def escape(self):
        if not self.peek(): self.fail('Secuencia de escape incompleta')
        char = self.read()
        if char == 'N': return mask_of('0123456789'), None
        if char == 'A': return mask_of('ABCDEFGHIJKLMNOPQRSTUVWXYZ'), None
        if char == 'a': return mask_of('abcdefghijklmnopqrstuvwxyz'), None
        if char == 'z': return mask_of('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'), None
        if char == 'h':
            if self.pos + 2 > len(self.text): self.fail('Se requieren dos dígitos hexadecimales después de \\h')
            chunk = self.text[self.pos:self.pos + 2]
            if any(c not in '0123456789abcdefABCDEF' for c in chunk):
                self.fail('Código hexadecimal no válido')
            self.pos += 2
            value = int(chunk, 16)
            if value > 127: self.fail('El código hexadecimal debe pertenecer a ASCII (00-7F)')
            return 1 << value, chr(value)
        return 1 << ord(char), char

    def class_item(self):
        """Lee un átomo del conjunto, devuelve (máscara, carácter para rangos)."""
        char = self.read()
        if char == '\\': return self.escape()
        return 1 << ord(char), char

    def character_class(self):
        inverted = self.peek() == '^'
        if inverted: self.read()
        items: list[tuple[int, Optional[str]]] = []
        while self.peek() and self.peek() != ']':
            items.append(self.class_item())
        if self.peek() != ']': self.fail('Conjunto sin corchete de cierre')
        self.read()
        if not items: self.fail('Conjunto de caracteres vacío')
        mask = 0
        index = 0
        while index < len(items):
            left_mask, left_char = items[index]
            if (index + 2 < len(items) and items[index + 1][1] == '-'
                    and left_char is not None and items[index + 2][1] is not None):
                right = items[index + 2][1]
                if ord(left_char) > ord(right): self.fail(f'Rango inválido: {left_char}-{right}')
                for code in range(ord(left_char), ord(right) + 1): mask |= 1 << code
                index += 3
            else:
                mask |= left_mask
                index += 1
        return (ALL_ASCII ^ mask) if inverted else mask


@dataclass(frozen=True)
class Edge:
    src: int
    dst: int
    mask: Optional[int]
    label: str


@dataclass
class NFA:
    start: int
    final: int
    count: int
    edges: list[Edge]
    symbols: list[str]
    atom_masks: list[int]


class Thompson:
    def __init__(self):
        self.count = 0
        self.edges = []

    def state(self):
        current = self.count
        self.count += 1
        return current

    def edge(self, a, b, mask=None, label=EPSILON):
        self.edges.append(Edge(a, b, mask, label))

    def fragment(self, node):
        if node.kind in ('symbol', 'epsilon'):
            a, b = self.state(), self.state()
            self.edge(a, b, node.mask if node.kind == 'symbol' else None,
                      node.label if node.kind == 'symbol' else EPSILON)
            return a, b
        if node.kind == 'concat':
            a, b = self.fragment(node.children[0])
            for item in node.children[1:]:
                c, d = self.fragment(item)
                self.edge(b, c)
                b = d
            return a, b
        if node.kind == 'union':
            a, b = self.fragment(node.children[0]); c, d = self.fragment(node.children[1])
            start, end = self.state(), self.state()
            for u in (a, c): self.edge(start, u)
            for u in (b, d): self.edge(u, end)
            return start, end
        if node.kind == 'star':
            a, b = self.fragment(node.children[0])
            start, end = self.state(), self.state()
            self.edge(start, a); self.edge(start, end)
            self.edge(b, a); self.edge(b, end)
            return start, end
        raise RuntimeError(f'Nodo desconocido: {node.kind}')

    def build(self, ast, symbol_order, atom_masks):
        start, final = self.fragment(ast)
        outgoing = {i: [] for i in range(self.count)}
        for e in self.edges: outgoing[e.src].append(e)
        queue = deque([start]); renamed = {start: 0}
        while queue:
            current = queue.popleft()
            for edge in outgoing[current]:
                if edge.dst not in renamed:
                    renamed[edge.dst] = len(renamed); queue.append(edge.dst)
        for state in range(self.count):
            if state not in renamed: renamed[state] = len(renamed)
        new_edges = [Edge(renamed[e.src], renamed[e.dst], e.mask, e.label) for e in self.edges]
        new_edges.sort(key=lambda e: (e.src, e.label, e.dst))
        symbols = symbol_order.copy()
        if EPSILON not in symbols: symbols.append(EPSILON)
        return NFA(0, renamed[final], self.count, new_edges, symbols, atom_masks)


@dataclass
class DFA:
    subsets: list[frozenset[int]]
    final_states: set[int]
    delta: list[dict[int, int]]
    alphabet: list[int]

    def trace(self, input_text: str):
        if not input_text.isascii():
            raise ValueError('La cadena debe contener únicamente caracteres ASCII')
        state, lines = 0, []
        for char in input_text:
            symbol = ord(char)
            next_state = self.delta[state].get(symbol)
            shown = ascii_label(char)
            if next_state is None:
                lines.append(f'Q{state}|{shown}|∅')
                return False, lines
            lines.append(f'Q{state}|{shown}|Q{next_state}')
            state = next_state
        return state in self.final_states, lines


def subset_construction(nfa: NFA, max_states=MAX_DFA_STATES) -> DFA:
    outgoing = [[] for _ in range(nfa.count)]
    for edge in nfa.edges: outgoing[edge.src].append(edge)
    alphabet_seen = set()
    alphabet = []
    for mask in nfa.atom_masks:
        for code in ASCII:
            if ((mask >> code) & 1) and code not in alphabet_seen:
                alphabet_seen.add(code)
                alphabet.append(code)

    def closure(states):
        seen = set(states); queue = deque(states)
        while queue:
            for edge in outgoing[queue.popleft()]:
                if edge.mask is None and edge.dst not in seen:
                    seen.add(edge.dst); queue.append(edge.dst)
        return frozenset(seen)

    initial = closure([nfa.start])
    subsets = [initial]; index = {initial: 0}; delta = []; final_states = set()
    queue = deque([initial])
    while queue:
        subset = queue.popleft(); row = {}
        idx = index[subset]
        if nfa.final in subset: final_states.add(idx)
        for code in alphabet:
            reached = set()
            for state in subset:
                for edge in outgoing[state]:
                    if edge.mask is not None and ((edge.mask >> code) & 1):
                        reached.add(edge.dst)
            target = closure(reached)
            if target not in index:
                if len(subsets) >= max_states:
                    raise ValueError(f'El AFD supera el límite de {max_states} estados; simplifica la ER')
                index[target] = len(subsets)
                subsets.append(target); queue.append(target)
            row[code] = index[target]
        delta.append(row)
    return DFA(subsets, final_states, delta, alphabet)


def grouped_alphabet(dfa):
    """Columnas de la matriz: símbolos ASCII aislados o clases equivalentes."""
    if len(dfa.alphabet) <= 14:
        return [(ascii_label(chr(code)), (code,)) for code in dfa.alphabet]
    groups = {}
    for code in dfa.alphabet:
        signature = tuple(row.get(code) for row in dfa.delta)
        groups.setdefault(signature, []).append(code)
    result = []
    for _, raw_codes in groups.items():
        codes = sorted(raw_codes)
        if len(codes) == 1:
            label = ascii_label(chr(codes[0]))
        elif len(codes) == 128:
            label = '.'
        elif codes == list(range(ord('0'), ord('9') + 1)):
            label = '[0-9]'
        elif codes == list(range(ord('a'), ord('z') + 1)):
            label = '[a-z]'
        elif codes == list(range(ord('A'), ord('Z') + 1)):
            label = '[A-Z]'
        elif len(codes) <= 12 and all(32 <= c <= 126 for c in codes):
            label = '[' + ''.join(chr(c) for c in codes) + ']'
        else:
            label = f'CLASE_{len(result)+1}'
        result.append((label, tuple(codes)))
    return result


def compile_regex(expression):
    parser = Parser(expression)
    ast = parser.parse()
    nfa = Thompson().build(ast, parser.symbol_order, parser.atom_masks)
    dfa = subset_construction(nfa)
    return nfa, dfa


def ordered_nfa_edges(nfa):
    groups = {}
    for edge in nfa.edges:
        groups.setdefault((edge.src, edge.label), set()).add(edge.dst)
    return sorted(groups.items(), key=lambda item: (item[0][0], nfa.symbols.index(item[0][1]) if item[0][1] in nfa.symbols else 10000))


def format_machine(nfa, dfa):
    lines = ['AFND', 'Q={' + ','.join(f'q{i}' for i in range(nfa.count)) + '}',
             'Σ={' + ','.join(nfa.symbols) + '}', f'q0 = inicial', f'F={{q{nfa.final}}}']
    for (state, label), destinations in ordered_nfa_edges(nfa):
        lines.append(f'q{state}|{label}|{{' + ','.join(f'q{i}' for i in sorted(destinations)) + '}')
    lines += ['', 'AFD', 'Q={' + ','.join(f'Q{i}' for i in range(len(dfa.subsets))) + '}']
    classes = grouped_alphabet(dfa)
    lines.append('Σ={' + ','.join(name for name, _ in classes) + '}')
    lines.append('Q0 = inicial')
    lines.append('F={' + ','.join('Q' + str(i) for i in sorted(dfa.final_states)) + '}')
    for i, row in enumerate(dfa.delta):
        for name, codes in classes:
            lines.append(f'Q{i}|{name}|Q{row[codes[0]]}')
    special = [(name, codes) for name, codes in classes if name.startswith('CLASE_')]
    if special:
        lines += ['', 'LEYENDA DE CLASES (rangos de códigos ASCII):']
        for name, codes in special:
            spans, beg, prev = [], codes[0], codes[0]
            for code in codes[1:]:
                if code == prev + 1: prev = code
                else:
                    spans.append(f'{beg:02X}-{prev:02X}' if beg != prev else f'{beg:02X}')
                    beg = prev = code
            spans.append(f'{beg:02X}-{prev:02X}' if beg != prev else f'{beg:02X}')
            lines.append(f'{name}: ' + ', '.join(spans))
    return '\n'.join(lines)
