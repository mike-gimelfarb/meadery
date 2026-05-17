# mead-tools

A command-line toolkit for mead-making calculations and must planning.

## Install

Install in editable mode from this folder:

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
- `calc`: ABV, attenuation, original gravity, dilution, stalled gravity
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
- `must fortify-volume --vol --og --abv --fg [--spirit-abv] [--method]`
- `calc potential-abv --og [--fg] [--method]`
- `calc attenuation --og --fg`
- `calc stalled-gravity --og --max-abv [--method] [--tol] [--min-fg]`
- `calc original-gravity --abv [--fg] [--method] [--tol] [--max-og]`
- `calc dilution --vol --og [--fermentable] [--base]`
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
- `cherry-sweet`
- `strawberry`
- `raspberry`
- `blackberry`
- `blueberry`
- `cranberry`
- `elderberry`
- `grape-wine`
- `grape-late-harvest`

## Examples

All volumes are in ml, all masses in grams.

```bash
mead convert sg-to-plato --sg 1.100
mead convert brix-to-sg --brix 24

mead correct hydrometer --sg 1.080 --temp 25 --calib-temp 20
mead correct refractometer --brix 10 --og 1.110

mead must combine --vol1 2000 --sg1 1.090 --vol2 1500 --sg2 1.040
mead must add --vol 3500 --sg 1.090 --fermentable honey --mass 500
mead must add-water --vol 3500 --sg 1.090 --mass 300
mead must add-fruit --vol 3800 --sg 1.080 --mass 1500 --fruit grape-late-harvest
mead must add-fruit --vol 3800 --sg 1.080 --mass 1500 --brix 18 --moisture 82 --extract-yield 0.75

mead calc potential-abv --og 1.110 --fg 1.010 --method alternate
mead calc attenuation --og 1.110 --fg 1.010
mead calc stalled-gravity --og 1.110 --max-abv 14 --method cutaia
mead calc original-gravity --abv 12 --fg 1.010 --method cutaia
mead calc dilution --vol 4000 --og 1.110 --fermentable honey --base water

mead adjust tosna3 --vol 3800 --og 1.100 --yeast-demand medium
mead adjust so2-target --vol 3800 --og 1.000 --target-ppm 50
mead adjust so2-ph --vol 3800 --og 1.000 --ph 3.5 --target-mol-so2 0.8
```

## JSON Output

Use `--format json` for machine-friendly output:

```bash
mead calc potential-abv --og 1.110 --fg 1.010 --format json
```
