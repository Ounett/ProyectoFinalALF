"""Servidor web local sin Flask ni dependencias pip: Python stdlib + motor académico.

Seguridad: loopback exclusivamente, Host/Origin validados, JSON POST con longitud máxima,
archivos estáticos permitidos explícitamente y sin ejecución de comandos del usuario.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from erafd.core import (
    RegexSyntaxError, ascii_label, compile_regex, format_machine,
    grouped_alphabet, ordered_nfa_edges,
)
from erafd.diagram import dfa_dot, nfa_dot

STATIC = Path(__file__).parent / 'static'
ALLOWED = {'/': 'index.html', '/index.html': 'index.html', '/styles.css': 'styles.css', '/app.js': 'app.js', '/favicon.svg': 'favicon.svg'}
MAX_BODY = 15_000
MAX_ER = 320
MAX_CHAIN = 4_000
MAX_NFA_NODES_FOR_GRAPH = 170
MAX_DFA_NODES_FOR_GRAPH = 130


def transitions_nfa(nfa):
    return [{'from': f'q{src}', 'symbol': label,
             'to': '{' + ','.join(f'q{dest}' for dest in sorted(destinations)) + '}'}
            for (src, label), destinations in ordered_nfa_edges(nfa)]


def transitions_dfa(dfa):
    return [{'from': f'Q{idx}', 'symbol': label, 'to': f'Q{row[values[0]]}'}
            for idx, row in enumerate(dfa.delta)
            for label, values in grouped_alphabet(dfa)]


def nodes_edges(nfa, dfa):
    nfa_edges = [{'from': f'q{e.src}', 'to': f'q{e.dst}', 'label': e.label}
                 for e in nfa.edges]
    dfa_edges = transitions_dfa(dfa)
    return {
        'nfa': {'nodes': [{'id': f'q{i}', 'final': i == nfa.final, 'initial': i == 0}
                          for i in range(nfa.count)], 'edges': nfa_edges},
        'dfa': {'nodes': [{'id': f'Q{i}', 'final': i in dfa.final_states, 'initial': i == 0,
                          'subset': ', '.join(f'q{n}' for n in sorted(dfa.subsets[i]))}
                         for i in range(len(dfa.subsets))], 'edges': dfa_edges}
    }


def svg_for(dot_code):
    if not shutil.which('dot'):
        return None
    try:
        result = subprocess.run(['dot', '-Tsvg'], input=dot_code, text=True,
                                capture_output=True, timeout=5, check=False)
        if result.returncode == 0 and result.stdout.lstrip().startswith('<?xml'):
            return result.stdout
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def analyze(expression: str, chain: str, include_svg=True) -> dict:
    if not isinstance(expression, str) or not isinstance(chain, str):
        raise ValueError('Expresión y cadena deben ser textos.')
    if not expression or len(expression) > MAX_ER:
        raise ValueError(f'La expresión debe contener entre 1 y {MAX_ER} caracteres.')
    if len(chain) > MAX_CHAIN:
        raise ValueError(f'La cadena supera el máximo de {MAX_CHAIN} caracteres.')
    if not chain.isascii():
        raise ValueError('La cadena de prueba debe contener únicamente caracteres ASCII.')
    nfa, dfa = compile_regex(expression)
    accepted, trace = dfa.trace(chain)
    classes = grouped_alphabet(dfa)
    state_path = ['Q0']
    state = 0
    for char in chain:
        nxt = dfa.delta[state].get(ord(char))
        if nxt is None:
            state_path.append('∅')
            break
        state_path.append(f'Q{nxt}')
        state = nxt
    diagrams = nodes_edges(nfa, dfa)
    graph_limited = nfa.count > MAX_NFA_NODES_FOR_GRAPH or len(dfa.subsets) > MAX_DFA_NODES_FOR_GRAPH
    graph_svg = {'nfa': None, 'dfa': None}
    if include_svg and not graph_limited:
        graph_svg['nfa'] = svg_for(nfa_dot(nfa))
        graph_svg['dfa'] = svg_for(dfa_dot(dfa))
    if graph_limited:
        diagrams = {'nfa': {'nodes': [], 'edges': []}, 'dfa': {'nodes': [], 'edges': []}}
    return {
        'expression': expression, 'chain': chain, 'accepted': accepted,
        'return_code': 1 if accepted else 0, 'trace': trace, 'path': state_path,
        'metrics': {'nfa_states': nfa.count, 'dfa_states': len(dfa.subsets),
                    'dfa_final_states': len(dfa.final_states), 'alphabet_size': len(dfa.alphabet),
                    'transitions_nfa': len(nfa.edges), 'transitions_dfa': len(dfa.delta) * len(classes)},
        'nfa': {'start': 'q0', 'finals': [f'q{nfa.final}'], 'symbols': nfa.symbols,
                'states': [f'q{i}' for i in range(nfa.count)], 'rows': transitions_nfa(nfa)},
        'dfa': {'start': 'Q0', 'finals': [f'Q{n}' for n in sorted(dfa.final_states)],
                'symbols': [label for label, _ in classes],
                'states': [f'Q{i}' for i in range(len(dfa.subsets))],
                'subsets': {f'Q{i}': [f'q{j}' for j in sorted(group)] for i, group in enumerate(dfa.subsets)},
                'rows': transitions_dfa(dfa)},
        'diagrams': diagrams, 'graph_svg': graph_svg, 'graph_limited': graph_limited,
        'machine_text': format_machine(nfa, dfa),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = 'ERAFDLocal/2.0'

    def log_message(self, fmt, *args):
        return

    def _headers(self, code, mime, length=None):
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data: blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        if length is not None:
            self.send_header('Content-Length', str(length))
        self.end_headers()

    def _json(self, code, obj):
        content = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self._headers(code, 'application/json; charset=utf-8', len(content))
        self.wfile.write(content)

    def _valid_host(self):
        host = self.headers.get('Host', '')
        return host in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def _same_origin(self):
        origin = self.headers.get('Origin', '')
        if not origin:
            return True
        parsed = urlsplit(origin)
        return parsed.scheme == 'http' and parsed.netloc in (
            f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def do_GET(self):
        if not self._valid_host():
            return self._json(403, {'error': 'Host no permitido.'})
        path = urlsplit(self.path).path
        if path == '/api/health':
            return self._json(200, {'status': 'ok', 'service': 'ER-AFD Web',
                                    'graphviz': bool(shutil.which('dot')), 'version': '2.0'})
        if path not in ALLOWED:
            return self._json(404, {'error': 'Recurso no encontrado.'})
        asset = STATIC / ALLOWED[path]
        try:
            content = asset.read_bytes()
        except OSError:
            return self._json(500, {'error': 'Archivo de interfaz ausente.'})
        mime = ('text/html; charset=utf-8' if asset.suffix == '.html' else
                'text/css; charset=utf-8' if asset.suffix == '.css' else
                'application/javascript; charset=utf-8' if asset.suffix == '.js' else 'image/svg+xml')
        self._headers(200, mime, len(content))
        self.wfile.write(content)

    def do_POST(self):
        if not self._valid_host() or not self._same_origin():
            return self._json(403, {'error': 'Origen no permitido.'})
        if urlsplit(self.path).path != '/api/convert':
            return self._json(404, {'error': 'Ruta no encontrada.'})
        if self.headers.get('Content-Type', '').split(';', 1)[0].lower() != 'application/json':
            return self._json(415, {'error': 'Envía JSON con Content-Type application/json.'})
        try:
            size = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            size = -1
        if size < 0 or size > MAX_BODY:
            return self._json(413, {'error': 'Solicitud demasiado grande.'})
        try:
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError('Se esperaba un objeto JSON.')
            data = analyze(payload.get('expression'), payload.get('chain'), include_svg=True)
            return self._json(200, data)
        except (RegexSyntaxError, ValueError, RecursionError, TypeError) as exc:
            return self._json(422, {'error': str(exc)})
        except Exception:
            return self._json(500, {'error': 'Se produjo un error interno. Consulta la terminal.'})


def main(argv=None):
    parser = argparse.ArgumentParser(description='Interfaz web local de ER-AFD (sin dependencias pip)')
    parser.add_argument('--port', type=int, default=8765, help='Puerto local (por defecto 8765)')
    parser.add_argument('--no-open', action='store_true', help='No abrir navegador automáticamente')
    args = parser.parse_args(argv)
    if args.port < 0 or args.port > 65535:
        parser.error('El puerto debe estar entre 0 y 65535')
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError as exc:
        parser.exit(2, f'No se pudo abrir el servidor local: {exc}\nPrueba: make web PORT=8766\n')
    url = f'http://127.0.0.1:{server.server_port}/'
    print('\n' + '=' * 61, flush=True)
    print(' ER a AFD | Aplicación local', flush=True)
    print(f' Dirección: {url}', flush=True)
    print(' Para cerrar: Ctrl + C en esta terminal', flush=True)
    print(' Funciona sin internet | Python estándar | Reconocimiento propio', flush=True)
    print('=' * 61 + '\n', flush=True)
    if not args.no_open:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        print('\nServidor finalizado.')
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
