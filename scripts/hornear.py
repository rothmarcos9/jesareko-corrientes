import json, sys, os, glob, time, re

pagina, salida, carpeta_db = sys.argv[1], sys.argv[2], sys.argv[3]

def cargar(nombre):
    try:
        return json.load(open(nombre + ".json"))
    except Exception:
        return None

def docs(col):
    out = []
    for f in glob.glob(os.path.join(carpeta_db, "**", col, "*.json"), recursive=True):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        d = d.get("data", d) if isinstance(d, dict) else None
        if isinstance(d, dict):
            d["id"] = os.path.splitext(os.path.basename(f))[0]
            out.append(d)
    return out

lim = time.time() * 1000 - 24 * 3600 * 1000
reportes = [{"id": r["id"], "loc": r.get("loc"), "tipo": r.get("tipo"), "texto": (r.get("texto") or "")[:200], "ts": r["ts"]}
            for r in docs("reportes") if isinstance(r.get("ts"), (int, float)) and r["ts"] >= lim]
comunicados = sorted([{k: c.get(k) for k in ("id", "titulo", "resumen", "fuente", "url", "fecha", "alertas")} for c in docs("comunicados")],
                     key=lambda c: c.get("fecha") or "", reverse=True)[:10]

sat = cargar("satelite")
if not (isinstance(sat, dict) and str(sat.get("img", "")).startswith("data:image/jpeg;base64,")):
    sat = None
tg = os.environ.get("TG_LINK", "").strip()
base = {"generado": int(time.time() * 1000), "pronostico": cargar("pronostico"), "rios": cargar("rios"),
        "incendios": cargar("incendios"), "comunicados": comunicados, "reportes": reportes,
        "satelite": sat, "ina": cargar("ina"), "smn": cargar("smn"), "telegram": tg if re.fullmatch(r"https://t\.me/[A-Za-z0-9_]+", tg) else None}
js = json.dumps(base, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

html = open(pagina, encoding="utf-8").read()
patron = re.compile(r'(<script type="application/json" id="datos-base">)(.*?)(</script>)', re.S)
if len(patron.findall(html)) != 1:
    sys.exit("No encontré el bloque datos-base en la página")
html = patron.sub(lambda m: m.group(1) + js + m.group(3), html)
open(salida, "w", encoding="utf-8").write(html)
print("OK pagina", salida, len(html), "bytes;", len(reportes), "avisos;", len(comunicados), "comunicados")
