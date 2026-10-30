import urllib.request, re, ssl, datetime, json
H={"User-Agent":"Mozilla/5.0 Jesareko"}
def get(u,n=4000):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=40)
        b=r.read(); return f"{r.status} {r.headers.get('Content-Type')} {len(b)}B\n"+b[:n].decode('utf-8','replace')
    except Exception as e: return "ERR "+repr(e)[:300]
out=[]
urls=["https://catalogos.conae.gov.ar/catalogo/catalogoGeoServiciosOGC.html",
"https://geoportal.conae.gov.ar/geoexplorer/composer/",
"https://geoservicios.conae.gov.ar/geoserver/ows?service=WMS&request=GetCapabilities",
"https://geoportal.conae.gov.ar/geoserver/ows?service=WMS&request=GetCapabilities",
"https://catalogos2.conae.gov.ar/humedad_suelos/",
"https://geocatalogos.conae.gov.ar/geonetwork/srv/spa/q?any=humedad&_content_type=json&fast=index&sortBy=changeDate&to=30"]
hoy=datetime.date.today()
for d in range(0,6):
    f=(hoy-datetime.timedelta(days=d)).strftime("%Y%m%d")
    urls.append(f"https://geodescargas.conae.gov.ar/descargas/productos/CONAE_MOD_MHS_DSS_PSM_{f}_v001.zip")
for u in urls:
    out.append("=== "+u+"\n"+get(u, 300 if u.endswith(".zip") else 6000))
open("sonda_out.txt","w").write("\n\n".join(out))
