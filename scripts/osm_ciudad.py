"""Baja de OpenStreetMap los barrios y cuerpos de agua de la ciudad de Corrientes (uso puntual).
© colaboradores de OpenStreetMap, licencia ODbL.""" 
import json, sys, time, urllib.parse, urllib.request

B = "-27.60,-58.92,-27.36,-58.66"
SERV = ["https://overpass.private.coffee/api/interpreter", "https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
Q = {
 "barrios": f'[out:json][timeout:300];(relation["boundary"="administrative"]["admin_level"~"9|10"]({B});relation["place"~"neighbourhood|suburb|quarter"]({B});way["place"~"neighbourhood|suburb|quarter"]({B}););out geom;',
 "agua": f'[out:json][timeout:300];(way["natural"="water"]({B});relation["natural"="water"]({B});way["natural"="wetland"]({B});relation["natural"="wetland"]({B});way["water"]({B}););out geom;',
 "puntos": f'[out:json][timeout:60];node["place"~"neighbourhood|suburb|quarter|hamlet"]({B});out;',
}

def consultar(q):
    err = None
    for s in SERV:
        for i in range(1):
            try:
                data = urllib.parse.urlencode({"data": q}).encode()
                with urllib.request.urlopen(urllib.request.Request(s, data=data, headers={"User-Agent": "Jesareko/1.0 (alerta temprana Corrientes)"}), timeout=320) as r:
                    return json.load(r)
            except Exception as e:
                err = e; print("reintento", s, repr(e)[:150]); time.sleep(10)
    raise err

def anillos(segs):
    """Une tramos de líneas en anillos cerrados."""
    segs = [s[:] for s in segs if len(s) >= 2]; out = []
    while segs:
        r = segs.pop(0)
        cambio = True
        while r[0] != r[-1] and cambio:
            cambio = False
            for i, s in enumerate(segs):
                if s[0] == r[-1]: r += s[1:]
                elif s[-1] == r[-1]: r += s[::-1][1:]
                elif s[-1] == r[0]: r = s + r[1:]
                elif s[0] == r[0]: r = s[::-1] + r[1:]
                else: continue
                segs.pop(i); cambio = True; break
        if r[0] == r[-1] and len(r) >= 4: out.append(r)
    return out

def geom(e):
    pt = lambda g: [round(g["lon"], 5), round(g["lat"], 5)]
    if e["type"] == "way" and e.get("geometry"):
        c = [pt(g) for g in e["geometry"]]
        return {"type": "Polygon", "coordinates": [c]} if c[0] == c[-1] and len(c) >= 4 else None
    if e["type"] == "relation":
        outer = [[pt(g) for g in m["geometry"]] for m in e.get("members", []) if m.get("type") == "way" and m.get("role") in ("outer", "") and m.get("geometry")]
        rings = anillos(outer)
        if rings: return {"type": "MultiPolygon", "coordinates": [[r] for r in rings]}
    return None

def main():
    res = {}
    for k in ("barrios", "agua"):
        d = consultar(Q[k]); feats = []
        for e in d.get("elements", []):
            g = geom(e)
            if not g: continue
            t = e.get("tags", {})
            feats.append({"type": "Feature", "properties": {x: t[x] for x in ("name", "place", "admin_level", "boundary", "landuse", "natural", "water", "wetland") if x in t}, "geometry": g})
        res[k] = {"type": "FeatureCollection", "features": feats}
        json.dump(res[k], open(f"datos/ciudad/{k}.geojson", "w"), ensure_ascii=False, separators=(",", ":"))
    d = consultar(Q["puntos"])
    pts = [{"name": e["tags"]["name"], "place": e["tags"].get("place"), "lat": e["lat"], "lon": e["lon"]} for e in d.get("elements", []) if e.get("tags", {}).get("name")]
    json.dump(pts, open("datos/ciudad/barrios_puntos.json", "w"), ensure_ascii=False)
    nb = sorted({f["properties"].get("name", "") for f in res["barrios"]["features"]} - {""})
    print("::notice title=OSM::barrios=%d (con nombre %d) agua=%d puntos=%d" % (len(res["barrios"]["features"]), len(nb), len(res["agua"]["features"]), len(pts)))
    print("::notice title=OSM nombres::" + ", ".join(nb)[:3000])
    print("::notice title=OSM puntos::" + ", ".join(sorted(p["name"] for p in pts))[:3000])

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("::error title=OSM::" + repr(e)[:400]); sys.exit(1)
