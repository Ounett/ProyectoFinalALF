"""Interfaz de línea de comandos exigida por el proyecto."""
import sys
from .core import compile_regex, format_machine, RegexSyntaxError

HELP = r'''ER-AFD | Convertidor de expresiones regulares a AFD
USO: er-afd <ER> <cadena>
EJEMPLOS:
  ./er-afd 'ab*' 'abbb'
  ./er-afd '(a|b)*abb' 'aabb'
  ./er-afd '\N\N' '42'
  ./er-afd 'hola mundo' 'hola mundo'
  ./er-afd 'ε' ''

Operadores: concatenación, |, *, (), ., ε, [abc], [^abc], [a-z]
Escapes: \N (0-9), \A (A-Z), \a (a-z), \z (letras), \hHH (ASCII hexadecimal), \X (literal X)
Solo se admiten caracteres ASCII en la cadena; ε en la ER representa la cadena vacía.
CÓDIGO DE SALIDA: 1 aceptada, 0 rechazada, 2 error (especificación del docente).
Nota: 1 se interpreta como error por bash, pero corresponde a una aceptación válida.
'''


def main(args=None):
    args = sys.argv[1:] if args is None else args
    if args in (['--help'], ['-h']):
        print(HELP)
        return 0
    if len(args) != 2:
        print('Error: deben recibirse la ER y la cadena. Ejecuta ./er-afd --help', file=sys.stderr)
        return 2
    expression, chain = args
    try:
        if not chain.isascii():
            raise ValueError('La cadena debe contener únicamente caracteres ASCII')
        nfa, dfa = compile_regex(expression)
        print('ER:', expression)
        print('CADENA:', repr(chain))
        print(format_machine(nfa, dfa))
        print('\nRECORRIDO DEL AFD')
        accepted, steps = dfa.trace(chain)
        if not steps: print('(cadena vacía: se verifica si Q0 es de aceptación)')
        for step in steps: print(step)
        print('Cadena aceptada' if accepted else 'Cadena rechazada')
        print('Código de retorno:', 1 if accepted else 0)
        return 1 if accepted else 0
    except (RegexSyntaxError, ValueError, RecursionError) as exc:
        print('Error:', exc, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
