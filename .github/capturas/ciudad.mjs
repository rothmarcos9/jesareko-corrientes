import { chromium } from 'playwright';
const b=await chromium.launch();
const p=await b.newPage({viewport:{width:412,height:880},deviceScaleFactor:2});
await p.goto('https://rothmarcos9.github.io/jesareko-corrientes/?v='+Date.now(),{waitUntil:'networkidle'});
await p.selectOption('#mi-loc','corrientes');
await p.addStyleTag({content:'header.top{position:static!important}'});
await p.waitForSelector('#ciudad:not([hidden]) .leaflet-tile-loaded',{timeout:60000});
await p.locator('#ciudad').scrollIntoViewIfNeeded();await p.waitForTimeout(4000);
await p.locator('#ciudad').screenshot({path:'out/ciudad.png'});
// zoom al sector Laguna Seca / La Olla y abrir ficha
await p.evaluate(()=>{CIU.mapa.setView([-27.497,-58.80],14);});await p.waitForTimeout(4000);
const pt=await p.evaluate(()=>{let best=null;CIU.mapa.eachLayer(l=>{if(l.getTooltip&&l.getTooltip()&&/La Olla|Laguna Seca|Ongay/.test(l.getTooltip().getContent()))best=best||l;});if(best){best.openPopup(best.getBounds?best.getBounds().getCenter():best.getLatLng());}return !!best;});
await p.waitForTimeout(2500);
await p.locator('#ciudad-mapa').screenshot({path:'out/ciudad-zoom.png'});
await p.click('#ciudad details:nth-of-type(1) summary').catch(()=>{});await p.waitForTimeout(300);
await p.locator('#ciudad-extra').screenshot({path:'out/ciudad-calles.png'});
// mapa de la provincia con satélite (imagen real)
await p.locator('#satelite').scrollIntoViewIfNeeded();await p.waitForTimeout(500);
console.log('popup',pt);await b.close();
