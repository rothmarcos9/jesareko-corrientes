"""Arma ciudad.json para el mapa de anegamientos de la ciudad de Corrientes.

Une datos/ciudad/zonas.json (zonas con nivel, motivo y fuentes) con los límites de barrios y los
cuerpos de agua de OpenStreetMap. Si un barrio no tiene límite dibujado en OSM, usa su punto
con un círculo aproximado; si tampoco hay punto, lo lista como "sin ubicar".
Uso: python3 scripts/ciudad.py <carpeta_salida>
"""
import json, os, re, sys, unicodedata

D = "datos/ciudad"
RADIO = 450  # metros, para barrios que solo tienen un punto


def norm(t):
    t = unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\b(barrio|b°|bo|villa|asentamiento|conglomerado)\b", " ", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def cargar(n, defecto):
    try:
        return json.load(open(os.path.join(D, n), encoding="utf-8"))
    except Exception:
        return defecto


def area(g):
    def a(r):
        return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r, r[1:])) / 2)
    if g["type"] == "Polygon":
        return a(g["coordinates"][0])
    return sum(a(p[0]) for p in g["coordinates"])


def main(salida):
    Z = cargar("zonas.json", None)
    if not Z:
        print("Sin zonas.json"); return
    barrios = cargar("barrios.geojson", {"features": []})["features"]
    puntos = cargar("barrios_puntos.json", [])
    agua = cargar("agua.geojson", {"type": "FeatureCollection", "features": []})
    por_nombre = {}
    for f in barrios:
        n = norm(f["properties"].get("name"))
        if not n or area(f["geometry"]) > 0.004:  # descarta polígonos enormes (más de unos 40 km²)
            continue
        if n not in por_nombre or area(f["geometry"]) < area(por_nombre[n]["geometry"]):
            por_nombre[n] = f
    pts = {norm(p["name"]): p for p in puntos}
    zonas, sin = [], []
    for z in Z["zonas"]:
        nombres = [z["n"]] + z.get("alias", [])
        g = None
        for nm in nombres:
            k = norm(nm)
            if k in por_nombre:
                g = por_nombre[k]["geometry"]; break
        if not g:
            for nm in nombres:
                k = norm(nm)
                if k in pts:
                    g = {"type": "Circle", "c": [pts[k]["lat"], pts[k]["lon"]], "r": RADIO}; break
        if not g and z.get("punto"):
            g = {"type": "Circle", "c": z["punto"], "r": z.get("radio", RADIO)}
        zz = {k: z[k] for k in ("n", "nivel", "motivo", "f")}
        if g:
            zz["geom"] = g
        else:
            sin.append(z["n"])
        zonas.append(zz)
    # agua: solo polígonos chicos/medianos dentro del ejido (las lagunas urbanas y bañados)
    ag = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": f["geometry"]} for f in agua["features"]
        if f["properties"].get("water") != "river" and area(f["geometry"]) < 0.002]}
    out = {"titulo": Z["titulo"], "nota": Z["nota"], "criterio": Z["criterio"], "fuentes": Z["fuentes"],
           "zonas": zonas, "calles": Z.get("calles", []), "agua": ag, "sin_ubicar": sin}
    os.makedirs(salida, exist_ok=True)
    with open(os.path.join(salida, "ciudad.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    ubic = len(zonas) - len(sin)
    print(f"::notice title=Mapa de la ciudad::{ubic} de {len(zonas)} zonas ubicadas; {len(ag['features'])} cuerpos de agua; sin ubicar: {', '.join(sin)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "_site")
