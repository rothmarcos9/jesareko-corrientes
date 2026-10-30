import urllib.request, re, json
H={"User-Agent":"Mozilla/5.0 Jesareko"}
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=60).read()
out=[]
j=json.loads(get("https://geocatalogos.conae.gov.ar/geonetwork/srv/spa/q?any=krigeado&_content_type=json&fast=index&sortBy=changeDate&to=4"))
for m in j.get("metadata",[]):
    out.append(json.dumps({k:m.get(k) for k in ("title","defaultTitle","geoBox","link","image","uuid","geonet:info")},ensure_ascii=False)[:2500])
for ws in ["humedad","humedad_suelo","humedadsuelo","mhs","saocom","conae"]:
    try:
        x=get(f"https://geoportal.conae.gov.ar/geoserver/{ws}/ows?service=WMS&version=1.3.0&request=GetCapabilities").decode("utf-8","replace")
        names=re.findall(r"<Layer[^>]*>\s*<Name>([^<]+)</Name>",x)
        out.append(f"WS {ws}: {len(names)} {names[:40]}")
    except Exception as e: out.append(f"WS {ws} ERR {e}")
try:
    x=get("https://geoportal.conae.gov.ar/geoserver/rest/workspaces.json").decode()[:500]; out.append("REST "+x)
except Exception as e: out.append("REST ERR "+str(e))
open("sonda_out.txt","w").write("\n".join(out))
