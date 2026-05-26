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

- `sg-to-plato --sg`: convert specific gravity to plato
- `brix-to-sg --brix`: convert brix to specific gravity
- `hydrometer --sg --temp --calib-temp`: calibrate hydrometer for temperature
- `refractometer --brix --og`: calubrate refractometer for alcohol
- `combine --vol1 --sg1 --ph1 --vol2 --sg2 --ph2`: combine two musts
- `add --vol --sg --ph --fermentable --mass`: add a fermentable to must
- `add-water --vol --sg --ph --mass`: add water to must
- `add-honey --vol --sg --ph --mass`: add honey to must
- `add-sugar --vol --sg --ph --mass`: add sugar to must
- `add-fruit --vol --sg --ph --fruit --mass [--extract-yield]`: add solid fruit to must
- `add-fruit-juice --vol --sg --ph --fruit --juice-vol`: add fruit juice to must
- `from-recipe <file>`: load must from recipe file
- `fortify-volume --vol --og --abv --fg [--spirit-abv] [--method]`: calculate spirit volume to fortify
- `fortify-abv --vol --og --fg --spirit-vol [--spirit-abv] [--method]`: calculate abv after fortification
- `potential-abv --og [--fg] [--method]`: calculate potential abv
- `attenuation --og --fg`: calculate attenuation
- `stalled-gravity --og --yeast [--method] [--tol] [--min-fg]`: calculate potential final gravity from yeast strain
- `original-gravity --abv [--fg] [--method] [--tol] [--max-og]`: calculate original gravity from final gravity and abv
- `residual-co2 --temp`: calculate residual CO2
- `volumes --vol --og [--fermentable] [--base]`: calculate volumes from gravity
- `priming-sugar --vol --co2 --temp --fermentable`: calculate priming sugar
- `gravity --vol --og --target-sg (--fermentable | --fruit)`: calculate volume to change gravity
- `ta --vol --current-ta --target-ta [--acid]`: calculate acid adjustment
- `pitching --vol --og`: calculate yeast pitch rate
- `tosna3 --vol --og --yeast`: calculate nutrient rate
- `so2-target --vol --og [--target-ppm]`: calculate sulfite rate
- `so2-ph --vol --og --ph [--target-mol-so2]`: calculate sulfite rate from ph

All commands support `--format text|json`.
`--spirit-vol` value is 40 by default.


## ABV Calculation Methods

- `standard`: simple linear formula, fast but inaccurate for typical wine/mead gravities
- `alternate`: non-linear Hall formula, more accurate for higher gravities
- `cutaia`: Cutaia-Reid-Speers formula, most accurate and currently the default


## Dynamic Fermentables And Fruits

`add`, `add-fruit`, and `volumes` use values from `mead_tools.core` at runtime.

Current fermentables are defined in `FERMENTABLES`:
- `water`
- `honey`
- `maple`
- `agave`
- `molasses`
- `table-sugar`
- `brown-sugar`
- `liquid-malt-extract`

Current fruits are defined in `FRUITS`:
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
