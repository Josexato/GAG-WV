"""Tests del aviso de motor desactualizado.

Sin depender de la red: pase lo que pase (sin conexión, API caída, motor
instalado de cualquier forma), estado_motor debe devolver un dict bien
formado y nunca lanzar.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from gagwv.actualizacion import estado_motor, _cache  # noqa: E402


def test_estado_motor_siempre_devuelve_dict_valido():
    estado = estado_motor(force=True)
    assert estado['status'] in ('ok', 'outdated', 'unknown')
    assert estado['detalle']
    if estado['status'] == 'outdated':
        assert 'como_actualizar' in estado


def test_estado_motor_usa_cache():
    e1 = estado_motor(force=True)
    marca = _cache['ts']
    e2 = estado_motor()
    assert e2 is e1
    assert _cache['ts'] == marca
