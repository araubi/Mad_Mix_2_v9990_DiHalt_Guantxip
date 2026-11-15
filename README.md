# Mad Mix 2 V9990: DiHalt + Guantxip (v1.0)

Versión de la conversión V9990 de **Mad Mix 2** (Topo Soft, 1990) hecha por **DiHalt Studio** ([DiHaltStudio/madmix2-v9990](https://github.com/DiHaltStudio/madmix2-v9990), v1.0), **coloreada por Guantxip**: lleva su set gráfico completo (losetas, figuras, marcador) y se puede elegir en el menú entre el set de Guantxip y el original de DiHalt. Hecha con permiso expreso de DiHalt Studio.

![Mad Mix 2 V9990](V9990/docs/img/play.png)

## Cómo se juega

ROM compilada en [`release/MadMix2_V9990_DiHalt_Guantxip_v1.0.zip`](release/) (ROM de 2 MB, mapper ASCII16, la detectan solos openMSX y blueMSX). Necesita un MSX con Z80 y cartucho V9990 (GFX9000).

- Cursores o joystick para mover; ESPACIO o disparo para elegir y jugar; H pausa (se sigue con disparo).
- En el menú, arriba/abajo eligen la línea y izquierda/derecha cambian su valor:
  - STANDARD / HARD.
  - Set gráfico: GUANTXIP (el de entrada) o DIHALT.
  - ARRIBA IZQDA (como el original) o ARRIBA DCHA (arriba lleva a Pac arriba a la derecha; todas las direcciones giran 90°).
  - Z80 / R800: solo en un MSX turbo R (en los demás se queda en Z80).
- Con el set de Guantxip: sus mapas corregidos (cada loseta nueva conserva la colisión de la que sustituye, así que se juega igual; lista en `V9990/assets-guantxip/maps/cambios.txt`), Pac rojo mientras dura la bola grande y las vidas con los dos ojos. El set DIHALT es el de la v1.0 de DiHalt sin cambios.

Manuales de DiHalt: [Español](V9990/docs/manual/manual-es.pdf) · [English](V9990/docs/manual/manual-en.pdf).

## Compilar

El juego original no se distribuye aquí. La compilación necesita un directorio privado con la cinta original y lo que se extrae de ella: ver [docs/BUILDING.md](docs/BUILDING.md) (`make build ORIGINAL_DIR=...`). El arte de Guantxip está en `V9990/assets-guantxip/` (sus hojas tal cual en `original/`; `V9990/tools/import_guantxip.py` las convierte y `V9990/tools/compara_fases.py` saca sus mapas corregidos).

## Créditos

- Juego original: **Topo Soft**, 1990.
- Conversión V9990, motor, música, set gráfico DIHALT y manuales: **DiHalt Studio**, 2026.
- Set gráfico GUANTXIP (coloreado): **Guantxip**.
- Esta versión (opción de set, importación del arte de Guantxip, menú, R800, pruebas): **araubi**, desarrollado con Claude (Anthropic).

## Licencia y avisos

- Las herramientas y el código añadidos en esta versión (`V9990/tools/import_guantxip.py`, `V9990/tools/compara_fases.py`, `V9990/tools/gfx_sets.py`, `V9990/src/port_cpu_switch.inc` y los cambios de esta versión al código) van con licencia **MIT** ([LICENSE](LICENSE)).
- La documentación propia de esta versión (este README y lo añadido a `docs/BUILDING.md`) va con licencia **CC BY-NC-SA 4.0** ([LICENSE-CC](LICENSE-CC)).
- El resto del código, el arte, la música y los manuales de la conversión son de **DiHalt Studio**, que no publicó licencia: se incluyen con su permiso para esta versión y siguen siendo suyos.
- Los gráficos del set GUANTXIP son de **Guantxip** y siguen siendo suyos.
- Mad Mix 2 y su código original son de sus titulares. La ROM de `release/` contiene el juego original convertido y no queda cubierta por ninguna de estas licencias.
- Es un homenaje sin ánimo de lucro, para estudio y conservación. Si algún titular de derechos lo pide, se retira.

---

# Mad Mix 2 V9990: DiHalt + Guantxip (v1.0), in English

A version of **DiHalt Studio**'s V9990 conversion of Topo Soft's 1990 game, **coloured by Guantxip**: his full graphics set, selectable in the menu against DiHalt's original one. Made with DiHalt Studio's explicit permission. The ROM is in `release/` (2 MB, ASCII16, MSX with Z80 and V9990). New tools and code: MIT; this version's own docs: CC BY-NC-SA 4.0; DiHalt Studio's code, art, music and manuals remain theirs (no licence published, used with permission); Guantxip's art remains his; original game rights remain with their owners. Developed by araubi with Claude (Anthropic).
