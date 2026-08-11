"""Servidor HTTP local de GAG-WV.

Sin dependencias propias: usa http.server de la librería estándar. El
renderizado llama a AlmaGag.generator.generate_diagram escribiendo el
archivo de entrada y el SVG de salida en un directorio temporal.
"""

import glob
import io
import json
import logging
import os
import tempfile
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from gagwv.engine import cargar_generate_diagram

STATIC_DIR = os.path.dirname(os.path.abspath(__file__))

# generate_diagram no es reentrante (logging global, estado de módulo):
# un render a la vez. Para uso local mono-usuario es suficiente.
_render_lock = threading.Lock()

VALID_EXTENSIONS = ('.sdjf', '.gag')


def _label_de_fase(path):
    """'03_columnas-por-flujo.svg' → '03 · columnas por flujo'."""
    nombre = os.path.splitext(os.path.basename(path))[0]
    partes = nombre.split('_', 1)
    if len(partes) == 2 and partes[0].isdigit():
        return f"{partes[0]} · {partes[1].replace('-', ' ').replace('_', ' ')}"
    return nombre.replace('-', ' ').replace('_', ' ')


def _recolectar_fases(tmp):
    """SVGs de la Epifanía escritos bajo <tmp>/debug/ durante el render."""
    fases = []
    patron = os.path.join(tmp, 'debug', '**', '*.svg')
    for path in sorted(glob.glob(patron, recursive=True)):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                fases.append({'label': _label_de_fase(path), 'svg': f.read()})
        except OSError:
            continue
    return fases


def render_source(filename, content, layout_algorithm='select', view='auto',
                  visualdebug=False, visualize_growth=False):
    """Renderiza el contenido de un .sdjf/.gag y devuelve (ok, svg, log, fases).

    ok: bool; svg: str con el XML del SVG (o None si falló); log: str con
    los mensajes WARNING/ERROR del motor durante el render; fases: lista de
    {label, svg} con el flipbook de la Epifanía (vacía si visualize_growth
    está apagado o el motor no capturó fases).
    """
    generate_diagram = cargar_generate_diagram()

    base = os.path.basename(filename) or 'diagrama.sdjf'
    ext = os.path.splitext(base)[1].lower()
    if ext not in VALID_EXTENSIONS:
        base += '.sdjf'

    log_buffer = io.StringIO()
    log_handler = logging.StreamHandler(log_buffer)
    log_handler.setLevel(logging.WARNING)
    log_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))

    with _render_lock:
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        try:
            with tempfile.TemporaryDirectory(prefix='gagwv_') as tmp:
                input_path = os.path.join(tmp, base)
                output_path = os.path.join(tmp, 'salida.svg')
                with open(input_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                # La Epifanía escribe en debug/epifania/ relativo al cwd:
                # entrar al tempdir para que sus SVGs caigan ahí (el lock
                # hace seguro el chdir global durante el render).
                prev_cwd = os.getcwd()
                os.chdir(tmp)
                try:
                    ok = generate_diagram(
                        input_path,
                        output_file=output_path,
                        layout_algorithm=layout_algorithm,
                        view=view,
                        visualdebug=visualdebug,
                        visualize_growth=visualize_growth,
                    )
                except Exception as e:  # el motor no debe tumbar el servidor
                    logging.getLogger(__name__).error(
                        f"Excepción durante el render: {e}")
                    ok = False
                finally:
                    os.chdir(prev_cwd)
                svg = None
                if ok and os.path.exists(output_path):
                    with open(output_path, 'r', encoding='utf-8') as f:
                        svg = f.read()
                elif ok:
                    ok = False
                    log_buffer.write('[ERROR] El motor no produjo el SVG\n')
                fases = _recolectar_fases(tmp) if visualize_growth else []
        finally:
            root_logger.removeHandler(log_handler)

    return bool(ok and svg), svg, log_buffer.getvalue(), fases


class VisorHandler(BaseHTTPRequestHandler):
    server_version = 'GAG-WV/1.0'

    def log_message(self, format, *args):
        # Silenciar el log por request; el terminal queda para el motor.
        pass

    def _send(self, status, body, content_type):
        data = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            index = os.path.join(STATIC_DIR, 'index.html')
            with open(index, 'r', encoding='utf-8') as f:
                self._send(HTTPStatus.OK, f.read(), 'text/html')
        else:
            self._send(HTTPStatus.NOT_FOUND, 'No encontrado', 'text/plain')

    def do_POST(self):
        if self.path != '/render':
            self._send(HTTPStatus.NOT_FOUND, 'No encontrado', 'text/plain')
            return
        try:
            length = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(length).decode('utf-8'))
            filename = payload.get('filename', 'diagrama.sdjf')
            content = payload.get('content', '')
            options = payload.get('options', {})
        except (ValueError, UnicodeDecodeError) as e:
            self._send(HTTPStatus.BAD_REQUEST,
                       json.dumps({'ok': False, 'log': f'Petición inválida: {e}'}),
                       'application/json')
            return

        ok, svg, log, fases = render_source(
            filename, content,
            layout_algorithm=options.get('layout_algorithm', 'select'),
            view=options.get('view', 'auto'),
            visualdebug=bool(options.get('visualdebug', False)),
            visualize_growth=bool(options.get('visualize_growth', False)),
        )
        self._send(HTTPStatus.OK,
                   json.dumps({'ok': ok, 'svg': svg, 'log': log,
                               'phases': fases}),
                   'application/json')


def serve(host='127.0.0.1', port=8321):
    httpd = ThreadingHTTPServer((host, port), VisorHandler)
    print(f"GAG-WV corriendo en http://{host}:{port}  (Ctrl+C para salir)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nVisor detenido.")
    finally:
        httpd.server_close()
