import urllib.request, json
u=("https://api.open-meteo.com/v1/forecast?latitude=-27.47,-29.14,-28.55,-30.25&longitude=-58.83,-59.26,-56.04,-57.64"
   "&hourly=soil_moisture_3_to_9cm,soil_moisture_9_to_27cm,precipitation&past_days=3&forecast_days=3&timezone=America%2FArgentina%2FCordoba")
out=[]
try:
    d=json.loads(urllib.request.urlopen(u,timeout=60).read())
    for x in d:
        h=x["hourly"]; out.append(json.dumps({"lat":x["latitude"],"s9":h["soil_moisture_3_to_9cm"][::12],"s27":h["soil_moisture_9_to_27cm"][::12],"lluvia":sum(v or 0 for v in h["precipitation"][:84])}))
except Exception as e: out.append("ERR "+repr(e)+" "+(e.read().decode()[:300] if hasattr(e,'read') else ''))
open("sonda_out.txt","w").write("\n".join(out))
