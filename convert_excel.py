# convert_excel.py
# Lee data/productos.xlsx y genera data/catalogo.json agrupando variantes por código.
# No modifica tu Excel original.

import pandas as pd
import json, re, unicodedata
from collections import OrderedDict

INPUT = "data/productos.xlsx"
OUTPUT_JSON = "data/catalogo.json"

def normalize_key(s):
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def main():
    # Leer la primera hoja
    df = pd.read_excel(INPUT, sheet_name=0, dtype=str).fillna("")
    orig_cols = list(df.columns)

    # Mapas entre nombre normalizado <-> nombre original (para mantener cabeceras legibles)
    norm_cols = [normalize_key(c) for c in orig_cols]
    norm_to_orig = dict(zip(norm_cols, orig_cols))
    orig_to_norm = dict(zip(orig_cols, norm_cols))

    # Renombrar columnas internamente a normalizadas
    df.columns = norm_cols

    # Detectar columnas clave (prueba varias opciones)
    candidates_code = ["codigo","cod","sku","id","ref","referencia"]
    candidates_name = ["nombre","producto","titulo","descripcion_corta"]
    candidates_desc = ["descripcion","detalle","descripcion_larga","observacion"]
    candidates_image = ["imagen","foto","img","imagen_url","url_imagen"]

    def find_col(cands):
        for c in cands:
            if c in df.columns:
                return c
        return None

    code_col = find_col(candidates_code)
    name_col = find_col(candidates_name)
    desc_col = find_col(candidates_desc)
    image_col = find_col(candidates_image)

    # Si no hay código, generar uno a partir del índice
    if code_col is None:
        code_col = "_generated_code"
        df[code_col] = ["no_code_%d" % i for i in range(len(df))]

    # Agrupar por código
    products = OrderedDict()
    for idx, row in df.iterrows():
        code = str(row.get(code_col, "")).strip() or f"no_code_{idx}"
        if code not in products:
            products[code] = {
                "codigo": code,
                "nombre": row.get(name_col, "") if name_col else "",
                "descripcion": row.get(desc_col, "") if desc_col else "",
                "imagen": row.get(image_col, "") if image_col else "",
                "variantes": []
            }

        # Construir variante: incluir todas las columnas excepto codigo/nombre/desc/imagen
        variant = {}
        for col in df.columns:
            if col in [code_col, name_col, desc_col, image_col]:
                continue
            val = row.get(col, "")
            if str(val).strip() == "":
                continue
            # Guardar la clave con el nombre original de la columna para legibilidad
            orig_key = norm_to_orig.get(col, col)
            variant[orig_key] = val

        if not variant:
            variant = {"fila": str(idx)}
        products[code]["variantes"].append(variant)

    # Guardar JSON
    records = list(products.values())
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"✅ Generado {OUTPUT_JSON} con {len(records)} productos agrupados.")

if __name__ == "__main__":
    main()
