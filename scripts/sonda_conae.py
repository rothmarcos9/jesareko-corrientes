import urllib.request
H={"User-Agent":"Mozilla/5.0 Jesareko"}
for p in ["psmkr","msmkr"]:
    for t in ["QL","TH"]:
        u=f"https://geocatalogos.conae.gov.ar/mod/mhs/dss/{p}/20261029/CONAE_MOD_MHS_DSS_{p.upper()}_20261029_v001_{t}.png"
        try: open(f"sonda_{p}_{t}.png","wb").write(urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=60).read())
        except Exception as e: open(f"sonda_{p}_{t}.err","w").write(str(e))
open("sonda_out.txt","w").write("ok")
