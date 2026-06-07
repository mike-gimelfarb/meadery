# <img src="https://github.com/mike-gimelfarb/meadery/blob/main/meadery.svg" width="92" style="vertical-align: middle;"> meadery

[Installation](#installation) | [Running](#running) | [Supported Commands](#supported-commands) | [Ingredients and Additives](#ingredients-and-additives) | [Recipe Files](#recipe-files)

A command-line toolkit for mead-making calculations and must planning.

## Installation

Install with git:

```bash
pip install git+https://github.com/mike-gimelfarb/meadery
```

## Running

The easiest way to run commands is to use the console-native graphical editor `trogon`:

```bash
meadery tui
```

Commands can be provided using the root `meadery` followed by the name of the command, for example to list all commands or calculate the attenuation:

```bash
meadery --help
meadery attenuation --og 1.110 --fg 1.010
```

## Supported Commands

General usage notes:
- `--recipe` arguments take priority over manual arguments such as `--vol, --og`, `--ph`
- by default, `--method duncan`, `--tol 1e-6`, `--spirit-abv 40`, `--extract-yield 1`, `--wcf 1.04`, `--target-mol-so2 0.8`.

### Conversion Formulas and Calibration

| Command | Description |
| --- | --- |
| `brix-to-sg --brix` | Convert Brix to specific gravity. [^lincoln] |
| `sg-to-brix --sg` | Convert specific gravity to Brix. [^absc] |
| `spirit-gravity --abv` | Estimate gravity of neutral spirit. [^oiml] |
| `hydrometer --sg --temp --calib-temp` | Correct hydrometer for sample temperature. [^glance] |
| `refractometer --og --brix` | Correct refractometer reading for alcohol. [^terrill] |

[^lincoln]: uses the Lincoln formula published in "Brew Your Own (BYO) Magazine"
[^absc]: uses the ASBC polynomial
[^oiml]: uses a 4th order alcohol density regression formula
[^glance]: uses the Kent Glass polynomial (or Glance polynomial) for water density
[^terrill]: uses Terrill's New Cubic formula (2012)


### Must Statistics

| Command | Description |
| --- | --- |
| `abv [--og \| --recipe] --fg [--method]` | Compute ABV from OG and FG. |
| `abv-dual --brix --fg [--wcf]` | Compute ABV without original gravity using refractometer and hydrometer estimates. [^bonham] |
| `abv-potential [--og \| --recipe] [--method]` | Compute potential ABV from OG. |
| `attenuation [--og \| --recipe] --fg` | Compute apparent attenuation. |
| `load-recipe <file>` | Print summary of must from a recipe file. |
| `original-gravity --target-abv --target-fg [--method] [--tol] [--max-og]` | Compute OG needed for target ABV. [^brentq] |
| `residual-co2 --temp` | Compute residual dissolved CO2. [^henry] |
| `stalled-gravity [--og \| --recipe] --yeast [--method] [--tol] [--min-fg]` | Estimate stall gravity from yeast tolerance. [^brentq] |

[^bonham]: uses the Dual-Instrument ABV formula published in "Brew Your Own (BYO) Magazine"
[^brentq]: uses Brent's iterative root finding algorithm to numerically solve for this
[^henry]: based on Henry's law


### Must Additions and Adjustments

| Command | Description |
| --- | --- |
| `add [--vol --og --ph --pka --cbuf \| --recipe] --fermentable --mass` | Add a fermentable to a must. [^hh] |
| `add-acid [--vol --og --ph --pka --cbuf \| --recipe] [--acid] --mass [--tol]` | Add a acid to a must. |
| `add-base [--vol --og --ph --pka --cbuf \| --recipe] [--base] --mass [--tol]` | Add a base to a must. |
| `add-fruit [--vol --og --ph --pka --cbuf \| --recipe] --fruit --mass [--extract-yield]` | Add solid fruit to a must. |
| `add-fruit-juice [--vol --og --ph --pka --cbuf \| --recipe] --fruit --juice-vol` | Add fruit juice to a must. |
| `add-honey [--vol --og --ph --pka --cbuf \| --recipe] --mass` | Add honey to a must. |
| `add-sugar [--vol --og --ph --pka --cbuf \| --recipe] --mass` | Add table sugar to a must. |
| `add-water [--vol --og --ph --pka --cbuf \| --recipe] --mass` | Add spring water to a must. |
| `adjust-gravity [--vol --og \| --recipe] --target-og (--fermentable \| --fruit)` | Compute additions to reach target gravity. [^brentq] |
| `combine [--vol1 --og1 --ph1 --pka1 --cbuf1 \| --recipe1] [--vol2 --og2 --ph2 --pka2 --cbuf2 \| --recipe2]` | Combine two musts into one. |
| `solve-recipe --recipe [--target-og] [--target-vol] [--target-ph]` | Solve unknowns in a recipe file to match target OG, volume and pH. [^slsqp] |
| `volumes --target-og --target-vol [--fermentable] [--dilutant]` | Compute fermentable amounts required for OG and volume. [^pearson] |

[^hh]: solves the complete transcendental electrical charge-balance equation using Brent's iterative root finding algorithm
[^slsqp]: uses the SLSQP algorithm for constrained optimization


### Pitching, Nutrients, Acid Adjustments and Sulfites

| Command | Description |
| --- | --- |
| `acidify [--vol --ph --pka --cbuf \| --recipe] --target-ph [--acid]` | Compute acid addition to reduce pH. [^chargebalance] |
| `acidify-ta [--vol \| --recipe] --current-ta --target-ta [--acid]` | Compute acid addition to raise TA. |
| `adjust-ph-strip [--ph --pka --cbuf \| --recipe] --strip-ph --parts-water [--fermentable]` | Adjust pH strip estimate for dilution. [^hh] |
| `deacidify [--vol --ph --pka --cbuf \| --recipe] --target-ph [--base]` | Compute base addition to increase pH. [^chargebalance] |
| `nutrient [--vol --og \| --recipe] --yeast` | Compute Fermaid O nutrient schedule. [^tosna] |
| `pitch [--vol --og \| --recipe]` | Compute yeast and Go-Ferm pitch amounts. [^goferm] |
| `sulfite-ph [--vol --ph \| --recipe] [--target-mol-so2]` | Compute sulfite additions from pH. [^hhso2] |
| `sulfite-ppm [--vol \| --recipe] --target-ppm` | Compute sulfite additions from target ppm. [^so2ppm] |

[^chargebalance]: solves the charge-balance equation exactly
[^tosna]: follows the TOSNA 3.0 nutrient schedule
[^hhso2]: uses the free SO2 Henderson-Hasselbalch equation
[^goferm]: follows the rehydration guidelines of Lallemand
[^so2ppm]: conversion of target ppm to mass via standard K2S2O5 -> SO2 stoichiometric weight ratio (0.57)


### Blending

| Command | Description |
| --- | --- |
| `blend-to-abv --abv1 --abv2 --target-abv --target-vol` | Blend two fermented musts to a final ABV. [^pearson] |
| `blend-to-gravity --fg1 --fg2 --target-fg --target-vol` | Blend two fermented musts to a final gravity. [^pearson] |
| `blend-to-ph [--ph1 --pka1 --cbuf1 \| --recipe1] [--ph2 --pka2 --cbuf2 \| --recipe2] --target-ph --target-vol [--tol]` | Blend two musts to a final pH. [^brentq] |
| `blend-nearest --abvs --fgs --target-abv --target-fg --target-vol [--w-abv] [--w-fg] [--extra-limit] [--extra-fermentable] [--extra-spirit-abv]` | Blend any number of musts to achieve a final ABV and gravity as close as possible. [^slsqp] |

[^pearson]: uses Pearson's square blending ratio


For `blend-nearest`, specify `--abvs` and `--fgs` using repeated flags, e.g.:

```bash
meadery blend-nearest --abvs 10 --abvs 14 --fgs 1 --fgs 0.99 --target-abv 14 --target-fg 1.0 --target-vol 3800
```

Since an exact blend cannot always be achieved using two musts, you can allow the command to include water, a spirit and a fermentable when blending. To do this, pass a positive value for `--extra-limit` to specify the maximum proportion of these additives.


### Post-Fermentation Adjustments (Backsweetening, Fortification and Priming)

| Command | Description |
| --- | --- |
| `backsweeten [--vol \| --recipe ] --fg --target-fg (--fermentable \| --fruit)` | Backsweeten amount to target gravity. [^brentq] |
| `fortify [--vol \| --recipe] --current-abv --target-abv [--spirit-abv]` | Compute spirit volume for fortification. [^pearson] |
| `fortify-fg [--vol --og \| --recipe] --target-abv --target-fg [--spirit-abv] [--method]` | Compute spirit volume for fortification with target final gravity. [^brentq] |
| `fortify-abv [--vol --og \| --recipe] --fg --spirit-vol [--spirit-abv] [--method]` | Compute ABV after fortification. |
| `prime [--vol \| --recipe] --co2 --temp --fermentable` | Compute priming sugar. [^prime] |

[^prime]: uses the equivalent mass priming sugar formula


### Adding New Types

| Command | Description |
| --- | --- |
| `new-fermentable --name --ppg --density --ph --pka --cbuf` | Add a fermentable entry. |
| `new-fruit --name --brix --moisture --ph --pka --cbuf` | Add a fruit profile entry. |
| `new-yeast --name --abv-limit --nitrogen` | Add a yeast strain entry. |


### ABV Calculation Methods

Current ABV calculation methods `--method` (default `balling`):
- `asbc` [^abscabv], `balling` [^ballingabv], `berry` [^berryabv], `cutaia` [^cutaiaabv], `duncan` [^duncanabv], `hall` [^hallabv], `standard` [^standardabv]. 

[^abscabv]: standard of the American Society of Brewing Chemists (ASBC)
[^ballingabv]: popularized by De Clerck in "A Textbook of Brewing" (1957)
[^berryabv]: described in "First Steps in Winemaking" by C. J. J. Berry (1987)
[^cutaiaabv]: Cutaia-Reid-Speers formula derived from beer data and published in (2009)
[^duncanabv]: described in "Progressive Winemaking" by Peter Duncan and Bryan Acton (1967)
[^hallabv]: described in "Brew by the Numbers: The Mathematics of Homebrewing" by M. L. Hall (1995)
[^standardabv]: simple linear formula popularized by C. Papazian in "The Joy of Homebrewing" (1984)


Current potential ABV calculations methods `--method` (default `cooke`):
- `cooke` [^cookeabv],`dubrunfaut` [^dubrunfautabv], `honneyman` [^honneymanabv], `margalit` [^margalitabv], `marsh` [^marshabv], `pambianchi` [^pambianchiabv].  

[^cookeabv]: proposed by Cooke and Lapsley (1988) (implemented according to the formula on the FermCalc website)
[^dubrunfautabv]: reported by Boulton et al (1999) and attributed to Dubrunfaut (implemented according to the formula on the FermCalc website)
[^honneymanabv]: proposed by Honneyman (1966) (implemented according to the formula on the FermCalc website)
[^margalitabv]: proposed by Margalit (2004) (implemented according to the formula on the FermCalc website)
[^marshabv]: proposed by Marsh (1958) (implemented according to the formula on the FermCalc website)
[^pambianchiabv]: proposed by Pambianchi (2008) (implemented according to the formula on the FermCalc website)


## Ingredients and Additives

### Fermentables

Current fermentables are defined in `meadery/data/fermentables.json`:
- water (`water`, `hard-water`, `spring-water`, `filtered-water`)
- `honey`
- `maple`
- `agave`
- `molasses`
- `table-sugar`
- `brown-sugar`
- `corn-sugar`
- `liquid-malt-extract`
- `dry-malt-extract`
- `star-san-concentrate`

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
- `71b`, `ec1118`, `k1v1116`, `qa23`, `d47`, `s04`, `us05`, `m05`, `rc212`, `voss-kveik`, `montrachet`, `bread`.

### Acids and Bases

Current acids `--acid` (default `acid-blend`):
- `tartaric`, `malic`, `citric`, `acid-blend` (LD Carlson brand).

Current bases `--base` (default `potassium-bicarbonate`):
- `calcium-carbonate`, `magnesium-carbonate`, `potassium-carbonate`, `potassium-bicarbonate`, `sodium-bicarbonate`.


### Adding New Ingredients and Additives

Functions `new-fermentable`, `new-fruit` and `new-yeast` allow adding new fermentable, fruit and yeast strains permanently to the json, which can then be referred to in any calculations, e.g.:

```bash
meadery new-fruit --name tulaberry --brix 18 --moisture 84 --ph 3.5 --pka 3.40 --cbuf 40
```


## Recipe Files

### General Format

Many functions accept a `--recipe` argument, which is either an absolute or relative path to a `.recipe` file. Recipe files make it easy to manage existing recipes and musts, and run commands without manually computing `--vol`, `--og`, `--ph`, `--pka` or `--cbuf`.

Rules:
- One instruction per non-empty line of the form `<ingredient>=<quantity>`.
- `<ingredient>` must be a valid fermentable, fruit, acid or base, matched case-insensitively.
- `<quantity>` for fermentable, fruit, acid or base is in grams.
- Fruit juice lines use the form `<fruit> juice=<quantity>`, e.g. `blueberry juice=500`, where `<quantity>` is in mL.
- `water` is a fermentable with unit density.
- Lines beginning with `#` or blank lines are ignored.

Example:
```
# sample recipe
honey=500
water=2500
blueberry juice=1000
table-sugar=200
acid-blend=2
```

### Solving for Unknown Quantities in a Recipe

The `--solve-recipe` command allows some ingredients in a recipe file to have unknown quantities, e.g.:

```
# sample recipe with unknowns
honey=x
water=y
blueberry juice=1000
acid-blend=z
```

will determine the amount of honey, water and acid blend required to match target OG, volume and pH desired. The number of unknowns must match the number of targets.