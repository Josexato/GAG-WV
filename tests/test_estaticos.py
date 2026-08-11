"""Tests del servido de archivos estáticos (CodeMirror vendoreado)."""

import http.client
import os
import sys
import threading

from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from gagwv.server import VisorHandler  # noqa: E402


def _con_servidor(fn):
    srv = ThreadingHTTPServer(('127.0.0.1', 0), VisorHandler)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    try:
        return fn(srv.server_address[1])
    finally:
        srv.shutdown()
        srv.server_close()


def _get(puerto, ruta):
    conn = http.client.HTTPConnection('127.0.0.1', puerto, timeout=5)
    conn.request('GET', ruta)
    resp = conn.getresponse()
    cuerpo = resp.read()
    conn.close()
    return resp.status, cuerpo


def test_sirve_codemirror():
    def caso(puerto):
        status, cuerpo = _get(puerto, '/static/codemirror/codemirror.min.js')
        assert status == 200
        assert b'CodeMirror' in cuerpo
    _con_servidor(caso)


def test_bloquea_path_traversal():
    def caso(puerto):
        # http.client normaliza '..', así que se arma la petición cruda
        import socket
        s = socket.create_connection(('127.0.0.1', puerto), timeout=5)
        s.sendall(b'GET /static/../server.py HTTP/1.1\r\n'
                  b'Host: x\r\nConnection: close\r\n\r\n')
        datos = b''
        while True:
            trozo = s.recv(4096)
            if not trozo:
                break
            datos += trozo
        s.close()
        assert b'404' in datos.split(b'\r\n')[0]
        assert b'render_source' not in datos
    _con_servidor(caso)


def test_extension_desconocida_404():
    def caso(puerto):
        status, _ = _get(puerto, '/static/codemirror/LICENSE-NOTICE.md')
        assert status == 404
    _con_servidor(caso)


def test_exportar_zip():
    import io
    import json
    import zipfile

    def caso(puerto):
        cuerpo = json.dumps({
            'filename': 'mi-diagrama.sdjf',
            'json': '{"elements": []}',
            'svg': '<svg xmlns="http://www.w3.org/2000/svg"/>',
            'fases': [{'label': '01', 'svg': '<svg/>'}],
        })
        conn = http.client.HTTPConnection('127.0.0.1', puerto, timeout=10)
        conn.request('POST', '/exportar', body=cuerpo,
                     headers={'Content-Type': 'application/json'})
        resp = conn.getresponse()
        datos = resp.read()
        assert resp.status == 200
        assert resp.getheader('Content-Type') == 'application/zip'
        assert 'mi-diagrama_analisis_' in (
            resp.getheader('Content-Disposition') or '')
        conn.close()
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            nombres = set(z.namelist())
            assert {'mi-diagrama.sdjf', 'mi-diagrama.svg', 'INFO.txt',
                    'epifania/01.svg'} == nombres
            assert b'GAG-WV' in z.read('INFO.txt')
    _con_servidor(caso)


def test_exportar_pdf():
    import json

    from gagwv.pdf import buscar_chrome
    import pytest
    if not buscar_chrome():
        pytest.skip('sin Chrome/Chromium en este entorno')

    def caso(puerto):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="200" '
               'height="100"><rect width="200" height="100" fill="red"/></svg>')
        conn = http.client.HTTPConnection('127.0.0.1', puerto, timeout=90)
        conn.request('POST', '/exportar-pdf',
                     body=json.dumps({'filename': 'demo.sdjf', 'svg': svg}),
                     headers={'Content-Type': 'application/json'})
        resp = conn.getresponse()
        datos = resp.read()
        conn.close()
        assert resp.status == 200
        assert resp.getheader('Content-Type') == 'application/pdf'
        assert 'demo.pdf' in (resp.getheader('Content-Disposition') or '')
        assert datos.startswith(b'%PDF')
    _con_servidor(caso)


def test_exportar_sin_svg_es_400():
    def caso(puerto):
        import json
        conn = http.client.HTTPConnection('127.0.0.1', puerto, timeout=10)
        conn.request('POST', '/exportar',
                     body=json.dumps({'json': '{}'}),
                     headers={'Content-Type': 'application/json'})
        resp = conn.getresponse()
        resp.read()
        assert resp.status == 400
        conn.close()
    _con_servidor(caso)