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

## Current Commands

- `convert sg-to-plato --sg`
- `convert brix-to-sg --brix`
- `correct hydrometer --sg --temp --calib-temp`
- `correct refractometer --brix --og`
- `must combine --vol1 --sg1 --vol2 --sg2`
- `must add --vol --sg --fermentable --mass`
- `must add-water --vol --sg --mass`
- `must add-honey --vol --sg --mass`
- `must add-sugar --vol --sg --mass`
- `must add-fruit --vol --sg --mass [--fruit | (--brix and --moisture)] [--extract-yield]`
- `calc fortify-volume --vol --og --abv --fg [--spirit-abv] [--method]`
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

## Dynamic Fermentables And Fruits

`must add`, `must add-fruit`, and `calc dilution` use values from `mead_tools.core` at runtime.

Current fermentables are defined in `FERMENTABLES`:
- `water`
- `white-grape-juice`
- `honey`
- `maple`
- `agave`
- `molasses`
- `table-sugar`
- `brown-sugar`

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
