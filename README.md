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


## Command Groups

- `convert`: SG/Brix/Plato conversions
- `correct`: Hydrometer and refractometer corrections
- `must`: Must combining and additions
- `calc`: ABV, attenuation, original gravity, dilution, stalled gravity, fortification
- `adjust`: TOSNA and SO2 adjustment calculations

## ABV Calculation Methods

- `standard`: simple linear formula, fast but inaccurate for typical wine/mead gravities
- `alternate`: non-linear Hall formula, more accurate for higher gravities
- `cutaia`: Cutaia-Reid-Speers formula, most accurate and currently the default

## Supported Functions

- `convert sg-to-plato --sg`
- `convert brix-to-sg --brix`
- `correct hydrometer --sg --temp --calib-temp`
- `correct refractometer --brix --og`
- `must combine --vol1 --sg1 --ph1 --vol2 --sg2 --ph2`
- `must add --vol --sg --ph --fermentable --mass`
- `must add-water --vol --sg --ph --mass`
- `must add-honey --vol --sg --ph --mass`
- `must add-sugar --vol --sg --ph --mass`
- `must add-fruit --vol --sg --ph --fruit --mass [--extract-yield]`
- `must add-fruit-juice --vol --sg --ph --fruit --fruit-vol`
- `must from-recipe <file>`
- `calc fortify-volume --vol --og --abv --fg [--spirit-abv] [--method]`
- `calc fortify-abv --vol --og --fg --spirit-vol [--spirit-abv] [--method]`
- `calc potential-abv --og [--fg] [--method]`
- `calc attenuation --og --fg`
- `calc stalled-gravity --og --max-abv [--method] [--tol] [--min-fg]`
- `calc original-gravity --abv [--fg] [--method] [--tol] [--max-og]`
- `calc dilution --vol --og [--fermentable] [--base]`
- `calc dilution-to-sg --vol --og --target-sg [--fermentable]`
- `adjust tosna3 --vol --og [--yeast-demand]`
- `adjust so2-target --vol --og [--target-ppm]`
- `adjust so2-ph --vol --og --ph [--target-mol-so2]`

All commands support `--format text|json`.
`--spirit-vol` value is 40 by default.

## Dynamic Fermentables And Fruits

`must add`, `must add-fruit`, and `calc dilution` use values from `mead_tools.core` at runtime.

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
- `cherry-bing`
- `cherry-montmorency`
- `strawberry`
- `raspberry`
- `blackberry`
- `blueberry`
- `cranberry`
- `elderberry`
- `grape-wine`
- `grape-late-harvest`
- `banana`
- `pomegranate`


## JSON Output

Use `--format json` for machine-friendly output:

```bash
mead calc potential-abv --og 1.110 --fg 1.010 --format json
```

## Recipe format

`mead must from-recipe <file>` loads a simple, line-oriented recipe and prints the final must volume and gravity.

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
