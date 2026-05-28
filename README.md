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

List of supported functions for conversions and calibration:

| Command | Description |
| --- | --- |
| `brix-to-sg --brix` | Convert Brix to specific gravity. |
| `sg-to-plato --sg` | Convert specific gravity to Plato. |
| `hydrometer --sg --temp --calib-temp` | Correct hydrometer for sample temperature. |
| `refractometer --brix --og` | Correct refractometer reading for alcohol. |


List of supported functions for must blending and additions:

| Command | Description |
| --- | --- |
| `add [--vol --sg --ph \| --recipe] --fermentable --mass` | Add a fermentable to a must. |
| `add-fruit [--vol --sg --ph \| --recipe] --fruit --mass [--extract-yield]` | Add solid fruit |
| `add-fruit-juice [--vol --sg --ph \| --recipe] --fruit --juice-vol` | Add fruit juice to a must. |
| `add-honey [--vol --sg --ph \| --recipe] --mass` | Add honey to a must. |
| `add-sugar [--vol --sg --ph \| --recipe] --mass` | Add table sugar to a must. |
| `add-water [--vol --sg --ph \| --recipe] --mass` | Add water to a must. |
to a must. |
| `combine [--vol1 --sg1 --ph1 \| --recipe1] [--vol2 --sg2 --ph2 \| --recipe2]` | Combine two musts into one. |
| `volumes [--vol --og \| --recipe] [--fermentable] [--base]` | Compute fermentable/base amounts for a must. |


List of supported functions for backsweetening and fortification:

| Command | Description |
| --- | --- |
| `adjust-gravity [--vol --og \| --recipe] --target-sg (--fermentable \| --fruit)` | Compute additions to reach target gravity. |
| `backsweeten [--vol \| --recipe ] --final-sg --target-sg (--fermentable \| --fruit)` | Backsweeten amount to target gravity. |
| `fortify-abv [--vol --og \| --recipe] --fg --spirit-vol [--spirit-abv] [--method]` | Compute ABV after fortification. |
| `fortify-volume [--vol --og \| --recipe] --abv --fg [--spirit-abv] [--method]` | Compute spirit volume for fortification. |


List of supported functions for adjuncts and adjustments:

| Command | Description |
| --- | --- |
| `pitching [--vol --og \| --recipe]` | Compute yeast and Go-Ferm pitch amounts. |
| `priming [--vol \| --recipe] --co2 --temp --fermentable` | Compute priming sugar. |
| `so2-target [--vol --og \| --recipe] [--target-ppm]` | Compute sulfite additions from target ppm. |
| `so2-ph [--vol --og \| --recipe] --ph [--target-mol-so2]` | Compute sulfite additions from pH. |
| `ta [--vol \| --recipe] --current-ta --target-ta [--acid]` | Compute acid addition to raise TA. |
| `tosna [--vol --og \| --recipe] --yeast` | Compute TOSNA 3.0 nutrient schedule. |


List of supported functions for must planning and miscellaneous calculations:

| Command | Description |
| --- | --- |
| `attenuation [--og \| --recipe] --fg` | Compute apparent attenuation. |
| `original-gravity --abv [--fg] [--method] [--tol] [--max-og]` | Compute OG needed for target ABV. |
| `potential-abv [--og \| --recipe] [--fg] [--method]` | Compute potential ABV from OG and FG. |
| `residual-co2 --temp` | Compute residual dissolved CO2. |
| `stalled-gravity [--og \| --recipe] --yeast [--method] [--tol] [--min-fg]` | Estimate stall gravity from yeast tolerance. |


List of supported functions for adding fermentables, fruit and yeast types to the database:

| Command | Description |
| --- | --- |
| `new-fermentable --name --ppg --density --ph` | Add a fermentable entry. |
| `new-fruit --name --brix --moisture --ph` | Add a fruit profile entry. |
| `new-yeast --name --abv-limit --nitrogen` | Add a yeast strain entry. |


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

Functions `new-fermentable`, `new-fruit` and `new-yeast` allow adding new fermentable, fruit and yeast strains permanently, which can be referred in any calculations. Example:

```bash
mead new-fruit --name tulaberry --brix 18 --moisture 84 --ph 3.5
```

will add the `tulaberry` to the `fruits.json` so it can be referred in calculations involving fruit additions.


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
