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
- Los errores del motor (JSON malformado, etc.) aparecen en rojo bajo el
  editor.

El render usa exactamente el mismo `generate_diagram` que el CLI de AlmaGag,
así que el resultado es idéntico a `python -m AlmaGag.main archivo.sdjf`.

## Tests

```bash
python -m pytest -q
```

## Licencia

MIT — igual que AlmaGag.
