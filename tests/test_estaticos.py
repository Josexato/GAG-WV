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