import urllib.request, time, re
h=urllib.request.urlopen("https://rothmarcos9.github.io/jesareko-corrientes/?x=%d"%time.time(),timeout=60).read().decode()
open("sonda_out.txt","w").write(re.search(r"<title>(.*?)</title>",h).group(1)+" | "+("en pausa" if "está en pausa" in h else "NO"))
