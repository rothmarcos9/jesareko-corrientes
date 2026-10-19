# Jesareko Corrientes · Alerta temprana (versión beta)

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

**Marcos Roth** · Licenciado en Geografía (UNNE) · Corrientes, Argentina.
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

© 2026 Marcos Roth. Todos los derechos reservados. Ver `LICENSE`.
