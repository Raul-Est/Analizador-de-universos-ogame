"""Interfaz de línea de comandos: menú interactivo y subcomandos."""

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

from .cliente import ClienteOgame, ErrorApi
from .config import CARPETA_SALIDA, Configuracion, Universo, cargar_configuracion
from .consultas import CONSULTAS
from .consultas.registro import Consulta, Parametro, Resultado, obtener_parametros
from .contexto import Contexto
from .exportar import FORMATOS, formatos_para, guardar


def crear_contexto(universo: Universo, pausa: float) -> Contexto:
    return Contexto(
        universo,
        ClienteOgame(universo, pausa_segundos=pausa),
        CARPETA_SALIDA / ".cache" / universo.clave,
        CARPETA_SALIDA / ".estado" / universo.clave,
    )


def ejecutar(contexto: Contexto, consulta_: Consulta, crudos: dict[str, Any]) -> Resultado:
    valores = obtener_parametros(consulta_, crudos)
    try:
        return consulta_.funcion(contexto, **valores)
    finally:
        contexto.guardar_cache()


def mostrar(resultado: Resultado) -> None:
    print(f"\n== {resultado.titulo} ==")
    for linea in resultado.resumen:
        print(f"  {linea}")
    datos = resultado.datos
    if isinstance(datos, list):
        for fila in datos[:50]:
            print(f"  {fila}")
        if len(datos) > 50:
            print(f"  ... ({len(datos) - 50} más; usa --formato para exportarlas)")
    else:
        print(f"  {datos}")


def _pedir(parametro: Parametro) -> Any:
    defecto = "" if parametro.defecto is None else parametro.defecto
    sufijo = f" [{defecto}]" if defecto != "" else ""
    while True:
        respuesta = input(f"  {parametro.nombre}{sufijo} - {parametro.descripcion}: ").strip()
        if not respuesta:
            if parametro.obligatorio and defecto == "":
                print("    Este parámetro es obligatorio.")
                continue
            return defecto
        return respuesta


def _carpeta_exportacion(resultado: Resultado, base: Path, universo: Universo) -> Path:
    carpeta = base / universo.clave
    return carpeta / resultado.subcarpeta if resultado.subcarpeta else carpeta


def _exportar_interactivo(resultado: Resultado, consulta_: Consulta, universo: Universo, carpeta) -> None:
    if not resultado.datos:
        return
    formatos = formatos_para(resultado.datos)
    if len(formatos) == 1:
        return
    eleccion = input(f"Exportar a ({'/'.join(formatos)}) o Enter para no exportar: ").strip().lower()
    if eleccion in formatos:
        ruta = guardar(resultado, eleccion, _carpeta_exportacion(resultado, carpeta, universo), resultado.nombre_archivo or consulta_.id)
        print(f"Guardado en {ruta}")


def menu(contexto: Contexto, configuracion: Configuracion) -> Universo:
    universo = contexto.universo
    ids = list(CONSULTAS)
    while True:
        titulo = f"=== Analizador de universos OGame - {universo} ==="
        lineas = [f"  {i:>2}. {CONSULTAS[id_].descripcion}  [{id_}]" for i, id_ in enumerate(ids, 1)]
        ancho = max(len(linea) for linea in lineas)
        print(f"\n{titulo.center(ancho).rstrip()}\n")
        for i, (id_, linea) in enumerate(zip(ids, lineas), 1):
            print(linea)
            if i % 5 == 0:
                print()
        if len(ids) % 5:
            print()
        print("   u. Cambiar de universo")
        print("   q. Salir")
        opcion = input("Elige una opción: ").strip().lower()
        if opcion == "q":
            return universo
        if opcion == "u":
            nuevo = input("Universo (idioma:numero, ej. es:268): ").strip()
            try:
                universo_nuevo = Universo.desde_texto(nuevo)
                nuevo_ctx = crear_contexto(universo_nuevo, configuracion.pausa_segundos)
                nuevo_ctx.servidor()
            except (ValueError, ErrorApi) as exc:
                print(f"No se pudo cambiar de universo: {exc}")
                continue
            contexto, universo = nuevo_ctx, universo_nuevo
            print(f"Universo activo: {universo}")
            continue
        if not opcion.isdigit() or not 1 <= int(opcion) <= len(ids):
            print("Opción no válida.")
            continue
        consulta_ = CONSULTAS[ids[int(opcion) - 1]]
        crudos = {p.nombre: _pedir(p) for p in consulta_.parametros}
        try:
            resultado = ejecutar(contexto, consulta_, crudos)
        except (ValueError, ErrorApi) as exc:
            print(f"Error: {exc}")
            continue
        mostrar(resultado)
        _exportar_interactivo(resultado, consulta_, universo, configuracion.carpeta_salida)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="analizador", description="Analizador de universos OGame")
    p.add_argument("--universo", help="Universo idioma:numero (sobrescribe universo.json)")
    p.add_argument("--pausa", type=float, help="Segundos entre peticiones a la API")
    sub = p.add_subparsers(dest="orden")
    sub.add_parser("listar", help="Lista las consultas disponibles")
    ej = sub.add_parser("ejecutar", help="Ejecuta una consulta")
    ej.add_argument("id", help="Id de la consulta (ver 'listar')")
    ej.add_argument("--param", action="append", default=[], metavar="CLAVE=VALOR")
    ej.add_argument("--formato", choices=FORMATOS)
    ej.add_argument("--nombre", help="Nombre del fichero exportado (por defecto, el id)")
    ej.add_argument("--carpeta", help="Carpeta de salida (por defecto output/<universo>)")
    return p


def _params_desde_cli(valores: list[str]) -> dict[str, str]:
    crudos = {}
    for par in valores:
        if "=" not in par:
            raise ValueError(f"Parámetro mal formado: {par!r}. Usa CLAVE=VALOR")
        clave, valor = par.split("=", 1)
        crudos[clave.strip()] = valor
    return crudos


def main(argv: Optional[list[str]] = None) -> int:
    args = _parser().parse_args(argv)
    configuracion = cargar_configuracion()
    universo = Universo.desde_texto(args.universo) if args.universo else configuracion.universo
    pausa = args.pausa if args.pausa is not None else configuracion.pausa_segundos
    configuracion = Configuracion(universo, pausa, configuracion.carpeta_salida)

    if args.orden == "listar":
        for id_, c in CONSULTAS.items():
            print(f"{id_:<20} {c.descripcion}")
            for p in c.parametros:
                print(f"    --param {p.nombre}=...  {p.descripcion}")
        return 0

    contexto = crear_contexto(universo, pausa)
    try:
        if args.orden == "ejecutar":
            if args.id not in CONSULTAS:
                print(f"Consulta desconocida: {args.id}. Usa 'listar'.", file=sys.stderr)
                return 2
            consulta_ = CONSULTAS[args.id]
            resultado = ejecutar(contexto, consulta_, _params_desde_cli(args.param))
            mostrar(resultado)
            if args.formato:
                carpeta = (
                    _carpeta_exportacion(resultado, configuracion.carpeta_salida, universo)
                    if not args.carpeta else Path(args.carpeta)
                )
                ruta = guardar(resultado, args.formato, carpeta, args.nombre or resultado.nombre_archivo or consulta_.id)
                print(f"Guardado en {ruta}")
            return 0
        menu(contexto, configuracion)
        return 0
    except (ValueError, ErrorApi) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelado.")
        return 130
