import argparse
import sys
import threading
import webbrowser

from gagwv.engine import cargar_generate_diagram
from gagwv.server import serve


def main():
    parser = argparse.ArgumentParser(
        prog='gagwv',
        description="GAG-WV: visor web local para diagramas AlmaGag (.sdjf/.gag)."
    )
    parser.add_argument('--host', default='127.0.0.1',
                        help="Host de escucha (default: 127.0.0.1, solo local)")
    parser.add_argument('--port', type=int, default=8321,
                        help="Puerto de escucha (default: 8321)")
    parser.add_argument('--no-browser', action='store_true',
                        help="No abrir el navegador automáticamente")
    args = parser.parse_args()

    # Verificar el motor ANTES de servir, para fallar con un mensaje claro.
    try:
        cargar_generate_diagram()
    except ImportError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if not args.no_browser:
        url = f"http://{args.host}:{args.port}"
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()

    serve(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
