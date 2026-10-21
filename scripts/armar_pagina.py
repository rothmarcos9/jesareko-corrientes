"""Arma la página pública de Jesareko con los datos del momento.

Lee los JSON que dejaron actualizar.py, ina.py y smn.py; si alguno falló, usa el
último dato publicado (datos.json del sitio) para que la página nunca quede vacía.
Suma los comunicados de datos/comunicados.json y, si hay formulario de Google
configurado, los avisos de vecinos de las últimas 24 horas.

Uso: python3 scripts/armar_pagina.py <carpeta_salida>
"""
import csv, io, json, os, re, sys, time, unicodedata, urllib.request
from datetime import datetime, timedelta, timezone

SALIDA = sys.argv[1] if len(sys.argv) > 1 else "_site"
SITIO = os.environ.get("SITIO_URL", "").rstrip("/")
PATRON = re.compile(r'(<script type="application/json" id="datos-base">)(.*?)(</script>)', re.S)
TZ = timezone(timedelta(hours=-3))
TIPOS = {"Empezó a llover": "llueve", "Llueve fuerte": "fuerte", "Calle o barrio anegado": "anegado",
         "Río o arroyo creciendo": "rio", "Granizo": "granizo", "Viento fuerte": "viento",
         "Calor extremo": "calor", "Corte de luz": "luz"}

def cargar(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def bajar(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Jesareko/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def slug(t):
    t = unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")

def avisos_formulario(cfg):
    """Avisos enviados por el formulario de Google (planilla publicada como CSV)."""
    if not cfg or not cfg.get("csv"):
        return []
    filas = list(csv.reader(io.StringIO(bajar(cfg["csv"]).decode("utf-8", "replace"))))
    lim = time.time() - 24 * 3600
    out = []
    for i, f in enumerate(filas[1:], start=2):
        if len(f) < 3:
            continue
        try:
            fecha = datetime.strptime(f[0].strip(), "%d/%m/%Y %H:%M:%S").replace(tzinfo=TZ)
        except ValueError:
            continue
        tipo = TIPOS.get(f[2].strip())
        if not tipo or fecha.timestamp() < lim:
            continue
        out.append({"id": f"form-{i}", "loc": slug(f[1]), "tipo": tipo,
                    "texto": (f[3].strip() if len(f) > 3 else "")[:200], "ts": int(fecha.timestamp() * 1000), "origen": "formulario"})
    return out

def main():
    html = open("app/index.html", encoding="utf-8").read()
    m = PATRON.search(html)
    if not m:
        sys.exit("No encontré el bloque datos-base en app/index.html")
    plantilla = json.loads(m.group(2) or "{}")
    previo = {}
    if SITIO:
        try:
            previo = json.loads(bajar(SITIO + "/datos.json"))
        except Exception as e:
            print("Sin datos previos:", e)

    base = {"generado": int(time.time() * 1000)}
    for k in ("pronostico", "rios", "incendios", "satelite", "ina", "smn"):
        nuevo = cargar(k + ".json")
        if k == "satelite" and not (isinstance(nuevo, dict) and str(nuevo.get("img", "")).startswith("data:image/jpeg;base64,")):
            nuevo = None
        base[k] = nuevo or previo.get(k) or plantilla.get(k)
        print(k, "nuevo" if nuevo else ("previo" if previo.get(k) else "plantilla"))

    comu = cargar("datos/comunicados.json") or previo.get("comunicados") or plantilla.get("comunicados") or []
    # Fuente extra: la versión de la app en claude.ai, que recibe los comunicados dos veces por día.
    remoto = "sin probar"
    url_comu = os.environ.get("COMU_URL", "")
    if url_comu:
        try:
            txt = bajar(url_comu, timeout=40).decode("utf-8", "replace")
            if os.environ.get("COMU_DIAG"):
                urls = sorted(set(re.findall(r'https?://[^"' + "'" + r'\s<>]+', txt)))[:25]
                print("::notice title=Diag claude::" + str(len(txt)) + " bytes | " + txt[:300].replace("\n", " ") + " | " + " ".join(urls))
            mm = PATRON.search(txt)
            lista = json.loads(mm.group(2)).get("comunicados") if mm else json.loads(txt)
            lista = [c for c in (lista or []) if isinstance(c, dict) and c.get("id")]
            ids = {c.get("id") for c in comu}
            nuevos = [c for c in lista if c["id"] not in ids]
            comu = comu + nuevos
            remoto = f"ok: {len(lista)} leídos, {len(nuevos)} nuevos"
        except Exception as e:
            remoto = "error: " + repr(e)[:200]
    print("::notice title=Comunicados remotos::" + remoto)
    claves = ("id", "titulo", "resumen", "fuente", "url", "fecha", "alertas")
    base["comunicados"] = sorted([{k: c.get(k) for k in claves} for c in comu if isinstance(c, dict)],
                                 key=lambda c: c.get("fecha") or "", reverse=True)[:10]

    form = cargar("datos/formulario.json")
    base["form"] = {k: form[k] for k in ("url", "loc", "tipo", "texto") if k in form} if form else None
    try:
        base["reportes"] = avisos_formulario(form)
    except Exception as e:
        print("Aviso: no se pudieron leer los avisos del formulario:", e)
        base["reportes"] = previo.get("reportes") or []
    # la imagen satelital va al final del JSON (es lo más pesado)
    base["fuentes"] = {k: ("nuevo" if cargar(k + ".json") else "anterior") for k in ("pronostico", "rios", "incendios", "satelite", "ina", "smn")}
    tg = (cargar("datos/telegram.json") or {}).get("link", "")
    base["telegram"] = tg if re.fullmatch(r"https://t\.me/[A-Za-z0-9_]+", tg or "") else None

    base["satelite"] = base.pop("satelite")
    js = json.dumps(base, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, "index.html"), "w", encoding="utf-8") as f:
        f.write(html[:m.start(2)] + js + html[m.end(2):])
    with open(os.path.join(SALIDA, "datos.json"), "w", encoding="utf-8") as f:
        f.write(js.replace("<\\/", "</"))
    smn = base.get("smn") or {}
    estado = {"generado": base["generado"], "fuentes": base["fuentes"],
              "pronostico_localidades": len((base.get("pronostico") or {}).get("locs") or {}),
              "ina_fecha": (base.get("ina") or {}).get("fecha"),
              "ina_estaciones": {e.get("est"): e.get("nivel") for e in (base.get("ina") or {}).get("estaciones") or []},
              "smn_localidades_con_alerta": len(smn.get("alertas") or {}),
              "smn_estaciones": sorted((smn.get("pronostico") or {}).keys()),
              "comunicados": len(base["comunicados"]), "avisos": len(base["reportes"]),
              "formulario": bool(base.get("form")), "comunicados_remotos": remoto}
    with open(os.path.join(SALIDA, "estado.json"), "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=1)
    print(json.dumps(estado, ensure_ascii=False))
    open(os.path.join(SALIDA, ".nojekyll"), "w").close()
    print("OK página:", len(base["comunicados"]), "comunicados,", len(base["reportes"]), "avisos")

if __name__ == "__main__":
    main()
