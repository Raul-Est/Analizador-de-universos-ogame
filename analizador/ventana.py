"""Ventana de seguimiento en vivo: verde para puntos destruidos, rojo para puntos perdidos."""

import queue
import threading

from .seguimiento import (
    Seguimiento,
    aplanar_historial,
    formatear_fecha,
    formatear_hora,
    formatear_puntos,
)

FONDO = "#2b3036"
PANEL = "#333a41"
VERDE = "#5dff6b"
ROJO = "#ff5c5c"
AZUL = "#3ea6ff"
GRIS = "#bac3cf"


def _segmentos(actualizacion: dict) -> list[tuple[str, str]]:
    """Texto de una actualización como pares (texto, etiqueta de color)."""
    segmentos = [
        (f"Hora {formatear_hora(actualizacion['hora'])}   Fecha {formatear_fecha(actualizacion['hora'])}", "titulo"),
        (f"   (cambios desde las {formatear_hora(actualizacion['desde'])})\n", "info"),
    ]
    if not actualizacion["filas"]:
        segmentos.append(("Sin cambios en puntos destruidos ni perdidos\n", "info"))
    for fila in actualizacion["filas"]:
        segmentos.append((f"{formatear_puntos(fila['puntos']):>14}", "verde" if fila["puntos"] > 0 else "rojo"))
        segmentos.append((f"  {fila['nombre'][:24]:<24}", "nombre"))
        segmentos.append((f" [{fila['alianza']}]\n" if fila["alianza"] else "\n", "alianza"))
    segmentos.append(("\n", "info"))
    return segmentos


def abrir(contexto, top: int = 10) -> list[dict]:
    """Abre la ventana y bloquea hasta que se cierra. Devuelve los cambios recibidos (filas planas)."""
    try:
        import tkinter as tk
    except ImportError as exc:
        raise ValueError("Esta instalación de Python no incluye tkinter, necesario para la ventana.") from exc

    cola: queue.Queue = queue.Queue()
    seguimiento = Seguimiento(
        contexto,
        top,
        lambda actualizacion: cola.put(("actualizacion", actualizacion)),
        lambda texto: cola.put(("estado", texto)),
    )

    try:
        raiz = tk.Tk()
    except tk.TclError as exc:
        raise ValueError(f"No se pudo abrir la ventana: {exc}") from exc
    raiz.title(f"Seguimiento en vivo - {contexto.universo}")
    raiz.configure(bg=FONDO)
    raiz.geometry("580x640")

    cabecera = tk.Label(
        raiz, text=f"Puntos destruidos / perdidos - {contexto.universo}", bg=PANEL, fg=GRIS,
        font=("Segoe UI", 13, "bold"), anchor="w", padx=12, pady=8,
    )
    cabecera.pack(fill="x", padx=8, pady=(8, 0))

    marco = tk.Frame(raiz, bg=PANEL)
    marco.pack(fill="both", expand=True, padx=8, pady=8)
    texto = tk.Text(
        marco, bg=PANEL, fg=GRIS, bd=0, highlightthickness=0, wrap="none", cursor="arrow",
        font=("Consolas", 11), padx=12, pady=8,
    )
    barra = tk.Scrollbar(marco, command=texto.yview)
    texto.configure(yscrollcommand=barra.set)
    barra.pack(side="right", fill="y")
    texto.pack(side="left", fill="both", expand=True)
    texto.tag_configure("verde", foreground=VERDE)
    texto.tag_configure("rojo", foreground=ROJO)
    texto.tag_configure("nombre", foreground=AZUL)
    texto.tag_configure("alianza", foreground=AZUL, font=("Consolas", 11, "italic"))
    texto.tag_configure("titulo", foreground=GRIS, font=("Consolas", 11, "bold"))
    texto.tag_configure("info", foreground="#8a94a0")
    texto.insert("1.0", "Esperando la primera actualización de la API...\n"
                        "(el highscore se regenera cada hora; en cuanto cambie se descarga y aparece aquí)\n", "info")
    texto.configure(state="disabled")

    estado = tk.Label(raiz, text="Conectando...", bg=FONDO, fg="#8a94a0", font=("Segoe UI", 9), anchor="w", padx=10)
    estado.pack(fill="x", pady=(0, 6))

    recibidas = {"n": 0}

    def mostrar(actualizacion: dict) -> None:
        texto.configure(state="normal")
        if recibidas["n"] == 0:
            texto.delete("1.0", "end")
        recibidas["n"] += 1
        for contenido, etiqueta in reversed(_segmentos(actualizacion)):
            texto.insert("1.0", contenido, etiqueta)
        texto.configure(state="disabled")
        cabecera.configure(
            text=f"Hora {formatear_hora(actualizacion['hora'])}   Fecha {formatear_fecha(actualizacion['hora'])}"
        )

    def vaciar_cola() -> None:
        try:
            while True:
                tipo, contenido = cola.get_nowait()
                if tipo == "actualizacion":
                    mostrar(contenido)
                else:
                    estado.configure(text=contenido)
        except queue.Empty:
            pass
        raiz.after(250, vaciar_cola)

    raiz.after(250, vaciar_cola)
    hilo = threading.Thread(target=seguimiento.ejecutar, daemon=True)
    hilo.start()
    try:
        raiz.mainloop()
    finally:
        seguimiento.parar.set()
    return aplanar_historial(seguimiento.historial)
