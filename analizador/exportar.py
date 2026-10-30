"""Exportación de resultados a JSON, CSV o Markdown."""

import csv
import json
from pathlib import Path
from typing import Any

from .consultas.registro import Resultado

FORMATOS = ("json", "csv", "md")


def formatos_para(datos: Any) -> tuple[str, ...]:
    """CSV y Markdown necesitan una lista de diccionarios. JSON sirve para cualquier dato."""
    if isinstance(datos, list) and all(isinstance(f, dict) for f in datos):
        return FORMATOS
    return ("json",)


def _celda_md(valor: Any) -> str:
    texto = "" if valor is None else str(valor)
    return texto.replace("|", "\\|").replace("\n", " ")


def _tabla_md(filas: list[dict]) -> str:
    if not filas:
        return "_Sin datos_\n"
    columnas = list(dict.fromkeys(k for f in filas for k in f))
    lineas = ["| " + " | ".join(columnas) + " |", "|" + "---|" * len(columnas)]
    for f in filas:
        lineas.append("| " + " | ".join(_celda_md(f.get(c)) for c in columnas) + " |")
    return "\n".join(lineas) + "\n"


def guardar(resultado: Resultado, formato: str, carpeta: Path, nombre: str) -> Path:
    if formato not in formatos_para(resultado.datos):
        raise ValueError(f"El formato {formato} no es válido para estos datos")
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{nombre}.{formato}"

    if formato == "json":
        ruta.write_text(json.dumps(resultado.datos, ensure_ascii=False, indent=2), encoding="utf-8")
    elif formato == "csv":
        filas = resultado.datos
        columnas = list(dict.fromkeys(k for f in filas for k in f))
        with ruta.open("w", newline="", encoding="utf-8-sig") as fh:
            escritor = csv.DictWriter(fh, fieldnames=columnas, extrasaction="ignore")
            escritor.writeheader()
            for f in filas:
                escritor.writerow({k: ";".join(map(str, v)) if isinstance(v, list) else v for k, v in f.items()})
    else:
        cuerpo = [f"# {resultado.titulo}", ""]
        cuerpo += [f"- {linea}" for linea in resultado.resumen] + [""]
        cuerpo.append(_tabla_md(resultado.datos))
        ruta.write_text("\n".join(cuerpo), encoding="utf-8")
    return ruta
