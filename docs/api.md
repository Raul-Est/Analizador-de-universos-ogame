# Endpoints de la API de OGame usados

Base por universo: `https://s{numero}-{idioma}.ogame.gameforge.com/api/`. Añade `?toJson=1` para recibir JSON.

Si el universo no existe o no está abierto, la web responde con HTML (código 200). El cliente lo detecta y muestra un error claro.

| Endpoint | Parámetros | Contenido |
| --- | --- | --- |
| `serverData.xml` | — | Configuración: `galaxies`, `systems`, `donutGalaxy`, `donutSystem`, `speed`, `version` |
| `players.xml` | — | Jugadores: `player` con `@attributes` (`id`, `name`, `status`, `alliance`) |
| `alliances.xml` | — | Alianzas: `alliance` con `id`, `name`, `tag` |
| `highscore.xml` | `category` (1 jugadores, 2 alianzas), `type` (0-7) | Posiciones con `position`, `score`, `ships` |
| `playerData.xml` | `id` | Planetas (`planets.planet`) con `coords` y `moon` |

Tipos de highscore: 0 economía, 1 investigación, 2 flota, 3 militar, 4 militar construido, 5 militar destruido, 6 honor, 7 pérdidas.

Lobby (lista de universos, fuera de la API del universo): `https://lobby.ogame.gameforge.com/api/servers`.

## Notas

- OGame devuelve un objeto en lugar de una lista cuando solo hay un elemento. Por eso se normaliza con `elementos()` en `analizador/normalizacion.py`.
- `playerData.xml` tiene una petición por jugador. Consultar el top 200 hace hasta 200 peticiones, por eso hay una pausa configurable (`pausa_segundos`).
- Universos circulares (donut): la distancia entre galaxias o sistemas es la menor de las dos vueltas posibles (`analizador/geometria.py`).
