# mead-tools

A command-line toolkit for mead-making calculations and must planning.

## Install

Install with git:

```bash
pip install git+https://github.com/mike-gimelfarb/mead-tools
```

## Run

Installed console script:

```bash
mead --help
```

Commands are available directly at the top level, for example:

```bash
mead attenuation --og 1.110 --fg 1.010
```

## Supported Functions

| Command | Description |
| --- | --- |
| `sg-to-plato --sg` | Convert specific gravity to Plato. |
| `brix-to-sg --brix` | Convert Brix to specific gravity. |
| `hydrometer --sg --temp --calib-temp` | Correct hydrometer SG for sample temperature. |
| `refractometer --brix --og` | Correct refractometer reading for alcohol. |
| `combine --vol1 --sg1 --ph1 --vol2 --sg2 --ph2` | Combine two musts into one. |
| `add --vol --sg --ph --fermentable --mass` | Add a fermentable to a must. |
| `add-water --vol --sg --ph --mass` | Add water to a must. |
| `add-honey --vol --sg --ph --mass` | Add honey to a must. |
| `add-sugar --vol --sg --ph --mass` | Add table sugar to a must. |
| `add-fruit --vol --sg --ph --fruit --mass [--extract-yield]` | Add solid fruit to a must. |
| `add-fruit-juice --vol --sg --ph --fruit --juice-vol` | Add fruit juice to a must. |
| `from-recipe <file>` | Build must stats from a recipe file. |
| `fortify-volume --vol --og --abv --fg [--spirit-abv] [--method]` | Compute spirit volume needed for fortification. |
| `fortify-abv --vol --og --fg --spirit-vol [--spirit-abv] [--method]` | Compute ABV after fortification. |
| `potential-abv --og [--fg] [--method]` | Compute potential ABV from OG and FG. |
| `attenuation --og --fg` | Compute apparent attenuation. |
| `stalled-gravity --og --yeast [--method] [--tol] [--min-fg]` | Estimate stall gravity from yeast ABV tolerance. |
| `original-gravity --abv [--fg] [--method] [--tol] [--max-og]` | Compute OG needed for a target ABV. |
| `residual-co2 --temp` | Compute residual dissolved CO2 by temperature. |
| `volumes --vol --og [--fermentable] [--base]` | Compute fermentable/base amounts for a target must. |
| `priming-sugar --vol --co2 --temp --fermentable` | Compute priming sugar for target carbonation. |
| `gravity --vol --og --target-sg (--fermentable \| --fruit)` | Compute additions to reach target gravity. |
| `ta --vol --current-ta --target-ta [--acid]` | Compute acid addition to raise TA. |
| `pitching --vol --og` | Compute yeast and Go-Ferm pitch amounts. |
| `tosna3 --vol --og --yeast` | Compute TOSNA 3.0 nutrient schedule. |
| `so2-target --vol --og [--target-ppm]` | Compute sulfite additions from target ppm. |
| `so2-ph --vol --og --ph [--target-mol-so2]` | Compute sulfite additions from pH and molecular SO2 target. |

All commands support `--format text|json`.
`--spirit-vol` value is 40 by default.


## ABV Calculation Methods

- `standard`: simple linear formula, fast but inaccurate for typical wine/mead gravities
- `alternate`: non-linear Hall formula, more accurate for higher gravities
- `cutaia`: Cutaia-Reid-Speers formula, most accurate and currently the default


## Dynamic Fermentables And Fruits

Current fermentables are defined in `FERMENTABLES` (`mead_tools/data/fermentables.json`):
- `water`
- `honey`
- `maple`
- `agave`
- `molasses`
- `table-sugar`
- `brown-sugar`
- `liquid-malt-extract`

Current fruits are defined in `FRUITS` (`mead_tools/data/fruits.json`):
- `apple`
- `pear`
- `peach`
- `plum`
- `apricot`
- cherry (`cherry-bing`, `cherry-montmorency`)
- `strawberry`
- `raspberry`
- `blackberry`
- `blueberry`
- `cranberry`
- `elderberry`
- `blackcurrant`
- grape (`grape-niagara`, `grape-concord`, `grape-cabernet`, `grape-late-harvest`)
- `banana`
- `pomegranate`
- `watermelon`
- `canteloupe`
- `fig`
- `mango`

Current yeast strains are defined in `YEAST_STRAINS` (`mead_tools/data/yeasts.json`):
- `71b`, `ec1118`, `k1v1116`, `qa23`, `d47`, `s04`, `us05`, `m05`, `rc212`, `voss-kveik`, `montrachet`, `bread`


## JSON Output

Use `--format json` for machine-friendly output:

```bash
mead potential-abv --og 1.110 --fg 1.010 --format json
```

## Recipe format

`mead from-recipe <file>` loads a simple, line-oriented recipe and prints the must volume, gravity and estimated ph.

Rules:
- One instruction per non-empty line: `<ingredient>=<quantity>`
- Quantities: fermentables and whole fruit are in grams; fruit juice is in milliliters.
- Fruit juice lines use the form `<fruit> juice=<ml>` (example: `blueberry juice=500`).
- `water` may be specified as a fermentable (grams; 1 g = 1 mL).
- Lines beginning with `#` or blank lines are ignored.

Example:
```
# sample recipe
honey=500
water=2500
blueberry juice=1000
table-sugar=200
```

Ingredient names are matched case-insensitively against the `FERMENTABLES` and `FRUITS` lists in the codebase.
