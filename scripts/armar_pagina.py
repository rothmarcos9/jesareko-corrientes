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

INDEXNOW = "2054cbf0ad5253f9355b55c86798a31d"  # clave pública de IndexNow (Bing, Yandex y otros buscadores)
URL_SITIO = "https://rothmarcos9.github.io/jesareko-corrientes/"
TITULO = "Jesareko Corrientes · Alerta temprana de lluvias, crecidas e incendios"
DESCRIPCION = ("App gratuita de alerta temprana para la provincia de Corrientes: pronóstico y alertas del SMN, "
               "altura del río Paraná y Uruguay (INA y Prefectura), evacuados, compuertas de Yacyretá e Itaipú, "
               "zonas inundables, focos de incendio e imagen satelital. Sin registrarse.")

def para_buscadores(h):
    """Agrega idioma, título, descripción, vista previa para compartir y datos estructurados."""
    import html as H
    ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": "Jesareko Corrientes",
          "alternateName": ["Jesareko", "Alerta temprana Corrientes"], "url": URL_SITIO,
          "description": DESCRIPCION, "applicationCategory": "WeatherApplication", "operatingSystem": "Web",
          "inLanguage": "es-AR", "isAccessibleForFree": True,
          "offers": {"@type": "Offer", "price": "0", "priceCurrency": "ARS"},
          "author": {"@type": "Person", "name": "Marcos Roth"},
          "areaServed": {"@type": "AdministrativeArea", "name": "Provincia de Corrientes, Argentina"},
          "keywords": "alerta temprana, Corrientes, crecida río Paraná, altura del río, inundaciones, El Niño, SMN, INA, Yacyretá, evacuados, Itatí, Goya, Paso de la Patria"}
    d, t = H.escape(DESCRIPCION, quote=True), H.escape(TITULO, quote=True)
    meta = (f'<title>{t}</title><meta name="description" content="{d}">'
            f'<meta name="keywords" content="{H.escape(ld["keywords"], quote=True)}">'
            f'<meta name="author" content="Marcos Roth"><meta name="robots" content="index,follow">'
            f'<link rel="canonical" href="{URL_SITIO}">'
            f'<meta property="og:type" content="website"><meta property="og:locale" content="es_AR">'
            f'<meta property="og:site_name" content="Jesareko Corrientes"><meta property="og:title" content="{t}">'
            f'<meta property="og:description" content="{d}"><meta property="og:url" content="{URL_SITIO}">'
            f'<meta property="og:image" content="{URL_SITIO}compartir.png"><meta property="og:image:width" content="1200">'
            f'<meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">'
            f'<meta name="theme-color" content="#13221E">')
    gv = (cargar("datos/google.json") or {}).get("verificacion", "")
    if re.fullmatch(r"[A-Za-z0-9_\-]{20,80}", gv or ""):
        meta += f'<meta name="google-site-verification" content="{gv}">'
    meta += '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + '</script>'
    h = h.replace("<html>", '<html lang="es-AR">', 1)
    h = re.sub(r"<title>[^<]*</title>", "", h, count=1)  # el título ahora va en <head>
    if "<meta charset=utf8>" in h:
        return h.replace("<meta charset=utf8>", "<meta charset=utf8>" + meta, 1)
    return h.replace("<head>", '<head><meta charset="utf-8">' + meta, 1)

def extras_buscadores():
    hoy = time.strftime("%Y-%m-%d", time.gmtime())
    with open(os.path.join(SALIDA, "robots.txt"), "w") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {URL_SITIO}sitemap.xml\n")
    with open(os.path.join(SALIDA, "sitemap.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f'<url><loc>{URL_SITIO}</loc><lastmod>{hoy}</lastmod><changefreq>hourly</changefreq><priority>1.0</priority></url></urlset>\n')
    with open(os.path.join(SALIDA, INDEXNOW + ".txt"), "w") as f:
        f.write(INDEXNOW)
    import shutil
    if os.path.exists("app/compartir.png"):
        shutil.copy("app/compartir.png", os.path.join(SALIDA, "compartir.png"))

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
    pagina = html[:m.start(2)] + js + html[m.end(2):]
    pagina = para_buscadores(pagina)
    with open(os.path.join(SALIDA, "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina)
    extras_buscadores()
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
