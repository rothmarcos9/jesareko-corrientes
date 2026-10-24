# Jesareko Corrientes · Alerta temprana (versión beta)

## 👉 Abrir la app: [rothmarcos9.github.io/jesareko-corrientes](https://rothmarcos9.github.io/jesareko-corrientes/)

App gratuita de **alerta temprana para la provincia de Corrientes**: alertas del SMN, **altura del río Paraná y del río Uruguay** (INA y Prefectura), crecida, evacuados, compuertas de Yacyretá e Itaipú, zonas inundables, focos de incendio e imagen satelital para 30 localidades (Corrientes capital, Goya, Itatí, Paso de la Patria, Bella Vista, Esquina, Empedrado, Ituzaingó, Paso de los Libres, Santo Tomé, Monte Caseros, Mercedes y más). Funciona desde el celular, sin registrarse ni instalar nada.

**Jesareko** significa "estar atento" o "vigilar" en guaraní.

Aplicación web gratuita de alerta temprana para la provincia de Corrientes
(Argentina). Reúne en un solo lugar:

- Pronóstico de lluvia, temperatura y viento para 29 localidades, con un nivel
  de alerta por localidad (verde, amarilla, naranja, roja) en un mapa.
- Caudal del río Paraná y del río Uruguay, incluidos Itaipú y Yacyretá, con
  umbrales de "alto" y "crecida".
- Focos de calor detectados por satélite (posibles incendios).
- Imagen satelital GOES-19 de la región y accesos al satélite y radar del SMN.
- Comunicados de las represas y organismos.
- Red de vecinos: avisos de lluvia fuerte, anegamientos o crecidas que se
  comparten con las localidades cercanas.
- Avisos automáticos por un canal de Telegram (en preparación).

## Autor

**Marcos E.A. Roth** · Licenciado en Geografía (UNNE) · Corrientes, Argentina.
Idea, concepto, nombre, criterios de alerta, selección de localidades y fuentes,
y dirección del desarrollo. El código fue escrito con asistencia de
inteligencia artificial (Claude, de Anthropic) bajo su dirección.

## Contenido del repositorio

| Archivo | Qué es |
|---|---|
| `index.html` | La aplicación completa (una sola página web). |
| `scripts/actualizar.py` | Descarga cada hora pronóstico, caudales, focos de calor e imagen satelital. |
| `scripts/hornear.py` | Inserta esos datos dentro de la página para que funcione sin cuenta. |
| `scripts/alertas.py` | Calcula los niveles y publica los avisos en Telegram. |

## Fuentes de datos

Open-Meteo (pronóstico y caudales GloFAS / Copernicus), NASA FIRMS (focos de
calor VIIRS), NOAA / NESDIS (imagen GOES-19), SMN, EBY e INA (comunicados y
umbrales). Los datos pertenecen a sus respectivas fuentes.

## Aviso

Versión beta, en prueba. No reemplaza los avisos oficiales del SMN, el INA,
Prefectura Naval ni Defensa Civil. Emergencias: 911 · Defensa Civil: 103 ·
Bomberos: 100.

© 2026 Marcos E.A. Roth. Todos los derechos reservados. Ver `LICENSE`.


## Página pública

La app se publica sola en GitHub Pages: https://rothmarcos9.github.io/jesareko-corrientes/

- `app/index.html`: la aplicación (un solo archivo).
- `scripts/`: descarga de datos (Open-Meteo, GloFAS, NASA FIRMS, NOAA GOES-19, INA, SMN) y armado de la página.
- `datos/comunicados.json`: comunicados sobre la crecida (se actualiza dos veces por día).
- `.github/workflows/publicar.yml`: cada hora baja los datos y vuelve a publicar la página.
