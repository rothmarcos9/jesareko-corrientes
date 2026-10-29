/**
 * Jesareko Corrientes · Recepción de avisos de vecinos con ubicación y foto.
 *
 * Se publica como "Aplicación web" de Google Apps Script (Ejecutar como: yo · Quién tiene acceso: Cualquier persona).
 * Cada aviso se guarda como una fila en la pestaña "Avisos app" de la planilla de respuestas de Jesareko,
 * y la foto (si hay) en la carpeta "Jesareko - fotos de avisos" de Google Drive.
 * Las fotos NO se muestran en la app hasta que en la columna "Estado foto" escribas: aprobada
 * (o elegís "aprobada" en la lista). Para que no se vea, escribí: rechazada.
 */
const PLANILLA = '1dZJ7hVYIwwz14R41-Iqo_TcgDr2TvRuqQ-ixhIxd8JY';
const HOJA = 'Avisos app';
const CARPETA = 'Jesareko - fotos de avisos';
const TIPOS = ['llueve', 'fuerte', 'anegado', 'rio', 'granizo', 'viento', 'calor', 'luz'];
const MAX_FOTO = 1600000;      // bytes (la app manda la foto ya achicada, unos 200-400 kB)
const MAX_POR_10_MIN = 40;     // freno simple contra abusos

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    if (TIPOS.indexOf(d.tipo) < 0) throw new Error('tipo inválido');
    if (!/^[a-z0-9-]{3,40}$/.test(d.loc || '')) throw new Error('localidad inválida');
    const texto = String(d.texto || '').replace(/[\u0000-\u001f]/g, ' ').slice(0, 200);
    let lat = '', lon = '', prec = '';
    if (d.lat != null && d.lon != null) {
      const la = Number(d.lat), lo = Number(d.lon);
      if (la > -31.8 && la < -26.0 && lo > -61.0 && lo < -55.0) { lat = la.toFixed(5); lon = lo.toFixed(5); prec = Math.round(Number(d.precision) || 0); }
    }
    const cache = CacheService.getScriptCache();
    const n = Number(cache.get('n') || 0);
    if (n >= MAX_POR_10_MIN) throw new Error('demasiados avisos, probá en unos minutos');
    cache.put('n', String(n + 1), 600);

    let foto = '';
    if (typeof d.foto === 'string' && d.foto.indexOf('data:image/jpeg;base64,') === 0) {
      const bytes = Utilities.base64Decode(d.foto.split(',')[1]);
      if (bytes.length > MAX_FOTO) throw new Error('foto demasiado grande');
      const f = carpeta_().createFile(Utilities.newBlob(bytes, 'image/jpeg', 'aviso-' + d.loc + '-' + Date.now() + '.jpg'));
      f.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
      foto = f.getId();
    }
    const lock = LockService.getScriptLock(); lock.waitLock(20000);
    try { hoja_().appendRow([new Date(), d.loc, d.tipo, texto, lat, lon, prec, foto, foto ? 'pendiente' : '']); }
    finally { lock.releaseLock(); }
    return salida_({ ok: true, foto: !!foto });
  } catch (err) {
    return salida_({ ok: false, error: String(err && err.message || err) });
  }
}

function doGet() { return salida_({ ok: true, servicio: 'Jesareko avisos' }); }

function salida_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }

function hoja_() {
  const ss = SpreadsheetApp.openById(PLANILLA);
  let h = ss.getSheetByName(HOJA);
  if (!h) {
    h = ss.insertSheet(HOJA);
    h.appendRow(['Fecha', 'Localidad', 'Tipo', 'Texto', 'Latitud', 'Longitud', 'Precisión (m)', 'Foto', 'Estado foto']);
    h.setFrozenRows(1);
    const regla = SpreadsheetApp.newDataValidation().requireValueInList(['pendiente', 'aprobada', 'rechazada'], true).build();
    h.getRange('I2:I').setDataValidation(regla);
  }
  return h;
}

function carpeta_() {
  const it = DriveApp.getFoldersByName(CARPETA);
  return it.hasNext() ? it.next() : DriveApp.createFolder(CARPETA);
}

/** Ejecutar una vez desde el editor para crear la pestaña y la carpeta, y dar los permisos. */
function preparar() { hoja_(); carpeta_(); Logger.log('Listo: pestaña "' + HOJA + '" y carpeta "' + CARPETA + '".'); }
