# Building

Requires Python 3, Pillow (`pip install -r requirements.txt` in a virtual environment), SJASM and an original-game workspace. For the manuals, install Tectonic and DejaVu Sans fonts.

`make build ORIGINAL_DIR=/path/to/private/workspace` links private resources and builds a 2 MiB ASCII16 ROM (both graphics sets included) at `V9990/build/madmix2-v99990.rom`. The private workspace must contain:

- `MSX/original/`: the original Mad Mix 2 CAS.
- `MSX/build/`: the byte-faithful `game.bin`, `loader.bin`, `opening.bin`, `intro.bin`, `stage.bin` and cartridge bridge images reconstructed from that CAS.
- `V9990/assets/music/`, `sfx/`, `opening/`: original PSG captures and opening art needed by the renderer build.

These private files are linked locally and excluded from Git. `make run` uses a downloaded release ROM and needs none of them. `make manual` builds the two PDF manuals. `make release` copies the built ROM and manuals to `release/`.

## Graphics sets

The cartridge carries two complete graphics sets and the menu chooses one (left/right on the third menu line; GUANTXIP is the default):

- **DiHalt** (`V9990/assets/`): the original v1.0 art, read with the strict 64-colour checks.
- **Guantxip** (`V9990/assets-guantxip/`): the V9990 remake art by Guantxip. `original/` keeps his sheets as delivered; `baldosas-mapa.json` and `figuras-mapa.json` map each port tile and pose to its place in those sheets. `python3 V9990/tools/import_guantxip.py` regenerates `tiles/`, `sprites/`, `hud.png`, `life.png`, `palettes.json` and `font-styles.json`. Guantxip's terrain has its own 16-colour palette per family (stages 1-3/7-9 and 4-6); the second one is streamed when the family changes.

`V9990/tools/gfx_sets.py` compiles either set into the same blobs (patterns, HUD names, terrain, sprite master, pose descriptors, palettes) and packs them into stream records in ROM banks 58-63 and 75 onwards; `port_ui.asm` (`ui_apply_set`, `ui_family`) streams them into VRAM/RAM at game start.

## Precompiled music, SFX and opening

Setting `MADMIX_PREBUILT=/path` makes `build_port.py` take `music-events.bin/json`, `sfx-runs-0/1.bin`, `sfx-table.inc` and `opening-b3.bin` from that folder instead of rebuilding them from the PSG captures. With the files extracted from the v1.0 ROM, the unmodified sources rebuild v1.0 byte for byte.

## Assembler

The build was also checked with sjasmplus 1.24 through a small wrapper that offers SJASM 0.42's command line (`SJASM=/path/to/wrapper`): it splits `DB` lines longer than 128 values and writes the `.lst` symbol lines the build reads.

## Mapper detection

The ROM pads its last bank with `LD ($7000),A` and `LD ($77FF),A` patterns so that openMSX and blueMSX detect ASCII16 on their own; the build asserts it.
