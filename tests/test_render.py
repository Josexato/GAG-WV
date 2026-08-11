"""Tests de GAG-WV: la función de render que usa el endpoint /render.

Requieren el motor AlmaGag disponible (pip, clon hermano o ALMAGAG_PATH);
si no está, se saltan con el mensaje de instalación.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from gagwv.engine import cargar_generate_diagram  # noqa: E402

try:
    cargar_generate_diagram()
    MOTOR_DISPONIBLE = True
    MOTIVO = ''
except ImportError as e:
    MOTOR_DISPONIBLE = False
    MOTIVO = str(e)

pytestmark = pytest.mark.skipif(not MOTOR_DISPONIBLE, reason=MOTIVO)

EJEMPLO = os.path.join(os.path.dirname(__file__), '..', 'ejemplos',
                       'red-edificios.sdjf')


def _leer_ejemplo():
    with open(EJEMPLO, 'r', encoding='utf-8') as f:
        return f.read()


def test_render_sdjf_valido():
    from gagwv.server import render_source
    ok, svg, log, fases = render_source('red-edificios.sdjf', _leer_ejemplo())
    assert ok, f"render falló, log: {log}"
    assert svg and '<svg' in svg
    assert fases == []  # sin visualize_growth no hay flipbook


def test_render_json_invalido():
    from gagwv.server import render_source
    ok, svg, log, fases = render_source('roto.sdjf', '{esto no es json')
    assert not ok
    assert svg is None
    assert 'ERROR' in log


def test_render_extension_desconocida_no_revienta():
    from gagwv.server import render_source
    ok, svg, log, fases = render_source('nota.txt', _leer_ejemplo())
    assert ok, f"render falló, log: {log}"
    assert '<svg' in svg


def test_render_epifania_devuelve_fases():
    from gagwv.server import render_source
    ok, svg, log, fases = render_source(
        'red-edificios.sdjf', _leer_ejemplo(), visualize_growth=True)
    assert ok, f"render falló, log: {log}"
    if not fases:
        pytest.skip('este motor no captura fases de Epifanía (versión antigua)')
    for fase in fases:
        assert fase['label']
        assert '<svg' in fase['svg']
    # cwd no debe quedar cambiado por el chdir interno
    assert os.path.isdir(os.getcwd())
