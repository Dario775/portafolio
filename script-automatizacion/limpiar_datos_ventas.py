#!/usr/bin/env python3
"""
Demo S2 — Limpieza de datos de ventas + informe automático.

Qué hace:
  1. Lee un CSV de ventas (datos sucios: espacios, duplicados, fechas mezcladas,
     precios con símbolos, emails inválidos, filas vacías).
  2. Normaliza y valida cada fila.
  3. Elimina duplicados exactos.
  4. Escribe ventas_limpias.csv y un resumen de negocio en resumen_ventas.txt.

Sin dependencias externas: solo la biblioteca estándar de Python.
Uso:
  python3 limpiar_datos_ventas.py datos_muestra_ventas.csv
"""

import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

# Columnas esperadas en el CSV de entrada
CAMPOS = ["fecha", "producto", "cantidad", "precio_unitario", "email_cliente"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def parse_fecha(valor: str):
    """Acepta dd/mm/aaaa, d/m/aaaa e ISO aaaa-mm-dd. Devuelve ISO o None."""
    v = valor.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(v, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_precio(valor: str):
    """Limpia símbolos, espacios y comas decimales. Devuelve float o None."""
    v = valor.strip().replace("$", "").replace(" ", "")
    if "," in v and "." not in v:
        v = v.replace(",", ".")
    try:
        return round(float(v), 2)
    except ValueError:
        return None


def parse_cantidad(valor: str):
    try:
        return int(float(valor.strip()))
    except (ValueError, TypeError):
        return None


def limpiar_fila(fila):
    """Devuelve dict normalizado o None si la fila es inválida."""
    if not any((fila.get(c) or "").strip() for c in CAMPOS):
        return None  # fila completamente vacía

    fecha = parse_fecha(fila.get("fecha", ""))
    producto = " ".join(fila.get("producto", "").split())
    cantidad = parse_cantidad(fila.get("cantidad", ""))
    precio = parse_precio(fila.get("precio_unitario", ""))
    email = fila.get("email_cliente", "").strip().lower()

    if not (fecha and producto and cantidad is not None and precio is not None
            and email and EMAIL_RE.match(email)):
        return None  # dato requerido ausente o con formato inválido

    return {
        "fecha": fecha,
        "producto": producto,
        "cantidad": cantidad,
        "precio_unitario": precio,
        "email_cliente": email,
    }


def main():
    parser = argparse.ArgumentParser(description="Limpieza de ventas (demo S2)")
    parser.add_argument("entrada", help="Ruta al CSV de ventas")
    parser.add_argument("--salida", default="ventas_limpias.csv")
    parser.add_argument("--resumen", default="resumen_ventas.txt")
    args = parser.parse_args()

    ruta = Path(args.entrada)
    if not ruta.exists():
        raise SystemExit(f"No existe el archivo: {ruta}")

    limpias, invalidas, duplicados = [], [], 0
    vistas = set()
    total_filas = 0

    with ruta.open(newline="", encoding="utf-8-sig") as fh:
        lector = csv.DictReader(fh)
        faltantes = [c for c in CAMPOS if c not in (lector.fieldnames or [])]
        if faltantes:
            raise SystemExit(f"Faltan columnas en el CSV: {', '.join(faltantes)}")

        for fila in lector:
            total_filas += 1
            limpia = limpiar_fila(fila)
            if limpia is None:
                invalidas.append(fila)
                continue
            clave = (limpia["fecha"], limpia["producto"],
                     limpia["cantidad"], limpia["precio_unitario"],
                     limpia["email_cliente"])
            if clave in vistas:
                duplicados += 1
                continue
            vistas.add(clave)
            limpias.append(limpia)

    # Escribir CSV limpio
    with Path(args.salida).open("w", newline="", encoding="utf-8") as fh:
        escritor = csv.DictWriter(fh, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(limpias)

    # Calcular resumen
    ingresos_totales = sum(f["cantidad"] * f["precio_unitario"] for f in limpias)
    por_producto, por_mes = {}, {}
    for f in limpias:
        subtotal = f["cantidad"] * f["precio_unitario"]
        p = por_producto.setdefault(f["producto"], {"unidades": 0, "ingresos": 0.0})
        p["unidades"] += f["cantidad"]
        p["ingresos"] = round(p["ingresos"] + subtotal, 2)
        mes = f["fecha"][:7]  # aaaa-mm
        m = por_mes.setdefault(mes, {"operaciones": 0, "ingresos": 0.0})
        m["operaciones"] += 1
        m["ingresos"] = round(m["ingresos"] + subtotal, 2)

    lineas = [
        "RESUMEN DE VENTAS — informe generado automáticamente",
        f"Fuente: {ruta.name}",
        "",
        f"Filas totales en el archivo:       {total_filas}",
        f"Filas válidas procesadas:          {len(limpias)}",
        f"Duplicados eliminados:             {duplicados}",
        f"Filas inválidas descartadas:       {len(invalidas)}",
        f"Ingresos totales (válidos):        ${ingresos_totales:,.2f}",
        "",
        "Ingresos por producto:",
    ]
    for prod, d in sorted(por_producto.items(), key=lambda x: -x[1]["ingresos"]):
        lineas.append(f"  - {prod}: {d['unidades']} un. · ${d['ingresos']:,.2f}")
    lineas.append("")
    lineas.append("Ingresos por mes:")
    for mes, d in sorted(por_mes.items()):
        anio, num = mes.split("-")
        nombre = MESES[int(num)]
        lineas.append(f"  - {nombre.capitalize()} {anio}: {d['operaciones']} op. · ${d['ingresos']:,.2f}")

    with Path(args.resumen).open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")

    print("\n".join(lineas))
    print(f"\n✔ Generados: {args.salida} y {args.resumen}")


if __name__ == "__main__":
    main()
