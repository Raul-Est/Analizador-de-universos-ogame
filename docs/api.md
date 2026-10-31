# Endpoints de la API de OGame usados

Base por universo: `https://s{numero}-{idioma}.ogame.gameforge.com/api/`. Añade `?toJson=1` para recibir JSON.

Si el universo no existe o no está abierto, la web responde con HTML (código 200). El cliente lo detecta y muestra un error claro.

| Endpoint | Parámetros | Contenido |
| --- | --- | --- |
| `serverData.xml` | — | Configuración: `galaxies`, `systems`, `donutGalaxy`, `donutSystem`, `speed`, `version` |
| `players.xml` | — | Jugadores: `player` con `@attributes` (`id`, `name`, `status`, `alliance`). `status` combina letras: vacío activo, `i` inactivo 7 días, `I` inactivo 28+ días, `v` vacaciones, `b` bloqueado, `a` admin |
| `alliances.xml` | — | Alianzas: `alliance` con `id`, `name`, `tag` |
| `highscore.xml` | `category` (1 jugadores, 2 alianzas), `type` (0-7) | Posiciones con `position`, `score`, `ships` |
| `playerData.xml` | `id` | Planetas (`planets.planet`) con `coords` y `moon` |

Tipos de highscore: 0 total, 1 economía, 2 investigación, 3 militar, 4 militar perdido, 5 militar construido, 6 militar destruido, 7 honor (puede ser negativo). Comprobado con datos reales: militar (3) = construido (5) − perdido (4). Cada respuesta incluye en `@attributes` un `timestamp` Unix con el momento en que se generó.

El highscore se regenera **cada hora** (cabeceras `Last-Modified` y `Expires = Last-Modified + 1 h`); `players.xml` y `serverData.xml` cada 12-24 h. El seguimiento en vivo se apoya en esto: calcula cuándo toca la siguiente actualización y la descarga en cuanto cambia el `timestamp`.

Lobby (lista de universos, fuera de la API del universo): `https://lobby.ogame.gameforge.com/api/servers`.

## Notas

- OGame devuelve un objeto en lugar de una lista cuando solo hay un elemento. Por eso se normaliza con `elementos()` en `analizador/normalizacion.py`.
- `playerData.xml` tiene una petición por jugador. Consultar el top 200 hace hasta 200 peticiones, por eso hay una pausa mínima configurable (`pausa_segundos`), un ajuste automático ante 503/429 (límite sostenido ≈ 1 petición/s) y una caché en disco de 6 horas.
- Universos circulares (donut): la distancia entre galaxias o sistemas es la menor de las dos vueltas posibles (`analizador/geometria.py`).
