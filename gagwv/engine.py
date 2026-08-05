"""Resolución del motor AlmaGag.

GAG-WV no incluye el motor: lo busca en este orden:
1. `AlmaGag` ya importable (instalado con pip).
2. La ruta indicada en la variable de entorno ALMAGAG_PATH.
3. Un clon hermano `../AlmaGag` junto a este repo.
"""

import importlib
import os
import sys

_CANDIDATOS = []
if os.environ.get('ALMAGAG_PATH'):
    _CANDIDATOS.append(os.environ['ALMAGAG_PATH'])
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CANDIDATOS.append(os.path.join(os.path.dirname(_REPO_ROOT), 'AlmaGag'))

AYUDA_INSTALACION = """\
No se encontró el motor AlmaGag. Opciones:
  pip install git+https://github.com/Josexato/AlmaGag
  — o —
  git clone https://github.com/Josexato/AlmaGag junto a este repo
  — o —
  export ALMAGAG_PATH=/ruta/a/AlmaGag (el directorio que contiene AlmaGag/)"""


def cargar_generate_diagram():
    """Devuelve la función generate_diagram del motor, o lanza ImportError."""
    try:
        return importlib.import_module('AlmaGag.generator').generate_diagram
    except ImportError:
        pass
    for ruta in _CANDIDATOS:
        # ALMAGAG_PATH puede apuntar al repo (contiene AlmaGag/) o al paquete.
        for base in (ruta, os.path.dirname(ruta)):
            if os.path.isdir(os.path.join(base, 'AlmaGag')) and base not in sys.path:
                sys.path.insert(0, base)
        try:
            return importlib.import_module('AlmaGag.generator').generate_diagram
        except ImportError:
            continue
    raise ImportError(AYUDA_INSTALACION)
