# Analizador de universos OGame

Herramienta en Python para consultar la API pública de OGame en cualquier universo.
Pensada para universos grandes y circulares (donut), como Xolotlan (279).

## Requisitos

- Python 3.10 o superior
- `pip install -r requirements.txt` (solo depende de `requests`)

## Configurar el universo

Edita `universo.json`:

```json
{
  "idioma": "es",
  "numero": 268,
  "pausa_segundos": 0.1
}
```

También puedes indicarlo al ejecutar, sin tocar el fichero: `--universo idioma:numero`.

> Xolotlan (279) existe en los idiomas `de`, `en`, `fr` e `it` (no en `es`). Para usarlo, pon su idioma, por ejemplo `"idioma": "de", "numero": 279`.

## Uso

Menú interactivo:

```powershell
python -m analizador
```

Desde la línea de comandos:

```powershell
python -m analizador listar
python -m analizador --universo es:268 ejecutar servidor
python -m analizador ejecutar ranking --param categoria=1 --param tipo=3 --param limite=50 --formato csv
python -m analizador ejecutar distancia --param origen=1:1:1 --param destino=6:499:1
```

Los ficheros exportados se guardan en `output/<idioma>-<numero>/` con la fecha en el nombre (por ejemplo `ranking_30-10-2026.csv`); en Markdown el título también lleva la fecha (`30/10/2026`). `pausa_segundos` es el intervalo mínimo entre peticiones (0,25 s por defecto); si la API responde 503/429 el programa se ralentiza solo (la API aguanta ~1 petición/s de forma sostenida). Los datos de jugadores se guardan en `output/.cache/` durante 6 horas, así que repetir consultas es casi instantáneo (borra esa carpeta para forzar la descarga).

## Consultas disponibles

| Id                       | Qué hace                                              |
| ------------------------ | ----------------------------------------------------- |
| `servidor`               | Galaxias, sistemas y si el universo es circular       |
| `universos_lobby`        | Lista de universos del lobby (filtro por idioma)      |
| `jugadores` / `alianzas` | Listados completos                                    |
| `ranking`                | Highscore por categoría (jugadores/alianzas) y tipo   |
| `alianza_miembros`       | Miembros de una alianza con puntos y naves            |
| `jugador_detalle`        | Planetas y lunas de un jugador                        |
| `top_lunas`              | Jugadores del top con lunas y sus coordenadas         |
| `alianza_top_lunas`      | Coordenadas de lunas de una alianza                   |
| `distribucion_galaxias`  | Planetas del top de flota por galaxia                 |
| `distancia`              | Distancia en galaxias y sistemas, respetando el donut |

## Añadir una consulta nueva

1. Crea una función en `analizador/consultas/` (o añádela a un módulo existente).
2. Decórala con `@consulta(id, descripcion, parametros)`. Recibe `contexto` y los parámetros, y devuelve un `Resultado`.
3. Importa el módulo en `analizador/consultas/__init__.py` si es un fichero nuevo.

```python
from .registro import Parametro, Resultado, consulta

@consulta("mi_consulta", "Descripción corta",
          (Parametro("limite", "Número de filas", int, 20),))
def mi_consulta(contexto, limite=20):
    datos = contexto.highscore(1, 3)[:limite]
    return Resultado(datos=datos, titulo="Mi consulta", resumen=[f"Filas: {len(datos)}"])
```

Usa `contexto` para obtener datos ya cacheados: `jugadores()`, `alianzas()`, `highscore(categoria, tipo)`, `detalle_jugador(id)`, `detalles(ids)`, `servidor()`, `resolver_jugador(texto)`, `resolver_alianza(texto)`.

Los endpoints y su formato están documentados en [docs/api.md](docs/api.md).

## Tests

```powershell
python -m unittest
```

Los tests no usan la red.

## Iniciar el programa

& "C:\Users\siemp\AppData\Local\Programs\Python\Python312\python.exe" -m analizador

& "C:\Users\siemp\AppData\Local\Programs\Python\Python312\python.exe" -m analizador
