"""Mide qué tan preciso es el pronóstico de Jesareko en Corrientes.

Compara el pronóstico que la app tenía un día antes (Open-Meteo, "previous runs") con lo que
midieron las estaciones del SMN:
  - Temperatura máxima y mínima: registro diario del SMN (datos abiertos).
  - Si llovió o no: partes METAR de los aeropuertos (lluvia o llovizna informada en el día).

Los días con lluvia observada se van acumulando en verificacion.json publicado en el sitio.
Uso: python3 scripts/verificar.py verificacion.json
"""
import io, json, os, re, sys, time, urllib.request, zipfile
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=-3))
UA = {"User-Agent": "Jesareko/1.0 (alerta temprana Corrientes)"}
DIAS = 30
# nombre en la app, nombre en el registro del SMN, código OACI (None si no hay METAR), lat, lon
EST = [("Corrientes", "CORRIENTES AERO", "SARC", -27.450, -58.759),
       ("Ituzaingó", "ITUZAINGO", None, -27.585, -56.677),
       ("Mercedes", "MERCEDES AERO (CTES)", "SATM", -29.226, -58.086),
       ("Monte Caseros", "MONTE CASEROS AERO", "SARM", -30.262, -57.639),
       ("Paso de los Libres", "PASO DE LOS LIBRES AERO", "SARL", -29.689, -57.149)]
UMBRAL_LLUVIA = 1.0  # mm en el día para decir "llueve" según el pronóstico


def get(url, timeout=60):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception:
            if i == 2:
                raise
            time.sleep(5 * (i + 1))


def previo():
    sitio = os.environ.get("SITIO_URL", "").rstrip("/")
    if not sitio:
        return {}
    try:
        return json.loads(get(sitio + "/verificacion.json"))
    except Exception as e:
        print("Sin verificación previa:", e)
        return {}


def pronosticos():
    """Pronóstico emitido el día anterior para cada hora (Open-Meteo previous runs), resumido por día."""
    lat = ",".join(str(e[3]) for e in EST); lon = ",".join(str(e[4]) for e in EST)
    url = ("https://previous-runs-api.open-meteo.com/v1/forecast?latitude=" + lat + "&longitude=" + lon +
           "&hourly=temperature_2m_previous_day1,precipitation_previous_day1"
           f"&past_days={DIAS + 1}&forecast_days=1&timezone=America%2FArgentina%2FCordoba")
    data = json.loads(get(url, 90))
    data = data if isinstance(data, list) else [data]
    out = {}
    for (nombre, *_), d in zip(EST, data):
        h = d["hourly"]; por_dia = {}
        for t, temp, pp in zip(h["time"], h["temperature_2m_previous_day1"], h["precipitation_previous_day1"]):
            x = por_dia.setdefault(t[:10], {"t": [], "pp": []})
            if temp is not None: x["t"].append(temp)
            if pp is not None: x["pp"].append(pp)
        out[nombre] = {f: {"tmax": round(max(x["t"]), 1), "tmin": round(min(x["t"]), 1), "lluvia": round(sum(x["pp"]), 1)}
                       for f, x in por_dia.items() if len(x["t"]) >= 20 and len(x["pp"]) >= 20}
    return out


def temperaturas_smn():
    """Máxima y mínima diaria medidas por el SMN (registro de los últimos 365 días)."""
    z = zipfile.ZipFile(io.BytesIO(get("https://ssl.smn.gob.ar/dpd/zipopendata.php?dato=regtemp")))
    txt = z.read(z.namelist()[0]).decode("latin-1")
    nombres = {e[1]: e[0] for e in EST}
    out = {}
    for linea in txt.splitlines():
        m = re.match(r"\s*(\d{2})(\d{2})(\d{4})\s+(-?[\d.]+|\s*)\s+(-?[\d.]+|\s*)\s+(.+?)\s*$", linea)
        if not m or m.group(6) not in nombres:
            continue
        f = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        try:
            out.setdefault(nombres[m.group(6)], {})[f] = {"tmax": float(m.group(4)), "tmin": float(m.group(5))}
        except ValueError:
            pass
    return out


def lluvia_metar():
    """Para cada aeropuerto y día (hora local), si algún parte METAR informó lluvia o llovizna."""
    ids = ",".join(e[2] for e in EST if e[2])
    txt = get(f"https://aviationweather.gov/api/data/metar?ids={ids}&hours=168&format=raw", 60).decode("utf-8", "replace")
    oaci = {e[2]: e[0] for e in EST if e[2]}
    ahora = datetime.now(timezone.utc)
    out, partes = {}, {}
    for linea in txt.splitlines():
        m = re.match(r"(?:METAR |SPECI )?(SA\w\w) (\d{2})(\d{2})(\d{2})Z (.*)$", linea.strip())
        if not m or m.group(1) not in oaci:
            continue
        dia, hh, mm = int(m.group(2)), int(m.group(3)), int(m.group(4))
        cand = ahora.replace(day=1, hour=hh, minute=mm, second=0, microsecond=0)
        # el día del mes puede ser del mes anterior
        for k in range(0, 40):
            t = (ahora - timedelta(days=k)).replace(hour=hh, minute=mm, second=0, microsecond=0)
            if t.day == dia and t <= ahora + timedelta(hours=1):
                cand = t; break
        f = cand.astimezone(TZ).strftime("%Y-%m-%d")
        cuerpo = re.split(r"\b(RMK|TEMPO|BECMG|NOSIG)\b", m.group(5))[0]
        llueve = bool(re.search(r"(?<![A-Z])[-+]?(VC)?(SH|TS|FZ)?(RA|DZ)\b|(?<![A-Z])[-+]?TSRA|SHRA", cuerpo))
        est = oaci[m.group(1)]
        partes.setdefault(est, {}).setdefault(f, 0)
        partes[est][f] += 1
        if llueve:
            out.setdefault(est, {})[f] = True
        else:
            out.setdefault(est, {}).setdefault(f, False)
    # solo días con suficientes partes (cobertura razonable del día)
    return {e: {f: v for f, v in d.items() if partes[e].get(f, 0) >= 8} for e, d in out.items()}


def main(salida="verificacion.json"):
    prev = previo()
    hoy = datetime.now(TZ).strftime("%Y-%m-%d")
    lim = (datetime.now(TZ) - timedelta(days=90)).strftime("%Y-%m-%d")
    res = {"actualizado": int(time.time() * 1000), "metodo": {
        "pronostico": "Open-Meteo, pronóstico emitido el día anterior (previous runs, día 1)",
        "temperatura_observada": "SMN, registro diario de máxima y mínima (datos abiertos)",
        "lluvia_observada": "partes METAR de los aeropuertos: lluvia o llovizna informada en el día",
        "umbral_lluvia_pronostico_mm": UMBRAL_LLUVIA}}
    errores = []
    try:
        pron = pronosticos()
    except Exception as e:
        errores.append("pronóstico: " + repr(e)[:150]); pron = {}
    try:
        temp = temperaturas_smn()
    except Exception as e:
        errores.append("SMN: " + repr(e)[:150]); temp = {}
    lluvia = {k: dict(v) for k, v in (prev.get("lluvia_obs") or {}).items()}
    try:
        for est, dias in lluvia_metar().items():
            for f, v in dias.items():
                if f < hoy:
                    lluvia.setdefault(est, {})[f] = v
    except Exception as e:
        errores.append("METAR: " + repr(e)[:150])
    lluvia = {e: {f: v for f, v in d.items() if f >= lim} for e, d in lluvia.items()}
    # Pronósticos ya guardados de corridas anteriores (por si la API deja de devolver días viejos)
    guard = {k: dict(v) for k, v in (prev.get("pron") or {}).items()}
    for est, dias in pron.items():
        for f, v in dias.items():
            if f < hoy:
                guard.setdefault(est, {})[f] = v
    guard = {e: {f: v for f, v in d.items() if f >= lim} for e, d in guard.items()}

    filas = []
    for nombre, *_ in EST:
        for f, p in sorted(guard.get(nombre, {}).items()):
            o = temp.get(nombre, {}).get(f) or (prev.get("temp_obs") or {}).get(nombre, {}).get(f)
            r = lluvia.get(nombre, {}).get(f)
            filas.append({"est": nombre, "fecha": f, "p": p, "o": o, "llovio": r})
    temp_obs = {e: {f: v for f, v in d.items() if f >= lim and f in guard.get(e, {})} for e, d in temp.items()}

    def mae(xs): return round(sum(abs(x) for x in xs) / len(xs), 1) if xs else None
    def sesgo(xs): return round(sum(xs) / len(xs), 1) if xs else None
    def resumen(fs):
        emax = [x["p"]["tmax"] - x["o"]["tmax"] for x in fs if x["o"]]
        emin = [x["p"]["tmin"] - x["o"]["tmin"] for x in fs if x["o"]]
        ll = [(x["p"]["lluvia"] >= UMBRAL_LLUVIA, x["llovio"]) for x in fs if x["llovio"] is not None]
        ac = sum(1 for a, b in ll if a == b)
        return {"dias_temp": len(emax), "error_tmax": mae(emax), "sesgo_tmax": sesgo(emax),
                "error_tmin": mae(emin), "sesgo_tmin": sesgo(emin),
                "tmax_dentro_2c": round(100 * sum(1 for x in emax if abs(x) <= 2) / len(emax)) if emax else None,
                "dias_lluvia": len(ll), "acierto_lluvia": round(100 * ac / len(ll)) if ll else None,
                "llovio_y_se_pronostico": sum(1 for a, b in ll if a and b),
                "llovio_sin_pronostico": sum(1 for a, b in ll if not a and b),
                "falsa_alarma": sum(1 for a, b in ll if a and not b),
                "seco_bien": sum(1 for a, b in ll if not a and not b)}
    recientes = [x for x in filas if x["fecha"] >= (datetime.now(TZ) - timedelta(days=DIAS)).strftime("%Y-%m-%d")]
    res["resumen"] = resumen(recientes)
    res["por_estacion"] = {n: resumen([x for x in recientes if x["est"] == n]) for n, *_ in EST}
    res["periodo"] = [min((x["fecha"] for x in recientes), default=None), max((x["fecha"] for x in recientes), default=None)]
    res["pron"], res["temp_obs"], res["lluvia_obs"], res["errores"] = guard, temp_obs, lluvia, errores
    json.dump(res, open(salida, "w"), ensure_ascii=False)
    r = res["resumen"]
    print("::notice title=Precisión del pronóstico::" + json.dumps({"periodo": res["periodo"], **r, "errores": errores}, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:])
