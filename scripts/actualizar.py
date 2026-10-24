import json, sys, time, csv, io, urllib.request, urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

UA = {"User-Agent": "AlertaTempranaCorrientes/1.0"}
TZ = ZoneInfo("America/Argentina/Cordoba")

L = [("corrientes",-27.469,-58.830),("goya",-29.143,-59.265),("paso-de-los-libres",-29.713,-57.087),("curuzu-cuatia",-29.792,-58.054),("mercedes",-29.184,-58.075),("santo-tome",-28.549,-56.041),("esquina",-30.015,-59.528),("bella-vista",-28.509,-59.044),("ituzaingo",-27.590,-56.688),("monte-caseros",-30.253,-57.636),("saladas",-28.254,-58.625),("gdor-virasoro",-28.050,-56.020),("empedrado",-27.951,-58.806),("concepcion",-28.392,-57.887),("mburucuya",-28.045,-58.228),("san-luis-del-palmar",-27.508,-58.555),("sauce",-30.085,-58.787),("santa-lucia",-28.987,-59.103),("san-roque",-28.574,-58.708),("ita-ibate",-27.427,-57.338),("san-miguel",-27.995,-57.590),("colonia-c-pellegrini",-28.537,-57.172),("alvear",-29.097,-56.552),("riachuelo",-27.583,-58.746),("perugorria",-29.341,-58.611),("chavarria",-28.955,-58.573),("paso-de-la-patria",-27.316,-58.573),("caa-cati",-27.751,-57.620),("yapeyu",-29.469,-56.817),("itati",-27.270,-58.240)]

# id, nombre, rio, lat, lon, mediana, p90, p97 (caudal diario m3/s, 2005-2025, GloFAS)
R = [["itaipu","Paraná en Itaipú (Foz do Iguaçu)","Paraná",-25.4,-54.6,8932,12646,17578],["ituzaingo","Paraná en Yacyretá–Ituzaingó","Paraná",-27.36,-56.5,10939,25000,30000],["itati","Paraná en Itatí","Paraná",-27.27,-58.24,10888,16557,23334],["corrientes","Paraná en Corrientes","Paraná",-27.47,-58.85,17178,25762,36057],["goya","Paraná en Goya","Paraná",-28.99,-59.25,17864,26606,37067],["esquina","Paraná en Esquina","Paraná",-30.2,-59.67,18238,27415,37930],["santo-tome","Uruguay en Santo Tomé","Uruguay",-28.6,-56.07,2108,6621,10863],["paso-de-los-libres","Uruguay en Paso de los Libres","Uruguay",-29.52,-56.98,3054,8649,13739],["monte-caseros","Uruguay en Monte Caseros","Uruguay",-30.15,-57.67,3372,9353,14621]]

def get(url, timeout=90):
    for intento in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, OSError) as e:
            if intento == 5 or (isinstance(e, urllib.error.HTTPError) and e.code not in (429, 500, 502, 503, 504)):
                raise
            time.sleep(15 * (intento + 1))

def multi(base, puntos, extra):
    u = (base + "?latitude=" + ",".join(str(p[0]) for p in puntos) +
         "&longitude=" + ",".join(str(p[1]) for p in puntos) + extra)
    d = json.loads(get(u))
    return d if isinstance(d, list) else [d]

def pronostico():
    ahora = datetime.now(TZ).strftime("%Y-%m-%dT%H:00")
    locs = {}
    r1 = lambda v: round(v, 1)
    for i in range(0, len(L), 5):
        g = L[i:i + 5]
        data = multi("https://api.open-meteo.com/v1/forecast", [(x[1], x[2]) for x in g],
                     "&hourly=precipitation,precipitation_probability,temperature_2m,wind_gusts_10m,relative_humidity_2m,apparent_temperature"
                     "&past_days=3&forecast_days=3&timezone=America%2FArgentina%2FCordoba")
        for (lid, _, _), d in zip(g, data):
            h = d["hourly"]; t = h["time"]
            i0 = next((k for k, x in enumerate(t) if x >= ahora), 0); s = slice(i0, i0 + 24)
            col = lambda k, sl, z=0: [z if v is None else v for v in h[k][sl]]
            pr = col("precipitation", s); pp = col("precipitation_probability", s)
            tt = [v for v in h["temperature_2m"][s] if v is not None]; wg = col("wind_gusts_10m", s)
            hu = [v for v in h["relative_humidity_2m"][s] if v is not None]
            at = [v for v in h["apparent_temperature"][s] if v is not None]
            s48 = slice(i0, i0 + 48)
            locs[lid] = {"lluvia24": round(sum(pr)), "lluviaMaxHora": round(max(pr)), "prob": round(max(pp)),
                         "tmax": round(max(tt)), "tmin": round(min(tt)), "rafagas": round(max(wg)),
                         # humedad y sensación térmica
                         "hum": round(h["relative_humidity_2m"][i0] or 0), "humMed": round(sum(hu) / len(hu)) if hu else None,
                         "st": round(h["apparent_temperature"][i0]) if h["apparent_temperature"][i0] is not None else None,
                         "stmax": round(max(at)) if at else None, "stmin": round(min(at)) if at else None,
                         # lluvia caída (estimada por el modelo) en las últimas 24 y 72 horas
                         "caida24": r1(sum(col("precipitation", slice(max(0, i0 - 24), i0)))),
                         "caida72": r1(sum(col("precipitation", slice(max(0, i0 - 72), i0)))),
                         # lluvia hora por hora, próximas 48 horas
                         "h48": {"t0": t[i0], "mm": [r1(v) for v in col("precipitation", s48)],
                                 "pp": [round(v) for v in col("precipitation_probability", s48)]}}
        time.sleep(3)
    return {"actualizado": int(time.time() * 1000), "fuente": "Open-Meteo", "locs": locs}

def rios():
    hoy = datetime.now(TZ).strftime("%Y-%m-%d")
    data = multi("https://flood-api.open-meteo.com/v1/flood", [(x[3], x[4]) for x in R],
                 "&daily=river_discharge&past_days=10&forecast_days=10")
    puntos = []
    for r, d in zip(R, data):
        fechas = d["daily"]["time"]; q = d["daily"]["river_discharge"]
        serie = [round(v) if v is not None else None for v in q]
        ih = fechas.index(hoy) if hoy in fechas else 10
        puntos.append({"id": r[0], "nombre": r[1], "rio": r[2], "lat": r[3], "lon": r[4],
                       "p50": r[5], "p90": r[6], "p97": r[7], "fechas": fechas, "serie": serie, "hoy": ih})
    return {"actualizado": int(time.time() * 1000), "fuente": "GloFAS vía Open-Meteo", "puntos": puntos}

def incendios():
    focos = []
    for sat, url in (("VIIRS S-NPP", "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_America_24h.csv"),
                     ("VIIRS NOAA-20", "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_South_America_24h.csv")):
        try:
            txt = get(url, timeout=120).decode("utf-8", "replace")
        except Exception as e:
            print("Aviso: no se pudo leer", sat, e); continue
        for row in csv.DictReader(io.StringIO(txt)):
            try:
                la, lo = float(row["latitude"]), float(row["longitude"])
            except (KeyError, ValueError):
                continue
            if not (-30.9 <= la <= -27.1 and -59.9 <= lo <= -55.4):
                continue
            conf = (row.get("confidence") or "").lower()[:1]
            if conf == "l":
                continue
            focos.append({"lat": round(la, 4), "lon": round(lo, 4), "frp": round(float(row.get("frp") or 0), 1),
                          "fecha": row.get("acq_date"), "hora": (row.get("acq_time") or "").zfill(4), "sat": sat,
                          "conf": "alta" if conf == "h" else "nominal"})
    focos.sort(key=lambda f: (f["fecha"], f["hora"]), reverse=True)
    return {"actualizado": int(time.time() * 1000), "fuente": "NASA FIRMS (VIIRS)", "focos": focos[:400]}

def satelite():
    import base64
    from PIL import Image, ImageDraw
    raw = get("https://cdn.star.nesdis.noaa.gov/GOES19/ABI/SECTOR/ssa/GEOCOLOR/latest.jpg", timeout=120)
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    if im.size != (7200, 4320):
        raise ValueError("tamaño inesperado " + str(im.size))
    im = im.crop((2961, 1164, 4046, 2207))  # NE argentino, Paraguay, sur de Brasil y Uruguay
    im.thumbnail((900, 900))
    d = ImageDraw.Draw(im)
    x, y = 380, 295  # ciudad de Corrientes en el recorte
    d.ellipse((x - 6, y - 6, x + 6, y + 6), outline=(255, 214, 10), width=3)
    try:
        from PIL import ImageFont
        fnt = ImageFont.load_default(size=24)
    except Exception:
        fnt = None
    d.text((x + 11, y - 30), "Corrientes", fill=(255, 214, 10), font=fnt, stroke_width=2, stroke_fill=(0, 0, 0))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=72, optimize=True); raw = buf.getvalue()
    if len(raw) > 900_000:
        raise ValueError("imagen demasiado grande")
    return {"ts": int(time.time() * 1000), "img": "data:image/jpeg;base64," + base64.b64encode(raw).decode()}

if __name__ == "__main__":
    salidas = {"pronostico": pronostico, "rios": rios, "incendios": incendios, "satelite": satelite}
    errores = []
    for nombre, f in salidas.items():
        try:
            doc = f()
            json.dump(doc, open(nombre + ".json", "w"), ensure_ascii=False)
            extra = len(doc.get("locs") or doc.get("puntos") or doc.get("focos") or doc.get("img") or [])
            print("OK", nombre, extra)
        except Exception as e:
            print("ERROR", nombre, repr(e))
            if nombre != "satelite":
                errores.append(nombre)
    sys.exit(1 if errores else 0)
