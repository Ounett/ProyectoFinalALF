"""Diagramas DOT de AFND y AFD. Graphviz es OPCIONAL y externo al motor.
"""
from __future__ import annotations
import subprocess
from pathlib import Path
from .core import EPSILON, grouped_alphabet


def _quote(s):
    """Texto seguro como atributo de DOT, incluyendo \" \\ y controles ASCII."""
    result = []
    for ch in str(s):
        if ch == '\\': result.append('\\\\')
        elif ch == '"': result.append('\\"')
        elif ch == '\n': result.append('\\n')
        elif ch == '\r': result.append('\\r')
        elif ch == '\t': result.append('\\t')
        elif ord(ch) < 32 or ord(ch) == 127: result.append(f'\\\\h{ord(ch):02X}')
        else: result.append(ch)
    return '"' + ''.join(result) + '"'


def _head(title):
    return [
        'digraph automata {',
        '  rankdir=LR; bgcolor="white"; pad=0.32; nodesep=0.36; ranksep=0.62;',
        '  graph [fontname="DejaVu Sans", label=' + _quote(title) + ', labelloc=t, fontsize=18, fontcolor="#000000"];',
        '  node [shape=circle, fontname="DejaVu Sans", fontsize=12, color="#000000", fontcolor="#000000", penwidth=1.5];',
        '  edge [fontname="DejaVu Sans", fontsize=10, color="#000000", fontcolor="#000000", arrowsize=0.75];',
        '  inicio [shape=point, width=0.09, color="#000000"];',
    ]


def nfa_dot(nfa):
    lines = _head('AFND - Construccion de Thompson')
    lines += [f'  q{i} [shape={"doublecircle" if i == nfa.final else "circle"}, color="{("#000000" if i == nfa.final else "#000000")}"];'
              for i in range(nfa.count)]
    lines.append(f'  inicio -> q{nfa.start};')
    grouped = {}
    for edge in nfa.edges:
        grouped.setdefault((edge.src, edge.dst), [])
        if edge.label not in grouped[(edge.src, edge.dst)]:
            grouped[(edge.src, edge.dst)].append(edge.label)
    for (src, dst), labels in sorted(grouped.items()):
        lines.append(f'  q{src} -> q{dst} [label={_quote(", ".join(labels))}];')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def dfa_dot(dfa):
    lines = _head('AFD - Construccion de subconjuntos')
    for i in range(len(dfa.subsets)):
        final = i in dfa.final_states
        lines.append(f'  Q{i} [shape={"doublecircle" if final else "circle"}, color="{("#000000" if final else "#000000")}"];')
    lines.append('  inicio -> Q0;')
    grouped = {}
    for src, row in enumerate(dfa.delta):
        for label, symbols in grouped_alphabet(dfa):
            grouped.setdefault((src, row[symbols[0]]), []).append(label)
    for (src, dst), labels in sorted(grouped.items()):
        lines.append(f'  Q{src} -> Q{dst} [label={_quote(", ".join(labels))}];')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def png_bytes(dot_source, timeout=12):
    """Convierte DOT a PNG llamando a Graphviz; no altera las máquinas."""
    try:
        cp = subprocess.run(['dot', '-Tpng'], input=dot_source.encode('utf-8'),
                            capture_output=True, check=False, timeout=timeout)
    except FileNotFoundError as exc:
        raise RuntimeError('Graphviz no está instalado. Instálalo con: sudo apt install graphviz') from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Se agotó el tiempo disponible para generar el diagrama.') from exc
    if cp.returncode:
        message = cp.stderr.decode('utf-8', 'replace').strip()[:300]
        raise RuntimeError('Error al generar el diagrama: ' + message)
    return cp.stdout


def write_diagrams(expression, folder, render_png=True):
    from .core import compile_regex
    nfa, dfa = compile_regex(expression)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    results = []
    for stem, source in [('AFND', nfa_dot(nfa)), ('AFD', dfa_dot(dfa))]:
        path = folder / (stem + '.dot')
        path.write_text(source, encoding='utf-8')
        results.append(path)
        if render_png:
            png = folder / (stem + '.png')
            png.write_bytes(png_bytes(source))
            results.append(png)
    return results


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Exportar AFND/AFD a DOT y PNG')
    parser.add_argument('er', help='Expresión regular, entre comillas simples')
    parser.add_argument('--salida', default='diagramas_generados', help='Carpeta de destino')
    parser.add_argument('--solo-dot', action='store_true', help='No se requiere Graphviz')
    args = parser.parse_args()
    try:
        paths = write_diagrams(args.er, args.salida, not args.solo_dot)
        print('Diagramas exportados:')
        for path in paths: print(' -', path)
    except (ValueError, RuntimeError) as exc:
        parser.exit(status=2, message=f'Error: {exc}\n')
