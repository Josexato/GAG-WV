"""Aviso de motor desactualizado.

Compara el AlmaGag local contra el repo oficial en GitHub y devuelve un
estado que la UI muestra como banner. Todo es tolerante a fallos: sin red,
sin git o con API caída el estado es 'unknown' y el visor sigue normal.

Estrategias, en orden:
1. Clon git (caso típico): commit local vs master remoto, con conteo de
   commits de atraso vía el endpoint compare de la API de GitHub.
2. Instalación pip (sin .git): versión instalada vs version= del
   pyproject.toml de master.
"""

import json
import logging
import os
import re
import subprocess
import time
import urllib.request

logger = logging.getLogger(__name__)

REPO = 'Josexato/AlmaGag'
API = f'https://api.github.com/repos/{REPO}'
RAW_PYPROJECT = f'https://raw.githubusercontent.com/{REPO}/master/pyproject.toml'
TIMEOUT = 5          # segundos por petición HTTP
CACHE_TTL = 3600     # re-verificar como mucho una vez por hora

_cache = {'ts': 0.0, 'estado': None}


def _http_json(url):
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'GAG-WV',
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode('utf-8'))


def _http_text(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'GAG-WV'})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode('utf-8')


def _raiz_git_del_motor():
    """Directorio del clon git que contiene el paquete AlmaGag, o None."""
    try:
        # El resolutor configura sys.path (pip, clon hermano o ALMAGAG_PATH)
        from gagwv.engine import cargar_generate_diagram
        cargar_generate_diagram()
        import AlmaGag
        # __file__ es None en namespace packages (sin __init__.py); __path__
        # trae los directorios del paquete (idealmente uno solo).
        rutas = [os.path.abspath(p) for p in AlmaGag.__path__]
    except Exception:
        return None
    for paquete in rutas:
        # .git puede ser directorio (clon) o archivo (worktree/submódulo);
        # probar el propio dir y su padre cubre repo-raíz y paquete anidado.
        for raiz in (os.path.dirname(paquete), paquete):
            if os.path.exists(os.path.join(raiz, '.git')):
                return raiz
    return None


def _commit_local(raiz):
    try:
        out = subprocess.run(
            ['git', '-C', raiz, 'rev-parse', 'HEAD'],
            capture_output=True, text=True, timeout=10)
        sha = out.stdout.strip()
        return sha if out.returncode == 0 and len(sha) == 40 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _estado_por_git(raiz):
    local = _commit_local(raiz)
    if not local:
        return None
    remoto = _http_json(f'{API}/commits/master')
    sha_remoto = remoto.get('sha', '')
    if not sha_remoto:
        return None
    if local == sha_remoto:
        return {'status': 'ok', 'detalle': f'motor al día ({local[:7]})'}

    # Cuántos commits atrás está el local (compare local...master).
    atras = None
    try:
        comp = _http_json(f'{API}/compare/{local}...master')
        atras = comp.get('ahead_by')
    except Exception:
        pass  # commit local no publicado, API limitada, etc.

    ultimo = (remoto.get('commit', {}).get('message') or '').splitlines()[0]
    if atras:
        detalle = (f'{atras} commit(s) atrás de master '
                   f'(último: “{ultimo[:80]}”)')
    else:
        detalle = (f'commit local {local[:7]} ≠ master {sha_remoto[:7]} '
                   f'(último: “{ultimo[:80]}”)')
    return {'status': 'outdated', 'detalle': detalle,
            'como_actualizar': f'git -C "{raiz}" pull'}


def _estado_por_version_pip():
    try:
        from importlib.metadata import version
        local = version('AlmaGag')
    except Exception:
        return None
    m = re.search(r'^version\s*=\s*"([^"]+)"', _http_text(RAW_PYPROJECT),
                  re.MULTILINE)
    if not m:
        return None
    remota = m.group(1)
    if local == remota:
        return {'status': 'ok', 'detalle': f'motor v{local} al día'}
    return {'status': 'outdated',
            'detalle': f'motor v{local} instalado; v{remota} disponible',
            'como_actualizar':
                'pip install --upgrade git+https://github.com/Josexato/AlmaGag'}


def estado_motor(force=False):
    """Estado de actualización del motor: {status, detalle[, como_actualizar]}.

    status ∈ {'ok', 'outdated', 'unknown'}. Cacheado CACHE_TTL segundos.
    """
    if not force and _cache['estado'] and time.time() - _cache['ts'] < CACHE_TTL:
        return _cache['estado']

    estado = None
    try:
        raiz = _raiz_git_del_motor()
        if raiz:
            estado = _estado_por_git(raiz)
        if estado is None:
            estado = _estado_por_version_pip()
    except Exception as e:
        logger.debug(f'verificación de versión falló: {e}')
    if estado is None:
        estado = {'status': 'unknown',
                  'detalle': 'no se pudo verificar (sin red o sin git)'}

    _cache['ts'] = time.time()
    _cache['estado'] = estado
    return estado
