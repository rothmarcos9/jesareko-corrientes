import urllib.request, re, json, xml.etree.ElementTree as ET
H={"User-Agent":"Mozilla/5.0 Jesareko"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=60).read()
out=[]
try:
    x=get("https://geoportal.conae.gov.ar/geoserver/ows?service=WMS&version=1.3.0&request=GetCapabilities")
    ns={"w":"http://www.opengis.net/wms"}
    r=ET.fromstring(x)
    for L in r.iter("{http://www.opengis.net/wms}Layer"):
        n=L.find("w:Name",ns); t=L.find("w:Title",ns)
        if n is None: continue
        bb=L.find("w:EX_GeographicBoundingBox",ns)
        b=[bb.find("w:"+k,ns).text for k in ("westBoundLongitude","eastBoundLongitude","southBoundLatitude","northBoundLatitude")] if bb is not None else ""
        dims=[(d.get("name"),(d.text or "")[-120:]) for d in L.findall("w:Dimension",ns)]
        out.append(f"{n.text} | {t.text if t is not None else ''} | {b} | {dims}")
except Exception as e: out.append("CAP ERR "+repr(e))
try:
    j=json.loads(get("https://geocatalogos.conae.gov.ar/geonetwork/srv/spa/q?any=humedad&_content_type=json&fast=index&sortBy=changeDate&to=40"))
    for m in j.get("metadata",[]):
        out.append("META "+str(m.get("title") or m.get("defaultTitle"))+" | "+str(m.get("changeDate"))+" | "+str(m.get("link"))[:300])
except Exception as e: out.append("GN ERR "+repr(e))
try:
    h=get("https://catalogos2.conae.gov.ar/humedad_suelos/").decode("utf-8","replace")
    out.append("HS dates: "+", ".join(sorted(set(re.findall(r"20\d{6}",h)))[-15:]))
    out.append("HS links: "+" ".join(sorted(set(re.findall(r'href="([^"]+)"',h)))[:60]))
except Exception as e: out.append("HS ERR "+repr(e))
try:
    h=get("https://geodescargas.conae.gov.ar/descargas/productos/CONAE_MOD_MHS_DSS_PSM_20261028_v001.zip").decode("utf-8","replace")
    out.append("GD: "+re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",h))[:800])
except Exception as e: out.append("GD ERR "+repr(e))
open("sonda_out.txt","w").write("\n".join(out))
