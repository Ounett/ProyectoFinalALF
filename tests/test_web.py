"""Pruebas de capa web, API local y reutilización del motor."""
from __future__ import annotations
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from erafd.web.server import Handler, analyze


class WebEngineTests(unittest.TestCase):
    def test_accept(self):
        result = analyze('(a|b)*abb', 'aabb', include_svg=False)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['return_code'], 1)
        self.assertEqual(result['path'][0], 'Q0')
        self.assertTrue(result['trace'])

    def test_reject(self):
        data = analyze(r'\N\N', '2A', include_svg=False)
        self.assertFalse(data['accepted'])
        self.assertEqual(data['return_code'], 0)

    def test_empty_chain_epsilon(self):
        data = analyze('ε', '', include_svg=False)
        self.assertTrue(data['accepted'])
        self.assertEqual(data['trace'], [])
        self.assertEqual(data['dfa']['finals'], ['Q0'])

    def test_table_nfa_and_dfa(self):
        data = analyze('ab', 'ab', include_svg=False)
        self.assertTrue(data['nfa']['rows'])
        self.assertTrue(data['dfa']['rows'])
        self.assertEqual(data['dfa']['start'], 'Q0')
        self.assertEqual(data['nfa']['start'], 'q0')

    def test_invalid_expression(self):
        with self.assertRaisesRegex(ValueError, 'Falta una expresión'):
            analyze('a|', 'a', include_svg=False)

    def test_non_ascii_rejected(self):
        with self.assertRaisesRegex(ValueError, 'ASCII'):
            analyze('a', 'á', include_svg=False)

    def test_limits(self):
        for er, chain in [('', ''), ('a'*321, ''), ('a', 'b'*4001)]:
            with self.subTest(er=er[:10], n=len(chain)):
                with self.assertRaises(ValueError):
                    analyze(er, chain, include_svg=False)

    def test_diagram_data(self):
        data = analyze('ab', 'ab', include_svg=False)
        self.assertEqual(len(data['diagrams']['nfa']['nodes']), data['metrics']['nfa_states'])
        self.assertEqual(len(data['diagrams']['dfa']['nodes']), data['metrics']['dfa_states'])

    def test_no_svg_when_disabled(self):
        data = analyze('ab', 'ab', include_svg=False)
        self.assertEqual(data['graph_svg'], {'nfa': None, 'dfa': None})


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.http.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=2)

    def request(self, path, obj=None, headers=None):
        body = json.dumps(obj).encode('utf-8') if obj is not None else None
        request = Request(self.base + path, data=body, headers=(headers or {}),
                          method='POST' if body is not None else 'GET')
        if obj is not None and 'Content-Type' not in (headers or {}):
            request.add_header('Content-Type', 'application/json')
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, response.read(), response.headers
        except HTTPError as err:
            return err.code, err.read(), err.headers

    def test_health(self):
        status, raw, headers = self.request('/api/health')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)['status'], 'ok')
        self.assertIn("default-src 'self'", headers['Content-Security-Policy'])

    def test_pantalla_tiene_solo_lo_necesario(self):
        from erafd.web.server import STATIC
        html = (STATIC / 'index.html').read_text(encoding='utf-8')
        for nombre in ('expresion', 'cadena', 'convertir', 'afnd-tabla', 'afd-tabla', 'dibujo'):
            self.assertIn(f'id="{nombre}"', html)
        self.assertNotIn('sidebar', html)
        self.assertNotIn('metric-card', html)

    def test_estilo_blanco_y_negro(self):
        from erafd.web.server import STATIC
        css = (STATIC / 'styles.css').read_text(encoding='utf-8')
        import re
        colores = set(re.findall(r'#[0-9a-fA-F]{3,8}\b', css))
        self.assertEqual(colores, {'#000', '#fff'})
        self.assertNotIn('gradient(', css)

    def test_static(self):
        for path in ['/', '/styles.css', '/app.js', '/favicon.svg']:
            with self.subTest(path=path):
                code, content, _ = self.request(path)
                self.assertEqual(code, 200)
                self.assertTrue(content)

    def test_http_conversion(self):
        code, raw, _ = self.request('/api/convert', {'expression': '(a|b)*abb', 'chain': 'aabb'})
        self.assertEqual(code, 200)
        data = json.loads(raw)
        self.assertTrue(data['accepted'])
        self.assertGreater(len(data['dfa']['rows']), 0)

    def test_bad_expression_http(self):
        code, raw, _ = self.request('/api/convert', {'expression': '(a|', 'chain': 'a'})
        self.assertEqual(code, 422)
        self.assertIn('error', json.loads(raw))

    def test_origin_rejected(self):
        code, _, _ = self.request('/api/convert', {'expression': 'a', 'chain': 'a'},
                                  {'Origin': 'https://example.org'})
        self.assertEqual(code, 403)

    def test_unknown_path(self):
        code, _, _ = self.request('/../../etc/passwd')
        self.assertEqual(code, 404)

    def test_invalid_content_type(self):
        code, _, _ = self.request('/api/convert', {'expression': 'a', 'chain': 'a'},
                                  {'Content-Type': 'text/plain'})
        self.assertEqual(code, 415)


if __name__ == '__main__':
    unittest.main()
