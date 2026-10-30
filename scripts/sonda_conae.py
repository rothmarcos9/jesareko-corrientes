import urllib.request, json, time
d=json.loads(urllib.request.urlopen("https://rothmarcos9.github.io/jesareko-corrientes/datos.json?x=%d"%time.time(),timeout=60).read())
L=d["pronostico"]["locs"]; con=[k for k,v in L.items() if v.get("suelo")]
open("sonda_out.txt","w").write(f"{len(con)}/{len(L)} con suelo; ej: "+json.dumps({k:L[k].get("suelo") for k in ["corrientes","goya","san-luis-del-palmar"] if k in L}))
