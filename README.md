# <img src="https://github.com/mike-gimelfarb/meadery/blob/main/meadery.svg" width="92" style="vertical-align: middle;"> meadery

A command-line toolkit for mead-making calculations and must planning.

## Install

Install with git:

```bash
pip install git+https://github.com/mike-gimelfarb/meadery
```

## Run

The easiest way to run commands is to use the console-native graphical editor `trogon`:

```bash
meadery tui
```

Commands can be provided explicitly using the root keyword `meadery` followed by the name of the command, for example to list all commands or calculate the attenuation:

```bash
meadery --help
meadery attenuation --og 1.110 --fg 1.010
```

## Supported Functions

General notes on usage:
- `--recipe` arguments always take priority over manual arguments, e.g., `--vol, --og`
- default values: `--method` is `duncan`, `--tol` is 1e-6, `--spirit-abv` is 40, `--extract-yield` is 1

### Conversion Formulas and Calibration

| Command | Description |
| --- | --- |
| `brix-to-sg --brix` | Convert Brix to specific gravity. |
| `sg-to-plato --sg` | Convert specific gravity to Plato. |
| `spirit-gravity --abv`  | Estimate gravity of neutral spirit. |
| `hydrometer --sg --temp --calib-temp` | Correct hydrometer for sample temperature. |
| `refractometer --og --brix` | Correct refractometer reading for alcohol. |

### Must Statistics

| Command | Description |
| --- | --- |
| `abv [--og \| --recipe] --fg [--method]` | Compute ABV from OG and FG. |
| `abv-potential [--og \| --recipe] [--method]` | Compute potential ABV from OG. |
| `attenuation [--og \| --recipe] --fg` | Compute apparent attenuation. |
| `load-recipe <file>` | Print summary of must from a recipe file. |
| `original-gravity --target-abv --target-fg [--method] [--tol] [--max-og]` | Compute OG needed for target ABV. |
| `residual-co2 --temp` | Compute residual dissolved CO2. |
| `stalled-gravity [--og \| --recipe] --yeast [--method] [--tol] [--min-fg]` | Estimate stall gravity from yeast tolerance. |

### Must Additions and Adjustments

| Command | Description |
| --- | --- |
| `add [--vol --og --ph \| --recipe] --fermentable --mass` | Add a fermentable to a must. |
| `add-fruit [--vol --og --ph \| --recipe] --fruit --mass [--extract-yield]` | Add solid fruit to a must. |
| `add-fruit-juice [--vol --og --ph \| --recipe] --fruit --juice-vol` | Add fruit juice to a must. |
| `add-honey [--vol --og --ph \| --recipe] --mass` | Add honey to a must. |
| `add-sugar [--vol --og --ph \| --recipe] --mass` | Add table sugar to a must. |
| `add-water [--vol --og --ph \| --recipe] --mass` | Add water to a must. |
| `adjust-gravity [--vol --og \| --recipe] --target-og (--fermentable \| --fruit)` | Compute additions to reach target gravity. |
| `combine [--vol1 --og1 --ph1 \| --recipe1] [--vol2 --og2 --ph2 \| --recipe2]` | Combine two musts into one. |
| `volumes --target-og --target-vol [--fermentable] [--base]` | Compute fermentable/base amounts required. |

### Pitching, Nutrients, TA and Sulfites

| Command | Description |
| --- | --- |
| `pitch [--vol --og \| --recipe]` | Compute yeast and Go-Ferm pitch amounts. |
| `so2-ph [--vol --ph \| --recipe] [--target-mol-so2]` | Compute sulfite additions from pH. |
| `so2-target [--vol \| --recipe] [--target-ppm]` | Compute sulfite additions from target ppm. |
| `ta [--vol \| --recipe] --current-ta --target-ta [--acid]` | Compute acid addition to raise TA. |
| `tosna [--vol --og \| --recipe] --yeast` | Compute TOSNA 3.0 nutrient schedule. |

### Blending

| Command | Description |
| --- | --- |
| `blend-to-abv --abv1 --abv2 --target-abv --target-vol` | Blend two fermented musts to a final ABV. |
| `blend-to-gravity --fg1 --fg2 --target-fg --target-vol` | Blend two fermented musts to a final gravity. |
| `blend-nearest --abvs --fgs --target-abv --target-fg --target-vol [--w-abv] [--w-fg][--extra-limit]` | Blend any number of musts to achieve a final ABV and gravity as close as possible. |

### Post-Fermentation Adjustments (Backsweetening, Fortification and Priming)

| Command | Description |
| --- | --- |
| `backsweeten [--vol \| --recipe ] --fg --target-fg (--fermentable \| --fruit)` | Backsweeten amount to target gravity. |
| `fortify [--vol \| --recipe] --current-abv --target-abv [--spirit-abv]` | Compute spirit volume for fortification. |
| `fortify-fg [--vol --og \| --recipe] --target-abv --target-fg [--spirit-abv] [--method]` | Compute spirit volume for fortification with target final gravity. |
| `fortify-abv [--vol --og \| --recipe] --fg --spirit-vol [--spirit-abv] [--method]` | Compute ABV after fortification. |
| `prime [--vol \| --recipe] --co2 --temp --fermentable` | Compute priming sugar. |

### Adding New Types

| Command | Description |
| --- | --- |
| `new-fermentable --name --ppg --density --ph` | Add a fermentable entry. |
| `new-fruit --name --brix --moisture --ph` | Add a fruit profile entry. |
| `new-yeast --name --abv-limit --nitrogen` | Add a yeast strain entry. |

## ABV Calculation Methods

- `standard`: simple linear formula, fast but inaccurate for wine/mead gravities
- `berry`: described in "First Steps in Winemaking" by C. J. J. Berry (1987)
- `alternate`: non-linear Hall formula, more accurate for higher gravities than the above
- `duncan`: described in "Progressive Winemaking" by Peter Duncan and Bryan Acton (1967)
- `cutaia`: Cutaia-Reid-Speers formula, accurate but derived from beer data.

The current default in all calculations is `duncan`, unless specified in `--method`.

For potential abv calculations, the options are currently `dubrunfaut`, `marsh`, `margalit`, `cooke`, `pambianchi` and `honneyman`, the default is `cooke`.


## Dynamic Fermentables, Fruits and Yeast Strains

### Fermentables

Current fermentables are defined in `meadery/data/fermentables.json`:
- `water`
- `honey`
- `maple`
- `agave`
- `molasses`
- `table-sugar`
- `brown-sugar`
- `corn-sugar`
- `liquid-malt-extract`
- `dry-malt-extract`

### Fruits

Current fruits are defined in `meadery/data/fruits.json`:
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
- `lemon`
- `orange`
- `pineapple`

### Yeast Strains

Current yeast strains are defined in `meadery/data/yeasts.json`:
- `71b`, `ec1118`, `k1v1116`, `qa23`, `d47`, `s04`, `us05`, `m05`, `rc212`, `voss-kveik`, `montrachet`, `bread`

### Adding New Objects

Functions `new-fermentable`, `new-fruit` and `new-yeast` allow adding new fermentable, fruit and yeast strains permanently, which can be referred in any calculations, for instance

```bash
meadery new-fruit --name tulaberry --brix 18 --moisture 84 --ph 3.5
```

will add the `tulaberry` to the `fruits.json` so it can be referred in calculations involving fruit additions.


## Recipe Files

Many functions accept a `--recipe` argument instead of volume, original graviy and ph, which is either an absolute path to a `.recipe` file, or relative path from the current working sub-directory. Recipe files make it easy to manage existing recipes and musts, and perform calculations or determine adjustments for them.

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
