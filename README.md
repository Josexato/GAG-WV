# GAG-WV — Visor web local para AlmaGag

Aplicación web independiente para ver diagramas [AlmaGag](https://github.com/Josexato/AlmaGag):
cargas un `.sdjf` o `.gag` a la izquierda y el SVG generado aparece a la
derecha, con scroll para moverte y zoom.

Corre 100% local en tu laptop (solo escucha en `127.0.0.1`) y no tiene
dependencias propias más allá del motor AlmaGag.

## Instalación

Necesitas Python 3.8+ y el motor AlmaGag. Cualquiera de estas opciones sirve:

```bash
# Opción A: instalar el motor con pip
pip install git+https://github.com/Josexato/AlmaGag

# Opción B: clonar el motor junto a este repo (GAG-WV lo detecta solo)
git clone https://github.com/Josexato/AlmaGag ../AlmaGag

# Opción C: apuntar a un clon existente en otra ruta
export ALMAGAG_PATH=/ruta/a/AlmaGag
```

## Uso

```bash
python -m gagwv
```

Abre el navegador solo en `http://127.0.0.1:8321`. Opciones:

```bash
python -m gagwv --port 9000        # otro puerto
python -m gagwv --no-browser      # no abrir el navegador
```

## Qué hace

- **Izquierda**: botón *Abrir archivo…*, arrastrar y soltar, o pegar el JSON
  directo. El contenido queda editable — retoca y re-renderiza con
  `Ctrl+Enter`.
- **Derecha**: el SVG en un contenedor con scroll, con zoom (`+`/`−`, `1:1`,
  *Ajustar* al ancho, `Ctrl+rueda` del mouse) y botón para descargar el SVG.
- Opciones del motor: layout (`select`/`auto`/`hier`/`legacy`), vista
  (`flow`/`areas`/`lanes`/`matrix`) y `visualdebug`.
- **Epifanía en pestañas**: con el checkbox *epifanía (fases)* activo, el
  render también captura el flipbook del layout naciendo (equivale a
  `--epifania` del CLI) y cada fase aparece como una pestaña sobre el visor
  — *Resultado · 01 posicionamiento · 02 contenedores · 03 ruteo…* — con el
  mismo scroll y zoom. *Descargar SVG* baja la pestaña visible.
- Los errores del motor (JSON malformado, etc.) aparecen en rojo bajo el
  editor.
- **Exportar a PDF**: el botón *🖨 PDF* genera un PDF vectorial de la
  pestaña visible al tamaño exacto del diagrama, usando el Chrome/Edge ya
  instalado en modo headless (mismo detector §O58 del motor, incluida la
  variable `ALMAGAG_CHROME`). Si no hay navegador compatible, abre la vista
  de impresión para *Guardar como PDF* a mano.
- **Exportar para análisis**: el botón *📦 Exportar análisis* descarga un
  ZIP con la fuente `.sdjf`/`.gag`, el SVG renderizado, las fases de la
  Epifanía (si están activas), un `LOG.txt` con los diagnósticos del motor
  en ese render (cruces, tinta, aspecto, bandas…) y un `INFO.txt` de contexto — listo para
  adjuntarlo a un análisis de diseño (p. ej. una conversación con Claude).
- **Ocultar el editor**: el botón *◀ JSON* colapsa el panel izquierdo para
  ver el diagrama a pantalla completa; *▶ JSON* lo trae de vuelta.
- **Editor con plegado**: el JSON se puede colapsar por llaves (flechitas en
  el margen, CodeMirror vendoreado — sigue sin necesitar internet), con
  números de línea, sintaxis coloreada y botones *Colapsar* / *Expandir*
  todo. El clic en el SVG despliega automáticamente lo que estaba colapsado.
- **Clic en el SVG → parte del JSON**: haz clic en un nodo, contenedor,
  etiqueta o conexión del diagrama y el editor selecciona y hace scroll al
  objeto JSON que lo definió (prefiriendo la definición en `elements` sobre
  referencias en `contains`/`journeys`), con un resaltado azul sobre la
  figura y un chip que dice qué se encontró. Las conexiones tienen una zona
  de clic ancha invisible para no tener que acertarle a la línea de 2px.
- **Aviso de motor desactualizado**: al abrir el visor compara tu AlmaGag
  local contra `master` en GitHub (commit git si es un clon; versión de
  `pyproject.toml` si fue `pip install`) y muestra un banner con cuántos
  commits estás atrás y el comando exacto para actualizar. Sin conexión o
  sin git el aviso simplemente no aparece — nada se bloquea. Se re-verifica
  como mucho una vez por hora.

El render usa exactamente el mismo `generate_diagram` que el CLI de AlmaGag,
así que el resultado es idéntico a `python -m AlmaGag.main archivo.sdjf`.

## Tests

```bash
python -m pytest -q
```

## Licencia

MIT — igual que AlmaGag.
