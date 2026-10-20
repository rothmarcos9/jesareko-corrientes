import io, json, re, sys, time, zipfile, urllib.request, html
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

# Datos oficiales del Servicio Meteorológico Nacional (licencia CC BY 4.0):
# alertas (CAP), pronóstico a 5 días por estación y estado del tiempo actual.
UA = {"User-Agent": "Mozilla/5.0 (Jesareko Corrientes)"}
TZ = timezone(timedelta(hours=-3))
NS = {"c": "urn:oasis:names:tc:emergency:cap:1.2"}
LOCS = {"corrientes":(-27.469,-58.830),"goya":(-29.143,-59.265),"paso-de-los-libres":(-29.713,-57.087),"curuzu-cuatia":(-29.792,-58.054),"mercedes":(-29.184,-58.075),"santo-tome":(-28.549,-56.041),"esquina":(-30.015,-59.528),"bella-vista":(-28.509,-59.044),"ituzaingo":(-27.590,-56.688),"monte-caseros":(-30.253,-57.636),"saladas":(-28.254,-58.625),"gdor-virasoro":(-28.050,-56.020),"empedrado":(-27.951,-58.806),"concepcion":(-28.392,-57.887),"mburucuya":(-28.045,-58.228),"san-luis-del-palmar":(-27.508,-58.555),"sauce":(-30.085,-58.787),"santa-lucia":(-28.987,-59.103),"san-roque":(-28.574,-58.708),"ita-ibate":(-27.427,-57.338),"san-miguel":(-27.995,-57.590),"colonia-c-pellegrini":(-28.537,-57.172),"alvear":(-29.097,-56.552),"riachuelo":(-27.583,-58.746),"perugorria":(-29.341,-58.611),"chavarria":(-28.955,-58.573),"paso-de-la-patria":(-27.316,-58.573),"caa-cati":(-27.751,-57.620),"yapeyu":(-29.469,-56.817),"itati":(-27.270,-58.240)}
# Estaciones del SMN en la provincia: nombre en pron5d, nombre en estado del tiempo, coordenadas
EST = [("CORRIENTES_AERO","Corrientes","Corrientes Aero",-27.450,-58.759),("ITUZAINGO","Ituzaingó","Ituzaingó",-27.585,-56.677),
       ("MERCEDES_AERO_(CTES)","Mercedes","Mercedes Aero",-29.226,-58.086),("MONTE_CASEROS_AERO","Monte Caseros","Monte Caseros Aero",-30.262,-57.639),
       ("PASO_DE_LOS_LIBRES_AERO","Paso De Los Libres","Paso de los Libres Aero",-29.689,-57.149)]
NIVEL = {"Minor": 1, "Moderate": 1, "Severe": 2, "Extreme": 3}
MESES = {m: i + 1 for i, m in enumerate(["ENE","FEB","MAR","ABR","MAY","JUN","JUL","AGO","SEP","OCT","NOV","DIC"])}

def get(url, timeout=60):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception:
            if i == 2: raise
            time.sleep(5)

def dentro(lat, lon, poli):
    ok, j = False, len(poli) - 1
    for i in range(len(poli)):
        (ya, xa), (yb, xb) = poli[i], poli[j]
        if (ya > lat) != (yb > lat) and lon < (xb - xa) * (lat - ya) / (yb - ya) + xa:
            ok = not ok
        j = i
    return ok

def alertas():
    idx = get("https://ssl.smn.gob.ar/CAP/AR.php").decode("utf-8", "replace")
    urls = sorted(set(re.findall(r"https://ssl\.smn\.gob\.ar/feeds/CAP/xml_generados/[A-Za-z0-9_.\-]+\.xml", idx)))
    ahora = datetime.now(TZ)
    out = {}
    for u in urls:
        try:
            root = ET.fromstring(get(u, 30))
        except Exception as e:
            print("Aviso CAP", u[-60:], e); continue
        for info in root.findall("c:info", NS):
            sev = NIVEL.get(info.findtext("c:severity", "", NS))
            exp = info.findtext("c:expires", "", NS)
            try:
                if not sev or datetime.fromisoformat(exp) < ahora: continue
            except ValueError:
                continue
            ev = html.unescape(info.findtext("c:event", "", NS)).strip()
            desc = html.unescape(info.findtext("c:description", "", NS)).strip()
            ons = info.findtext("c:onset", "", NS)
            for area in info.findall("c:area", NS):
                for pg in area.findall("c:polygon", NS):
                    poli = [tuple(map(float, p.split(","))) for p in (pg.text or "").split()]
                    if len(poli) < 3: continue
                    lats = [p[0] for p in poli]; lons = [p[1] for p in poli]
                    if max(lats) < -31 or min(lats) > -27 or max(lons) < -60 or min(lons) > -55.5: continue
                    for lid, (la, lo) in LOCS.items():
                        if dentro(la, lo, poli):
                            a = {"evento": ev, "n": sev, "desde": ons, "hasta": exp, "desc": desc[:300]}
                            if a not in out.setdefault(lid, []): out[lid].append(a)
    for lid in out: out[lid].sort(key=lambda a: (-a["n"], a["desde"]))
    print("CAP:", len(urls), "archivos;", len(out), "localidades con alerta")
    return out

def leer_zip(dato):
    z = zipfile.ZipFile(io.BytesIO(get(f"https://ssl.smn.gob.ar/dpd/zipopendata.php?dato={dato}")))
    return z.read(z.namelist()[0]).decode("latin-1")

def pronostico():
    txt = leer_zip("pron5d")
    bloques = re.split(r"\n\s*([A-Z0-9_().\-]+)\s*\n\s*=+", txt)
    datos = {bloques[i].strip(): bloques[i + 1] for i in range(1, len(bloques) - 1, 2)}
    out = {}
    for clave, _, nombre, la, lo in EST:
        b = datos.get(clave)
        if not b: continue
        dias = {}
        for m in re.finditer(r"(\d{2})/([A-Z]{3})/(\d{4})\s+(\d{2})Hs\.\s+(-?[\d.]+)\s+(\d+)\s*\|\s*(\d+)\s+([\d.]+)", b):
            d = f"{m.group(3)}-{MESES[m.group(2)]:02d}-{m.group(1)}"
            x = dias.setdefault(d, {"tmax": -99, "tmin": 99, "lluvia": 0.0, "viento": 0})
            t = float(m.group(5)); x["tmax"] = max(x["tmax"], t); x["tmin"] = min(x["tmin"], t)
            x["lluvia"] += float(m.group(8)); x["viento"] = max(x["viento"], int(m.group(7)))
        out[nombre] = {"lat": la, "lon": lo, "dias": [{"fecha": d, "tmax": round(v["tmax"]), "tmin": round(v["tmin"]), "lluvia": round(v["lluvia"], 1), "viento": v["viento"]} for d, v in sorted(dias.items())][:5]}
    print("pron5d:", list(out))
    return out

def actual():
    out = {}
    for linea in leer_zip("tiepre").splitlines():
        c = [x.strip() for x in linea.split(";")]
        if len(c) < 9: continue
        for _, tn, nombre, la, lo in EST:
            if c[0].lower() == tn.lower():
                try: t = float(c[5])
                except ValueError: t = None
                out[nombre] = {"hora": c[2], "fecha": c[1], "cielo": c[3], "temp": t, "hum": c[7].strip(), "viento": re.sub(r"\s+", " ", c[8])}
    print("tiepre:", list(out))
    return out

def main(salida="smn.json"):
    res = {"actualizado": int(time.time() * 1000), "fuente": "Servicio Meteorológico Nacional", "licencia": "CC BY 4.0"}
    errores = 0
    for k, f in (("alertas", alertas), ("pronostico", pronostico), ("actual", actual)):
        try:
            res[k] = f()
        except Exception as e:
            print("ERROR smn", k, repr(e)); errores += 1
    if errores == 3:
        sys.exit("ERROR smn: sin datos")
    json.dump(res, open(salida, "w"), ensure_ascii=False)
    print("OK smn")

if __name__ == "__main__":
    main(*sys.argv[1:])
