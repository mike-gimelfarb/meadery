# mead-tools

A command-line toolkit for common mead-making calculations.

## Install

Install in editable mode from this folder:

```bash
pip install -e .
```

## Run

Use the installed command:

```bash
mead --help
```

Or run directly with Python:

```bash
python main.py --help
```

## Command Groups

- `convert`: SG/Brix/Plato conversions
- `correct`: Hydrometer and refractometer corrections
- `must`: Must combining and additive operations
- `calc`: ABV, attenuation, and stalled FG calculations
- `adjust`: TOSNA and SO2 adjustment calculations

## Examples

```bash
mead convert sg-to-plato --sg 1.100
mead convert brix-to-sg --brix 24
mead correct hydrometer --gravity 1.080 --temperature 25 --calib-temp 20
mead correct refractometer --current-brix 10 --original-gravity 1.110

mead must combine --volume-a 2000 --gravity-a 1.090 --volume-b 1500 --gravity-b 1.040
mead must add --volume 3500 --gravity 1.090 --additive honey --mass 500
mead must add-water --volume 3500 --gravity 1.090 --mass 300

mead calc potential-abv --volume 4000 --gravity 1.110 --fg 1.010 --method alternate
mead calc attenuation --volume 4000 --gravity 1.110 --fg 1.010
mead calc stalled-fg --volume 4000 --gravity 1.110 --yeast-abv-limit 14 --method cutaia

mead adjust tosna3 --volume 3800 --gravity 1.100 --yeast-demand medium
mead adjust so2-target --volume 3800 --gravity 1.000 --target-ppm 50
mead adjust so2-ph --volume 3800 --gravity 1.000 --ph 3.5 --target-mol-so2 0.8
```

## JSON Output

Most commands support machine-friendly output:

```bash
mead calc potential-abv --volume 4000 --gravity 1.110 --fg 1.010 --format json
```
