"""Tests del export a Excel (gagwv/xlsx.py y POST /exportar-xlsx)."""

import http.client
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

sys.path.insert(0, os.path.dirname(__file__))

from gagwv.xlsx import libro_desde_sdjf  # noqa: E402
from test_estaticos import _con_servidor  # noqa: E402

openpyxl = pytest.importorskip('openpyxl', reason='validación con openpyxl')

DATA = {
    'elements': [
        {'id': 'a', 'label': 'Nodo A', 'type': 'cloud', 'color': 'red',
         'contains': [{'id': 'b', 'scope': 'full'}], 'extra': 1},
        {'id': 'b', 'label': 'Nodo B'},
    ],
    'connections': [
        {'from': 'a', 'to': 'b', 'semantic_type': 'dependency',
         'routing': {'type': 'orthogonal'}},
    ],
    'areas': [{'id': 'A1', 'label': 'Zona', 'members': ['a', 'b']}],
    'journeys': [{'id': 'j1', 'label': 'Ruta', 'color': '#fff',
                  'path': ['a', 'b']}],
}


def _hojas(xlsx_bytes):
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    return {ws.title: [[c.value for c in fila] for fila in ws.iter_rows()]
            for ws in wb.worksheets}


def test_libro_cuatro_hojas_con_datos():
    hojas = _hojas(libro_desde_sdjf(DATA))
    assert list(hojas) == ['Elements', 'Connections', 'Areas', 'Journeys']
    assert hojas['Elements'][0][:2] == ['id', 'label']
    assert hojas['Elements'][1][4] == 'b (full)'          # contains legible
    assert hojas['Elements'][1][5] == '{"extra": 1}'      # extras → otros
    assert hojas['Connections'][1][6] == (
        '{"routing": {"type": "orthogonal"}}')
    assert hojas['Areas'][1][3] == 'a, b'
    assert hojas['Journeys'][1][3] == 'a → b'


def test_libro_secciones_vacias_no_revienta():
    hojas = _hojas(libro_desde_sdjf({'elements': []}))
    assert len(hojas) == 4
    assert all(len(filas) == 1 for filas in hojas.values())  # solo cabecera


def test_endpoint_exportar_xlsx():
    def caso(puerto):
        conn = http.client.HTTPConnection('127.0.0.1', puerto, timeout=10)
        conn.request('POST', '/exportar-xlsx',
                     body=json.dumps({'filename': 'demo.sdjf',
                                      'json': json.dumps(DATA)}),
                     headers={'Content-Type': 'application/json'})
        resp = conn.getresponse()
        datos = resp.read()
        conn.close()
        assert resp.status == 200
        assert 'spreadsheetml' in (resp.getheader('Content-Type') or '')
        assert 'demo.xlsx' in (resp.getheader('Content-Disposition') or '')
        assert _hojas(datos)['Connections'][1][0] == 'a'
    _con_servidor(caso)


def test_endpoint_json_invalido_es_400():
    def caso(puerto):
        conn = http.client.HTTPConnection('127.0.0.1', puerto, timeout=10)
        conn.request('POST', '/exportar-xlsx',
                     body=json.dumps({'json': '{roto'}),
                     headers={'Content-Type': 'application/json'})
        resp = conn.getresponse()
        resp.read()
        conn.close()
        assert resp.status == 400
    _con_servidor(caso)
