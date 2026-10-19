import json, os, sys, time, math, urllib.request, urllib.parse

# Uso: TG_TOKEN=... TG_CHAT=@canal python3 alertas.py estado_anterior.json estado_nuevo.json
# Si estado_anterior.json no existe, arranca de cero. TG_DRY=1 imprime sin enviar.
APP = "https://claude.ai/artifact/8QiioDCRRDCaC3NeoxEYFm"
NOMBRES = {"corrientes":"Corrientes","goya":"Goya","paso-de-los-libres":"Paso de los Libres","curuzu-cuatia":"Curuzú Cuatiá","mercedes":"Mercedes","santo-tome":"Santo Tomé","esquina":"Esquina","bella-vista":"Bella Vista","ituzaingo":"Ituzaingó","monte-caseros":"Monte Caseros","saladas":"Saladas","gdor-virasoro":"Gdor. Virasoro","empedrado":"Empedrado","concepcion":"Concepción","mburucuya":"Mburucuyá","san-luis-del-palmar":"San Luis del Palmar","sauce":"Sauce","santa-lucia":"Santa Lucía","san-roque":"San Roque","ita-ibate":"Itá Ibaté","san-miguel":"San Miguel","colonia-c-pellegrini":"Colonia C. Pellegrini","alvear":"Alvear","riachuelo":"Riachuelo","perugorria":"Perugorría","chavarria":"Chavarría","paso-de-la-patria":"Paso de la Patria","caa-cati":"Caá Catí","yapeyu":"Yapeyú"}
COORD = {"corrientes":(-27.469,-58.830),"goya":(-29.143,-59.265),"paso-de-los-libres":(-29.713,-57.087),"curuzu-cuatia":(-29.792,-58.054),"mercedes":(-29.184,-58.075),"santo-tome":(-28.549,-56.041),"esquina":(-30.015,-59.528),"bella-vista":(-28.509,-59.044),"ituzaingo":(-27.590,-56.688),"monte-caseros":(-30.253,-57.636),"saladas":(-28.254,-58.625),"gdor-virasoro":(-28.050,-56.020),"empedrado":(-27.951,-58.806),"concepcion":(-28.392,-57.887),"mburucuya":(-28.045,-58.228),"san-luis-del-palmar":(-27.508,-58.555),"sauce":(-30.085,-58.787),"santa-lucia":(-28.987,-59.103),"san-roque":(-28.574,-58.708),"ita-ibate":(-27.427,-57.338),"san-miguel":(-27.995,-57.590),"colonia-c-pellegrini":(-28.537,-57.172),"alvear":(-29.097,-56.552),"riachuelo":(-27.583,-58.746),"perugorria":(-29.341,-58.611),"chavarria":(-28.955,-58.573),"paso-de-la-patria":(-27.316,-58.573),"caa-cati":(-27.751,-57.620),"yapeyu":(-29.469,-56.817)}
RIOLOC = {"corrientes":"corrientes","riachuelo":"corrientes","empedrado":"corrientes","paso-de-la-patria":"itati","ita-ibate":"itati","ituzaingo":"ituzaingo","bella-vista":"goya","goya":"goya","santa-lucia":"goya","esquina":"esquina","santo-tome":"santo-tome","alvear":"paso-de-los-libres","yapeyu":"paso-de-los-libres","paso-de-los-libres":"paso-de-los-libres","monte-caseros":"monte-caseros"}
NIV = ["sin alerta", "alerta amarilla", "alerta naranja", "alerta roja"]
ICO = ["🟢", "🟡", "🟠", "🔴"]
REENVIO_H = 12

def cargar(p, defecto=None):
    try:
        d = json.load(open(p))
        return d.get("data", d) if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict) else d
    except Exception:
        return defecto

def km(a, b):
    r = math.pi / 180
    h = math.sin((b[0]-a[0])*r/2)**2 + math.cos(a[0]*r)*math.cos(b[0]*r)*math.sin((b[1]-a[1])*r/2)**2
    return 2 * 6371 * math.asin(math.sqrt(h))

def estado_rio(p):
    v = p["serie"][p["hoy"]]
    if v is None:
        return None
    fut = [x for x in p["serie"][p["hoy"]:p["hoy"]+8] if x is not None]
    mx = max([v] + fut)
    n = 2 if mx >= p["p97"] else 1 if mx >= p["p90"] else 0
    return {"n": n, "v": v, "mx": mx}

def niveles(pron, rios, fuego):
    out = {}
    rio_por_id = {p["id"]: p for p in (rios or {}).get("puntos", [])}
    focos = (fuego or {}).get("focos", [])
    for lid, c in COORD.items():
        p = (pron or {}).get("locs", {}).get(lid)
        motivos = []
        if p:
            l, lh = p.get("lluvia24", 0), p.get("lluviaMaxHora", 0)
            n = 3 if l >= 100 or lh >= 50 else 2 if l >= 60 or lh >= 30 else 1 if l >= 30 or lh >= 15 else 0
            if n: motivos.append((n, f"lluvia: {l} mm en 24 h (picos de {lh} mm/h)"))
            tx, tn, rf = p.get("tmax"), p.get("tmin"), p.get("rafagas")
            if tx is not None:
                n = 3 if tx >= 42 else 2 if tx >= 40 else 1 if tx >= 38 else 0
                if n: motivos.append((n, f"calor: máxima de {tx} °C"))
            if tn is not None:
                n = 3 if tn <= -3 else 2 if tn <= 0 else 1 if tn <= 2 else 0
                if n: motivos.append((n, f"frío: mínima de {tn} °C"))
            if rf is not None:
                n = 3 if rf >= 100 else 2 if rf >= 80 else 1 if rf >= 60 else 0
                if n: motivos.append((n, f"viento: ráfagas de {rf} km/h"))
        rp = rio_por_id.get(RIOLOC.get(lid, ""))
        if rp:
            e = estado_rio(rp)
            if e and e["n"]:
                motivos.append((e["n"] + 1, f"río {rp['rio']} {'en crecida' if e['n'] == 2 else 'alto'} ({e['v']:,} m³/s hoy)".replace(",", ".")))
        cerca = [f for f in focos if km(c, (f["lat"], f["lon"])) <= 15]
        if len(cerca) >= 3 or any(km(c, (f["lat"], f["lon"])) <= 5 for f in cerca):
            motivos.append((1, f"{len(cerca)} focos de calor a menos de 15 km"))
        motivos.sort(key=lambda m: -m[0])
        out[lid] = {"n": motivos[0][0] if motivos else 0, "motivos": [m[1] for m in motivos if m[0] >= 1][:3]}
    return out

def enviar(texto):
    if os.environ.get("TG_DRY"):
        print("---- MENSAJE (prueba, no enviado) ----\n" + texto); return
    token, chat = os.environ["TG_TOKEN"], os.environ["TG_CHAT"]
    data = urllib.parse.urlencode({"chat_id": chat, "text": texto, "disable_web_page_preview": "true"}).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=60) as r:
        res = json.load(r)
    if not res.get("ok"):
        raise RuntimeError("Telegram respondió: " + str(res)[:200])
    print("Enviado a Telegram")

def main(previo_p, nuevo_p):
    previo = cargar(previo_p, {}) or {}
    ant = previo.get("niveles", {})
    enviados = previo.get("enviados", {})
    pron, rios, fuego = cargar("pronostico.json"), cargar("rios.json"), cargar("incendios.json")
    if not pron and not rios:
        print("Sin datos, no se evalúan alertas"); return
    ahora = time.time()
    act = niveles(pron, rios, fuego)
    suben, bajan = [], []
    for lid, x in act.items():
        n0 = ant.get(lid, 0)
        clave = f"{lid}:{x['n']}"
        if x["n"] >= 2 and x["n"] > n0 and ahora - enviados.get(clave, 0) > REENVIO_H * 3600:
            suben.append((lid, x)); enviados[clave] = ahora
        elif n0 >= 2 and x["n"] <= 1:
            bajan.append(lid)
    if suben or bajan:
        partes = ["⚠️ JESAREKO · Alerta temprana de Corrientes", ""]
        for lid, x in sorted(suben, key=lambda t: -t[1]["n"]):
            partes.append(f"{ICO[x['n']]} {NOMBRES[lid]}: {NIV[x['n']].upper()}")
            partes += [f"   • {m}" for m in x["motivos"]]
        if bajan:
            if suben: partes.append("")
            partes.append("🟢 Bajó el nivel de alerta en: " + ", ".join(NOMBRES[l] for l in bajan))
        partes += ["", "Ver mapa y consejos: " + APP, "Versión beta. Seguí siempre las indicaciones del SMN, el INA y Defensa Civil. Emergencias: 911 · Defensa Civil: 103"]
        enviar("\n".join(partes))
    else:
        print("Sin cambios que avisar")
    enviados = {k: v for k, v in enviados.items() if ahora - v < 7 * 86400}
    json.dump({"niveles": {k: v["n"] for k, v in act.items()}, "enviados": enviados, "ts": int(ahora * 1000)},
              open(nuevo_p, "w"), ensure_ascii=False)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
