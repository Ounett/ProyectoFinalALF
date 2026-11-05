PYTHON := python3
export ER ?= ab*
export CADENA ?= abbb
PORT ?= 8765

.PHONY: config build run web test docs clean
config:
	@$(PYTHON) -c "import sys; assert sys.version_info >= (3, 9), 'Se necesita Python 3.9+'"
	@chmod +x er-afd er-afd-web iniciar.sh
	@echo "Configuración lista"

build: config
	@$(PYTHON) -m compileall -q erafd
	@echo "Código verificado"

run:
	@$(PYTHON) -m erafd "$${ER}" "$${CADENA}"; code=$$?; \
	 if [ $$code -eq 0 ] || [ $$code -eq 1 ]; then exit 0; else exit $$code; fi

web:
	@$(PYTHON) -m erafd.web.server --port "$(PORT)"

test:
	@$(PYTHON) -m unittest discover -s tests -v

docs:
	@command -v libreoffice >/dev/null || { echo "Se necesita LibreOffice para generar los PDF"; exit 1; }
	@mkdir -p doc
	@libreoffice --headless --convert-to pdf --outdir doc doc/reporte-tecnico.html doc/manual-usuario.html doc/casos-de-prueba.html >/dev/null
	@echo "Documentación PDF generada en doc/"

clean:
	@find . -type d -name __pycache__ -prune -exec rm -rf '{}' +
	@find . -type f -name '*.pyc' -delete
	@echo "Temporales eliminados"
