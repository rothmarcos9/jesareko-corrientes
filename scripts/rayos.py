"""Rayos detectados por el satélite GOES-19 (sensor GLM de la NOAA) en la última hora sobre Corrientes.

Lee los archivos GLM-L2-LCFA (uno cada 20 segundos) del repositorio público de la NOAA en AWS,
se queda con los destellos dentro de la provincia y alrededores, y resume por localidad:
cuántos hubo a menos de 20 y de 50 km, y a qué distancia quedó el más cercano.
Uso: python3 scripts/rayos.py rayos.json
"""
import json, math, os, re, sys, tempfile, time, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

BUCKET = "https://noaa-goes19.s3.amazonaws.com"
MIN = 60  # minutos hacia atrás
CAJA = (-31.5, -26.0, -61.0, -54.8)  # lat mín, lat máx, lon mín, lon máx
LOCS = {"corrientes":(-27.469,-58.830),"goya":(-29.143,-59.265),"paso-de-los-libres":(-29.713,-57.087),"curuzu-cuatia":(-29.792,-58.054),"mercedes":(-29.184,-58.075),"santo-tome":(-28.549,-56.041),"esquina":(-30.015,-59.528),"bella-vista":(-28.509,-59.044),"ituzaingo":(-27.590,-56.688),"monte-caseros":(-30.253,-57.636),"saladas":(-28.254,-58.625),"gdor-virasoro":(-28.050,-56.020),"empedrado":(-27.951,-58.806),"concepcion":(-28.392,-57.887),"mburucuya":(-28.045,-58.228),"san-luis-del-palmar":(-27.508,-58.555),"sauce":(-30.085,-58.787),"santa-lucia":(-28.987,-59.103),"san-roque":(-28.574,-58.708),"ita-ibate":(-27.427,-57.338),"san-miguel":(-27.995,-57.590),"colonia-c-pellegrini":(-28.537,-57.172),"alvear":(-29.097,-56.552),"riachuelo":(-27.583,-58.746),"perugorria":(-29.341,-58.611),"chavarria":(-28.955,-58.573),"paso-de-la-patria":(-27.316,-58.573),"caa-cati":(-27.751,-57.620),"yapeyu":(-29.469,-56.817),"itati":(-27.270,-58.240)}


def get(url, timeout=40):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Jesareko/1.0"}), timeout=timeout) as r:
                return r.read()
        except Exception:
            if i == 2:
                raise
            time.sleep(2)


def listar(desde, hasta):
    claves = []
    h = desde.replace(minute=0, second=0, microsecond=0)
    while h <= hasta:
        pref = f"GLM-L2-LCFA/{h:%Y}/{h:%j}/{h:%H}/"
        root = ET.fromstring(get(f"{BUCKET}/?list-type=2&prefix={pref}&max-keys=1000"))
        ns = {"s": root.tag.split("}")[0].strip("{")}
        for c in root.findall("s:Contents", ns):
            k = c.findtext("s:Key", "", ns)
            m = re.search(r"_s(\d{4})(\d{3})(\d{2})(\d{2})(\d{2})", k)
            if not m:
                continue
            t = datetime.strptime("".join(m.groups()), "%Y%j%H%M%S").replace(tzinfo=timezone.utc)
            if desde <= t <= hasta:
                claves.append((t, k))
        h += timedelta(hours=1)
    return sorted(claves)


def destellos(clave):
    import netCDF4
    raw = get(f"{BUCKET}/{clave}")
    with tempfile.NamedTemporaryFile(suffix=".nc") as f:
        f.write(raw); f.flush()
        with netCDF4.Dataset(f.name) as ds:
            la = ds.variables["flash_lat"][:]; lo = ds.variables["flash_lon"][:]
            return [(float(a), float(b)) for a, b in zip(la, lo)
                    if CAJA[0] <= a <= CAJA[1] and CAJA[2] <= b <= CAJA[3]]


def km(a, b):
    r = math.pi / 180
    x = (b[1] - a[1]) * r * math.cos((a[0] + b[0]) / 2 * r); y = (b[0] - a[0]) * r
    return 6371 * math.hypot(x, y)


def main(salida="rayos.json"):
    hasta = datetime.now(timezone.utc); desde = hasta - timedelta(minutes=MIN)
    claves = listar(desde, hasta)
    if not claves:
        sys.exit("ERROR rayos: no hay archivos GLM recientes")
    pts, fallas = [], 0
    with ThreadPoolExecutor(8) as ex:
        for r in ex.map(lambda c: _seguro(c[1]), claves):
            if r is None:
                fallas += 1
            else:
                pts.extend(r)
    locs = {}
    for lid, c in LOCS.items():
        d = [km(c, p) for p in pts]
        n20 = sum(1 for x in d if x <= 20); n50 = sum(1 for x in d if x <= 50)
        if n50:
            locs[lid] = {"n20": n20, "n50": n50, "dmin": round(min(d))}
    celdas = {}
    for a, b in pts:
        k = (round(a * 20) / 20, round(b * 20) / 20)
        celdas[k] = celdas.get(k, 0) + 1
    puntos = sorted(([a, b, n] for (a, b), n in celdas.items()), key=lambda x: -x[2])[:600]
    res = {"actualizado": int(time.time() * 1000), "desde": int(desde.timestamp() * 1000), "hasta": int(claves[-1][0].timestamp() * 1000),
           "fuente": "NOAA GOES-19 GLM", "archivos": len(claves), "fallas": fallas, "total": len(pts), "locs": locs, "puntos": puntos}
    json.dump(res, open(salida, "w"), ensure_ascii=False)
    print(f"::notice title=Rayos::{len(claves)} archivos ({fallas} con error), {len(pts)} destellos en la región, {len(locs)} localidades con rayos a menos de 50 km")


def _seguro(clave):
    try:
        return destellos(clave)
    except Exception as e:
        print("Aviso GLM", clave[-40:], repr(e)[:120])
        return None


if __name__ == "__main__":
    main(*sys.argv[1:])
