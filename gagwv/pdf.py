"""Exportar SVG a PDF vectorial con Chrome/Edge headless (--print-to-pdf).

Sin dependencias Python nuevas: se apoya en el navegador ya instalado.
Si no hay ninguno, el endpoint responde 501 y la UI cae al diálogo de
impresión del navegador (Guardar como PDF).
"""

import glob
import os
import re
import shutil
import subprocess
import tempfile

PLANTILLA = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@page {{ size: {w}px {h}px; margin: 0; }}
html, body {{ margin: 0; padding: 0; }}
svg {{ display: block; width: {w}px; height: {h}px; }}
</style></head><body>{svg}</body></html>"""


def buscar_chrome():
    """Ejecutable de Chrome/Chromium/Edge, o None. Prefiere el detector
    del motor (§O58) y cae a una búsqueda local equivalente."""
    try:
        from AlmaGag.debug import _find_chrome_executable
        encontrado = _find_chrome_executable()
        if encontrado:
            return encontrado
    except Exception:
        pass

    env = os.environ.get('ALMAGAG_CHROME')
    if env and os.path.exists(env):
        return env
    for nombre in ('google-chrome', 'google-chrome-stable', 'chromium',
                   'chromium-browser', 'chrome', 'msedge'):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    tipicas = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    pw_root = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '/opt/pw-browsers')
    tipicas += sorted(glob.glob(os.path.join(
        pw_root, 'chromium-*', 'chrome-linux', 'chrome')), reverse=True)
    tipicas.append(os.path.join(pw_root, 'chromium'))
    for ruta in tipicas:
        if os.path.exists(ruta):
            return ruta
    return None


def _dimensiones(svg):
    """(ancho, alto) en px CSS desde width/height o el viewBox del SVG."""
    def attr(nombre):
        m = re.search(nombre + r'="([\d.]+)"', svg[:2000])
        return float(m.group(1)) if m else None
    w, h = attr('width'), attr('height')
    if not (w and h):
        m = re.search(r'viewBox="[\d.\-]+[ ,]+[\d.\-]+[ ,]+([\d.]+)[ ,]+([\d.]+)"',
                      svg[:2000])
        if m:
            w, h = w or float(m.group(1)), h or float(m.group(2))
    return w or 800.0, h or 600.0


def svg_a_pdf(svg, chrome=None):
    """Convierte el SVG (str) a PDF (bytes) con el navegador headless.

    Devuelve None si no hay navegador o la conversión falla."""
    chrome = chrome or buscar_chrome()
    if not chrome:
        return None
    w, h = _dimensiones(svg)
    with tempfile.TemporaryDirectory(prefix='gagwv_pdf_') as tmp:
        html_path = os.path.join(tmp, 'pagina.html')
        pdf_path = os.path.join(tmp, 'salida.pdf')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(PLANTILLA.format(w=w, h=h, svg=svg))
        cmd = [
            chrome,
            '--headless',
            '--disable-gpu',
            '--no-sandbox',
            '--no-pdf-header-footer',
            f'--print-to-pdf={pdf_path}',
            'file:///' + os.path.abspath(html_path).replace('\\', '/'),
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if r.returncode != 0 or not os.path.exists(pdf_path):
            return None
        with open(pdf_path, 'rb') as f:
            datos = f.read()
    return datos if datos.startswith(b'%PDF') else None
