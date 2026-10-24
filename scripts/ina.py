import json, os, re, subprocess, sys, time, urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Lee el reporte diario del INA y extrae altura, cota de alerta y de evacuación de los puertos de Corrientes.
EST = r"(Corrientes|Goya|Santo Tom[eé]|Paso de los Libres|Bella Vista|Esquina|Ituzaing[oó]|Itat[ií]|Monte Caseros|Empedrado)"
FILA = re.compile(EST + r"\s+(Paran[aá]|Uruguay)\s+(-?\d+[,.]\d+)\s*[^\d\s]?\s+(\d+[,.]\d+)\s+(\d+[,.]\d+)\s*(.*)$", re.I)
num = lambda t: float(t.replace(",", "."))

def texto_pdf(ruta):
    try:
        return subprocess.run(["pdftotext", "-layout", ruta, "-"], capture_output=True, text=True, check=True).stdout
    except Exception:
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(ruta).pages)

def bajar_reporte(f):
    """Estaciones del reporte diario del INA de la fecha f, o None si no hay reporte."""
    url = f"https://alerta.ina.gob.ar/ina/06-INFORMES/diario/pdf/reporte_diario_{f.isoformat()}.pdf"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Jesareko/1.0"}), timeout=60) as r:
            data = r.read()
    except Exception as e:
        print("No disponible", f, e); return None, url
    if not data.startswith(b"%PDF"):
        return None, url
    open("ina.pdf", "wb").write(data)
    estaciones, vistos = [], set()
    for linea in texto_pdf("ina.pdf").splitlines():
        m = FILA.search(linea.strip())
        if not m:
            continue
        est = m.group(1)
        if est.lower() in vistos:
            continue
        vistos.add(est.lower())
        persp = re.sub(r"\s{2,}.*$", "", m.group(6).strip())[:60]
        estaciones.append({"est": est, "rio": m.group(2).capitalize().replace("Parana", "Paraná"),
                           "nivel": num(m.group(3)), "alerta": num(m.group(4)), "evac": num(m.group(5)), "persp": persp})
    return (estaciones or None), url

DIAS_HIST = 15

def historial(hoy, ultimo):
    """Alturas de los últimos días por puerto. Reusa lo ya publicado y baja solo los reportes que faltan."""
    hist, sin = {}, set()
    sitio = os.environ.get("SITIO_URL", "").rstrip("/")
    if sitio:
        try:
            with urllib.request.urlopen(urllib.request.Request(sitio + "/datos.json", headers={"User-Agent": "Jesareko/1.0"}), timeout=60) as r:
                prev = (json.load(r).get("ina") or {})
            for est, serie in (prev.get("hist") or {}).items():
                hist[est] = {d: v for d, v in serie}
            sin = set(prev.get("hist_sin") or [])
        except Exception as e:
            print("Sin historial previo:", e)
    desde = hoy - timedelta(days=DIAS_HIST)
    for f, estaciones in ultimo:
        for e in estaciones:
            hist.setdefault(e["est"], {})[f.isoformat()] = e["nivel"]
    tiene = {d for serie in hist.values() for d in serie}
    bajados = 0
    for k in range(DIAS_HIST, 0, -1):
        f = hoy - timedelta(days=k); iso = f.isoformat()
        if iso in tiene or (iso in sin and k > 2) or bajados >= 6:
            continue
        estaciones, _ = bajar_reporte(f); bajados += 1
        if estaciones:
            for e in estaciones:
                hist.setdefault(e["est"], {})[iso] = e["nivel"]
            sin.discard(iso)
        else:
            sin.add(iso)
        time.sleep(1)
    lim = desde.isoformat()
    out = {est: sorted([[d, v] for d, v in serie.items() if d >= lim]) for est, serie in hist.items()}
    return out, sorted(d for d in sin if d >= lim)

def main(salida="ina.json"):
    hoy = datetime.now(ZoneInfo("America/Argentina/Cordoba")).date()
    for atras in range(0, 4):
        f = hoy - timedelta(days=atras)
        estaciones, url = bajar_reporte(f)
        if not estaciones:
            print("Sin estaciones en", f); continue
        res = {"fecha": f"{f.day}/{f.month}", "fuente": "INA", "url": url, "estaciones": estaciones,
               "actualizado": int(time.time() * 1000)}
        try:
            res["hist"], res["hist_sin"] = historial(hoy, [(f, estaciones)])
        except Exception as e:
            print("Aviso: sin historial", e)
        json.dump(res, open(salida, "w"), ensure_ascii=False)
        print("OK ina", f, [(e["est"], e["nivel"]) for e in estaciones], "historial:", {k: len(v) for k, v in (res.get("hist") or {}).items()}); return
    print("ERROR ina: no se encontró reporte con datos"); sys.exit(1)

if __name__ == "__main__":
    main(*sys.argv[1:])
