import json, re, subprocess, sys, time, urllib.request
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

def main(salida="ina.json"):
    hoy = datetime.now(ZoneInfo("America/Argentina/Cordoba")).date()
    for atras in range(0, 4):
        f = hoy - timedelta(days=atras)
        url = f"https://alerta.ina.gob.ar/ina/06-INFORMES/diario/pdf/reporte_diario_{f.isoformat()}.pdf"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Jesareko/1.0"}), timeout=60) as r:
                data = r.read()
        except Exception as e:
            print("No disponible", f, e); continue
        if not data.startswith(b"%PDF"):
            continue
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
        if estaciones:
            json.dump({"fecha": f"{f.day}/{f.month}", "fuente": "INA", "url": url, "estaciones": estaciones,
                       "actualizado": int(time.time() * 1000)}, open(salida, "w"), ensure_ascii=False)
            print("OK ina", f, [(e["est"], e["nivel"]) for e in estaciones]); return
        print("Sin estaciones en", f)
    print("ERROR ina: no se encontró reporte con datos"); sys.exit(1)

if __name__ == "__main__":
    main(*sys.argv[1:])
