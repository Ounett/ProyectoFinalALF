# ER a AFD

Aplicación local para convertir una expresión regular (ER) en un autómata
finito no determinista (AFND), construir el autómata finito determinista (AFD)
y evaluar una cadena mediante el AFD.

La aplicación web usa únicamente la biblioteca estándar de Python. No requiere
Flask, Node.js ni paquetes instalados con `pip`.

## Requisitos

- Python 3.9 o posterior.
- Un navegador web actualizado.
- Graphviz es opcional. Se utiliza únicamente para generar diagramas SVG más
  completos; la aplicación incluye una vista básica sin Graphviz.

## Instalación y ejecución en Linux

1. Instala Python:

   ```bash
   sudo apt update
   sudo apt install python3
   ```

2. Opcionalmente instala Graphviz:

   ```bash
   sudo apt install graphviz
   ```

3. Abre una terminal en la carpeta del proyecto y ejecuta:

   ```bash
   ./iniciar.sh
   ```

4. El navegador se abrirá en `http://127.0.0.1:8765/`. Si no se abre
   automáticamente, visita esa dirección.

Para usar otro puerto:

```bash
./iniciar.sh --port 8766
```

Para cerrar la aplicación, vuelve a la terminal y presiona `Ctrl+C`.

## Instalación y ejecución en Windows

1. Instala Python 3.9 o posterior desde
   [python.org](https://www.python.org/downloads/windows/). Durante la
   instalación activa la opción **Add Python to PATH**.
2. Opcionalmente instala Graphviz desde
   [graphviz.org](https://graphviz.org/download/). Si Graphviz no está en
   `PATH`, la aplicación seguirá funcionando con sus diagramas básicos.
3. Abre el Explorador de archivos, entra en la carpeta del proyecto y haz doble
   clic en `iniciar.bat`.

También puedes usar PowerShell:

```powershell
cd C:\ruta\ER_AFD_MINIMAL_BN
py -3 -m erafd.web.server
```

Para cambiar el puerto:

```powershell
.\iniciar.bat --port 8766
```

Para cerrar la aplicación, cierra la ventana de la terminal o presiona
`Ctrl+C`.

## Uso de la interfaz web

1. Escribe la expresión regular en **Expresión regular**.
2. Escribe la cadena que quieres evaluar en **Cadena para evaluar**. Déjala
   vacía para evaluar la cadena ε.
3. Selecciona **Convertir y evaluar**.
4. Revisa el resultado en **Recorrido**:
   - **Cadena aceptada** indica que el AFD termina en un estado final.
   - **Cadena rechazada** indica que no termina en un estado final o que no
     existe una transición válida.
5. Consulta **Tabla AFND** y **Tabla AFD** para revisar las transiciones.
6. En **Diagramas**, selecciona AFND o AFD. Si el autómata es demasiado grande,
   utiliza las tablas.
7. Usa **Limpiar** para iniciar una nueva operación.

El botón principal también puede ejecutarse con `Ctrl+Enter`. La expresión
regular admite concatenación, `|`, `*`, paréntesis, `ε`, `.`, clases como
`[abc]` y rangos como `[a-z]`. Las cadenas de prueba deben contener caracteres
ASCII.

## Verificación del proyecto

Para comprobar que el proyecto funciona, ejecuta en Linux:

```bash
make test
```

Esto ejecuta las pruebas del motor, la interfaz web y la API local.

## Interfaz de terminal

La interfaz web es la forma recomendada para usar el proyecto. La CLI se
mantiene para automatización y evaluación:

```bash
./er-afd '(a|b)*abb' 'aabb'
```

Su código de salida es `1` si acepta la cadena, `0` si la rechaza y `2` si
existe un error de entrada.

-Ounett-

