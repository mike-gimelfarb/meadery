from enum import Enum
import os
from pathlib import Path
import typer
try:
    from trogon.typer import init_tui 
except ImportError:
    def init_tui(app):
        pass
from trogon.typer import init_tui
from typing import Optional, List 

from meadery.core import (
    ACID_ADJUSTMENTS, FERMENTABLES, FRUITS, YEAST_STRAINS,
    Hydrometer, Must, Refractometer,
    add_fermentable, add_fruit, add_yeast_strain,
    brix_to_sg, original_gravity, sg_to_plato, parse_recipe,
    blend_to_gravity, blend_to_abv, blend_nearest, spirit_abv_to_sg
)


# ===================================================
#                  Application Base
# ===================================================

app = typer.Typer(help="Meadery tools command-line app")


class OutputFormat(str, Enum):
    text = "text"
    json = "json"


class AbvMethod(str, Enum):
    standard = "standard"
    berry = "berry"
    alternate = "alternate"
    duncan = "duncan"
    cutaia = "cutaia"


class PotentialAbvMethod(str, Enum):
    dubrunfaut = "dubrunfaut"
    marsh = "marsh"
    margalit = "margalit"
    cooke = "cooke"
    pambianchi = "pambianchi"
    honneyman = "honneyman"


def get_fermentable_choices() -> List[str]:
    return list(FERMENTABLES.keys())


def get_fruit_choices() -> List[str]:
    return list(FRUITS.keys())


def get_yeast_choices() -> List[str]:
    return list(YEAST_STRAINS.keys())


def get_acid_choices() -> List[str]:
    return list(ACID_ADJUSTMENTS.keys())


def _validate_must(volume: float, gravity: float, ph: Optional[float] = None) -> None:
    if volume < 0:
        raise typer.BadParameter("volume must be >= 0")
    if gravity <= 0:
        raise typer.BadParameter("gravity must be > 0")
    if ph is not None and (ph < 0 or ph > 14):
        raise typer.BadParameter("pH must be between 0 and 14")


def _recipe_path(recipe: str) -> str:
    recipe_path = Path(recipe)
    if not recipe_path.is_absolute():
        recipe_path = Path(os.getcwd()) / recipe_path
    return str(recipe_path)


def _must_from_args(*, label: str, recipe: Optional[str], volume: Optional[float],
                    gravity: Optional[float], ph: Optional[float], require_ph: bool=True) -> Must:
    """Build a Must from either a recipe path or explicit volume/gravity/pH arguments."""
    manual_values = [volume, gravity, ph] if require_ph else [volume, gravity]
    has_manual = any(value is not None for value in manual_values)

    # recipe takes priority
    if recipe is not None:
        try:
            return parse_recipe(_recipe_path(recipe))
        except Exception as exc:
            raise typer.BadParameter(str(exc)) from exc

    # check manual inputs
    if not has_manual:
        req_args = "--vol, --sg, and --ph" if require_ph else "--vol and --sg"
        raise typer.BadParameter(f"{label} requires either --recipe or manual inputs ({req_args}).")
    if any(value is None for value in manual_values):
        req_args = "--vol, --sg, and --ph" if require_ph else "--vol and --sg"
        raise typer.BadParameter(f"{label} manual mode requires {req_args} together.")

    _validate_must(volume, gravity, ph)
    return Must(volume=volume, gravity=gravity, ph=ph)


def echo_boxed(message: str, color: str=None) -> None:
    lines = message.splitlines()
    width = max(len(line) for line in lines)
    top = "\n" + f"┌{'─' * (width + 2)}┐"
    bottom = f"└{'─' * (width + 2)}┘"
    typer.echo(typer.style(top, fg=color))
    for line in lines:
        typer.echo(typer.style(f"│ {line.ljust(width)} │", fg=color))
    typer.echo(typer.style(bottom, fg=color))


def get_yeast_obj(yeast: str) -> object:
    yeast_key = yeast.strip().lower()
    yeast_obj = YEAST_STRAINS.get(yeast_key, None)
    if yeast_obj is None:
        choices = ", ".join(sorted(YEAST_STRAINS.keys()))
        raise typer.BadParameter(f"Invalid yeast strain: {yeast_key}, choose from: {choices}")
    return yeast_obj


def get_fermentable_object(fermentable: str) -> object:
    fermentable_key = fermentable.strip().lower()
    fermentable_obj = FERMENTABLES.get(fermentable_key)
    if fermentable_obj is None:
        choices = ", ".join(sorted(FERMENTABLES.keys()))
        raise typer.BadParameter(f"Unknown fermentable: {fermentable_key}, choose from: {choices}")
    return fermentable_obj


def get_fruit_object(fruit: str) -> object:
    fruit_key = fruit.strip().lower()
    fruit_obj = FRUITS.get(fruit_key)
    if fruit_obj is None:
        choices = ", ".join(sorted(FRUITS.keys()))
        raise typer.BadParameter(f"Unknown fruit: {fruit_key}, choose from: {choices}")
    return fruit_obj


# ===================================================
#              Conversion and Calibration
# ===================================================

@app.command("brix-to-sg")
def convert_brix_to_sg(
    brix: float = typer.Option(..., "--brix", help="Brix value"),
) -> None:
    result = brix_to_sg(brix)
    echo_boxed(f'{round(result, 4)}')


@app.command("sg-to-plato")
def convert_sg_to_plato(
    gravity: float = typer.Option(..., "--sg", help="Specific gravity"),
) -> None:
    result = sg_to_plato(gravity)
    echo_boxed(f'{round(result, 2)}')


@app.command("spirit-gravity")
def convert_spirit_abv_to_sg(
    abv: float = typer.Option(..., "--abv", help="Spirit ABV in percent"),
) -> None:
    result = spirit_abv_to_sg(abv)
    echo_boxed(f'{round(result, 4)}')


@app.command("hydrometer")
def correct_hydrometer(
    gravity: float = typer.Option(..., "--sg", help="Measured specific gravity"),
    temperature: float = typer.Option(..., "--temp", help="Measured temperature in C"),
    calibration_temp: float = typer.Option(..., "--calib-temp", help="Hydrometer calibration temperature in C"),
) -> None:
    corrected = Hydrometer(calibration_temperature=calibration_temp).corrected_gravity(
        gravity=gravity, temperature=temperature)
    echo_boxed(f'{round(corrected, 4)}')


@app.command("refractometer")
def correct_refractometer(
    gravity: float = typer.Option(..., "--og", help="Original gravity"),
    brix: float = typer.Option(..., "--brix", help="Current measured Brix"),
) -> None:
    corrected = Refractometer().corrected_gravity(current_brix=brix, original_gravity=gravity)
    echo_boxed(f'{round(corrected, 4)}')


# ===================================================
#           Planning and Calculations
# ===================================================

@app.command("attenuation")
def calc_attenuation(
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fg: float = typer.Option(..., "--fg", help="Final gravity"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=3785.41, gravity=gravity, ph=None, require_ph=False)
    result = base_must.attenuation(fg=fg)
    echo_boxed(f'{round(result, 2)}%')


@app.command("load-recipe")
def must_load_recipe(
    recipe: str = typer.Argument(..., help="Path to recipe file"),
) -> None:
    recipe_path = _recipe_path(recipe)
    try:
        must = parse_recipe(recipe_path)
    except Exception as exc:
        raise typer.BadParameter(str(exc)) from exc
    echo_boxed(str(must))


@app.command("original-gravity")
def calc_original_gravity(
    target_abv: float = typer.Option(..., "--target-abv", help="Target ABV in percent"),
    fg: float = typer.Option(..., "--target-fg", help="Target final gravity"),
    method: AbvMethod = typer.Option(AbvMethod.duncan, "--method", help="ABV calculation method"),
    tol: float = typer.Option(1e-6, "--tol", help="Root finding tolerance"),
    max_og: float = typer.Option(1.3, "--max-og", help="Maximum original gravity bound"),
) -> None:
    result = original_gravity(
        target_abv=target_abv, fg=fg, method=method.value, tol=tol, max_og=max_og)
    echo_boxed(f'{round(result, 4)}')


@app.command("abv")
def calc_abv(
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fg: float = typer.Option(..., "--fg", help="Final gravity"),
    method: AbvMethod = typer.Option(AbvMethod.duncan, "--method", help="ABV calculation method"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=3785.41, gravity=gravity, ph=None, require_ph=False)
    result = base_must.abv(fg=fg, method=method.value)
    echo_boxed(f'{round(result, 2)}%')


@app.command("abv-potential")
def calc_potential_abv(
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    method: PotentialAbvMethod = typer.Option(PotentialAbvMethod.cooke, "--method", help="Potential ABV calculation method"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=3785.41, gravity=gravity, ph=None, require_ph=False)
    result = base_must.abv_potential(method=method.value)
    echo_boxed(f'{round(result, 2)}%')


@app.command("residual-co2")
def calc_residual_co2(
    temp: float = typer.Option(..., "--temp", help="Temperature in C"),
) -> None:
    result = Must.residual_co2(temp)
    echo_boxed(f'{round(result, 2)}volumes, {round(result * 1.96, 3)}g/L')


@app.command("stalled-gravity")
def calc_stalled_gravity(
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    yeast: str = typer.Option(..., "--yeast", help="Yeast strain name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_yeast_choices() if k.startswith(incomplete)]),
    method: AbvMethod = typer.Option(AbvMethod.duncan, "--method", help="ABV calculation method"),
    tol: float = typer.Option(1e-6, "--tol", help="Root finding tolerance"),
    min_fg: float = typer.Option(0.9, "--min-fg", help="Minimum FG for root finding"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=3785.41, gravity=gravity, ph=None, require_ph=False)
    yeast_obj = get_yeast_obj(yeast)
    result = base_must.stalled_final_gravity(
        yeast=yeast_obj, method=method.value, tol=tol, min_fg=min_fg)
    echo_boxed(f'{round(result, 4)}')


# ===================================================
#           Must Addition and Combination
# ===================================================

@app.command("add")
def must_add(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fermentable: str = typer.Option(..., "--fermentable", help="Fermentable name",
        case_sensitive=False, show_choices=True, prompt=True, 
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    mass: float = typer.Option(..., "--mass", help="Fermentable mass in grams"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=ph)
    fermentable_obj = get_fermentable_object(fermentable)
    result = base_must.add(fermentable_obj, mass=mass)
    echo_boxed(str(result))


@app.command("add-fruit")
def must_add_fruit(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Preset fruit name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
    mass: float = typer.Option(..., "--mass", help="Fruit mass in grams"),
    extract_yield: float = typer.Option(1.0, "--extract-yield", help="Extracted juice yield from 0 to 1"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=ph)
    if fruit is None:
        raise typer.BadParameter("--fruit is required")
    selected_fruit = get_fruit_object(fruit)
    try:
        result = base_must.add_fruit(selected_fruit, mass=mass, extract_yield=extract_yield)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    echo_boxed(str(result))


@app.command("add-fruit-juice")
def must_add_fruit_juice(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Preset fruit name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
    juice_volume: float = typer.Option(..., "--juice-vol", help="Fruit juice volume in mL"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=ph)
    if fruit is None:
        raise typer.BadParameter("--fruit is required")
    selected_fruit = get_fruit_object(fruit)    
    try:
        result = base_must.add_fruit_juice(selected_fruit, volume=juice_volume)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    echo_boxed(str(result))


@app.command("add-honey")
def must_add_honey(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    mass: float = typer.Option(..., "--mass", help="Honey mass in grams"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=ph)
    result = base_must.add_honey(mass=mass)
    echo_boxed(str(result))


@app.command("add-sugar")
def must_add_sugar(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    mass: float = typer.Option(..., "--mass", help="Sugar mass in grams"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=ph)
    result = base_must.add_sugar(mass=mass)
    echo_boxed(str(result))


@app.command("add-water")
def must_add_water(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    mass: float = typer.Option(..., "--mass", help="Water mass in grams"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=ph)
    result = base_must.add_water(mass=mass)
    echo_boxed(str(result))


@app.command("adjust-gravity")
def adjust_gravity(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    target_sg: float = typer.Option(..., "--target-og", help="Target original gravity after dilution"),
    fermentable: str = typer.Option(None, "--fermentable", help="Fermentable name for dilution",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Fruit name for dilution",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=None, require_ph=False)
    if fermentable is None:
        if fruit is None:
            raise typer.BadParameter("Either --fermentable or --fruit must be provided")
        fruit_obj = get_fruit_object(fruit)
        result = base_must.adjust_gravity_with_fruit_juice(target_sg=target_sg, fruit=fruit_obj)
    else:
        fermentable_obj = get_fermentable_object(fermentable)
        result = base_must.adjust_gravity(target_sg=target_sg, fermentable=fermentable_obj)
    if fruit:
        result = f'{round(result, 2)}ml'
    else:
        result = f'{round(result, 2)}g'
    echo_boxed(result)


@app.command("combine")
def must_combine(
    volume_a: Optional[float] = typer.Option(None, "--vol1", help="Must A volume in mL"),
    gravity_a: Optional[float] = typer.Option(None, "--og1", help="Must A original gravity"),
    ph_a: Optional[float] = typer.Option(None, "--ph1", help="Must A pH"),
    recipe1: Optional[str] = typer.Option(None, "--recipe1", help="Path to recipe for must A"),
    volume_b: Optional[float] = typer.Option(None, "--vol2", help="Must B volume in mL"),
    gravity_b: Optional[float] = typer.Option(None, "--og2", help="Must B original gravity"),
    ph_b: Optional[float] = typer.Option(None, "--ph2", help="Must B pH"),
    recipe2: Optional[str] = typer.Option(None, "--recipe2", help="Path to recipe for must B"),
) -> None:
    must_a = _must_from_args(
        label="Must A", recipe=recipe1, volume=volume_a, gravity=gravity_a, ph=ph_a)
    must_b = _must_from_args(
        label="Must B", recipe=recipe2, volume=volume_b, gravity=gravity_b, ph=ph_b)

    result = must_a.combine(must_b)
    echo_boxed(str(result))


@app.command("volumes")
def calc_volumes(
    gravity: Optional[float] = typer.Option(None, "--target-og", help="Target original gravity"),
    volume: Optional[float] = typer.Option(None, "--target-vol", help="Target volume in mL"),
    fermentable: str = typer.Option("honey", "--fermentable", help="Fermentable name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    base: str = typer.Option("water", "--base", help="Base fermentable or fruit name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [
            k for k in get_fermentable_choices() + get_fruit_choices() if k.startswith(incomplete)]),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=None, volume=volume, gravity=gravity, ph=None, require_ph=False)
    fermentable_key = fermentable.strip().lower()
    fermentable_obj = get_fermentable_object(fermentable)
    
    base_key = base.strip().lower()
    if base_key in FERMENTABLES:
        result = base_must.volumes(fermentable_obj, base=FERMENTABLES[base_key])
        fruit = False
    elif base_key in FRUITS:
        result = base_must.volumes_with_fruit_juice(fermentable_obj, fruit=FRUITS[base_key])
        fruit = True
    else:
        choices = ", ".join(sorted(get_fermentable_choices() + get_fruit_choices()))
        raise typer.BadParameter(f"Unknown base: {base}, choose from: {choices}")
     
    base_units = "ml" if fruit else "g"
    echo_boxed(
        f'{fermentable_key}: {round(result[0], 2)}g\n'
        f'{base_key}: {round(result[1], 2)}{base_units}'
    )


# ===================================================
#           Adjuncts and Adjustments
# ===================================================

@app.command("pitch")
def adjust_pitching_rate(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=None, require_ph=False)
    result = base_must.pitch_rate()
    echo_boxed(
        f'Yeast: {round(result["yeast_g"], 2)}g\n'
        f'Go-Ferm: {round(result["goferm_g"], 2)}g'
    )


@app.command("so2-ph")
def adjust_so2_ph(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    target_mol_so2: float = typer.Option(0.8, "--target-mol-so2", help="Target molecular SO2 in ppm"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=1.0, ph=ph, require_ph=not recipe)
    result = base_must.so2_from_ph(target_mol_so2=target_mol_so2)
    result_str = '\n'.join(f'{key}: {round(val, 4)}' for key, val in result.items())
    echo_boxed(result_str)


@app.command("so2-target")
def adjust_so2_target(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    target_ppm: float = typer.Option(50.0, "--target-ppm", help="Target SO2 in ppm"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=1.0, ph=None, require_ph=False)
    result = base_must.so2_from_target_ppm(target_ppm=target_ppm)
    result_str = '\n'.join(f'{key}: {round(val, 4)}' for key, val in result.items())
    echo_boxed(result_str)


@app.command("ta")
def adjust_ta(
    volume: Optional[float] = typer.Option(None, "--vol", help="Batch volume in mL"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for must"),
    current_ta: float = typer.Option(..., "--current-ta", help="Current TA in g/L as tartaric equivalent"),
    target_ta: float = typer.Option(..., "--target-ta", help="Target TA in g/L as tartaric equivalent"),
    acid: str = typer.Option("tartaric", "--acid", help="Acid to add",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_acid_choices() if k.startswith(incomplete)]),
) -> None:
    acid_key = acid.strip().lower()
    acid_obj = ACID_ADJUSTMENTS.get(acid_key)
    if acid_obj is None:
        choices = ", ".join(sorted(ACID_ADJUSTMENTS.keys()))
        raise typer.BadParameter(f"unknown acid '{acid}'. Choose one of: {choices}")

    must = _must_from_args(
        label="Must", recipe=recipe, volume=volume, gravity=1.0, ph=None, require_ph=False)
    try:
        result = must.adjust_ta(current_ta=current_ta, target_ta=target_ta, acid=acid_obj)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    echo_boxed(
        f'Mass: {round(result["acid_addition_grams"], 2)}g {acid_key}\n'
        f'Rate: {round(result["acid_addition_g_per_l"], 3)}g/L'
    )


@app.command("tosna")
def adjust_tosna3(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    yeast: str = typer.Option(..., "--yeast", help="Yeast strain name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in YEAST_STRAINS.keys() if k.startswith(incomplete)]),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=None, require_ph=False)
    yeast_obj = get_yeast_obj(yeast)
    result = base_must.tosna_3(yeast=yeast_obj)
    result_str = '\n'.join(f'{key}: {round(val, 4)}' for key, val in result.items())
    echo_boxed(result_str)
    

# ===================================================
#                 Wine/Mead Blending
# ===================================================

@app.command("blend-to-abv")
def blend_to_abv_cli(
    abv_a: float = typer.Option(..., "--abv1", help="ABV of must/wine A (percent)"),
    abv_b: float = typer.Option(..., "--abv2", help="ABV of must/wine B (percent)"),
    target_abv: float = typer.Option(..., "--target-abv", help="Target blend ABV (percent)"),
    total_volume: float = typer.Option(..., "--target-vol", help="Total blend volume (mL)"),
) -> None:
    try:
        p_a = blend_to_abv(abv_a, abv_b, target_abv)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    p_b = 1 - p_a
    v_a = p_a * total_volume
    v_b = p_b * total_volume

    echo_boxed(
        f'Batch 1: {round(p_a * 100, 2)}%, {round(v_a, 2)}mL\n'
        f'Batch 2: {round(p_b * 100, 2)}%, {round(v_b, 2)}mL'
    )

@app.command("blend-to-gravity")
def blend_to_gravity_cli(
    fg_a: float = typer.Option(..., "--fg1", help="Final gravity of must A"),
    fg_b: float = typer.Option(..., "--fg2", help="Final gravity of must B"),
    target_fg: float = typer.Option(..., "--target-fg", help="Target blend final gravity"),
    total_volume: float = typer.Option(..., "--target-vol", help="Total blend volume (mL)"),
) -> None:
    try:
        p_a = blend_to_gravity(fg_a, fg_b, target_fg)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    p_b = 1 - p_a
    v_a = p_a * total_volume
    v_b = p_b * total_volume
    
    echo_boxed(
        f'Batch 1: {round(p_a * 100, 2)}%, {round(v_a, 2)}mL\n'
        f'Batch 2: {round(p_b * 100, 2)}%, {round(v_b, 2)}mL'
    )

@app.command("blend-nearest")
def blend_nearest_cli(
    abvs: str = typer.Option(..., "--abvs", help="Comma-separated ABVs of musts"),
    fgs: str = typer.Option(..., "--fgs", help="Comma-separated FGs of musts"),
    target_abv: float = typer.Option(..., "--target-abv", help="Target blend ABV (percent)"),
    target_fg: float = typer.Option(..., "--target-fg", help="Target blend FG"),
    total_volume: float = typer.Option(..., "--target-vol", help="Total blend volume (mL)"),
    w_abv: float = typer.Option(1.0, "--w-abv", help="Weight for ABV in optimization (default 1.0)"),
    w_fg: float = typer.Option(1.0, "--w-fg", help="Weight for FG in optimization (default 1.0)"),
    extra_limit: float = typer.Option(0.0, "--extra-limit", help="Limit for adding water, 40 abv ethanol and honey as extras to achieve targets"),
) -> None:
    try:
        abv_list = [float(x.strip()) for x in abvs.split(",") if x.strip()]
        fg_list = [float(x.strip()) for x in fgs.split(",") if x.strip()]
        limits = [(0, 1)] * len(abv_list)
        if extra_limit > 0:
            abv_list.extend([0, 40, 0])
            fg_list.extend([1.0, 0.95, 1.415])
            limits.extend([(0, extra_limit)] * 3)
        result = blend_nearest(
            abvs=abv_list, fgs=fg_list,
            target_abv=target_abv, target_fg=target_fg, target_vol=total_volume,
            w_abv=w_abv, w_fg=w_fg, limits=limits
        )
    except Exception as exc:
        raise typer.BadParameter(str(exc)) from exc
    
    volumes = ', '.join([f"{round(v, 1)}mL" for v in result['volumes']])
    proportions = ', '.join([f"{round(100 * p, 2)}%" for p in result['proportions']])
    lines = [
        f"Volumes: {volumes}",
        f"Proportions: {proportions}",
        f"Blend ABV: {round(result['blend_abv'], 2)}%",
        f"Blend FG: {round(result['blend_fg'], 4)}"
    ]
    if extra_limit > 0:
        lines.append(f'Last three components are extras (water, 40% ethanol, honey).')
    echo_boxed("\n".join(lines))
    

# ===================================================
#           Fortification and Backsweetening
# ===================================================

@app.command("backsweeten")
def backsweeten(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    final_sg: float = typer.Option(..., "--fg", help="Final gravity before backsweetening"),
    target_sg: float = typer.Option(..., "--target-fg", help="Target gravity after backsweetening"),
    fermentable: str = typer.Option(None, "--fermentable", help="Fermentable name for backsweetening",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Fruit name for backsweetening",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=1.0, ph=7, require_ph=False)
    if fermentable is None:
        if fruit is None:
            raise typer.BadParameter("Either --fermentable or --fruit must be provided")
        fruit_obj = get_fruit_object(fruit)
        result = base_must.backsweeten_with_fruit_juice(
            final_sg=final_sg, target_sg=target_sg, fruit=fruit_obj)
    else:
        fermentable_obj = get_fermentable_object(fermentable)
        result = base_must.backsweeten(
            final_sg=final_sg, target_sg=target_sg, sweetener=fermentable_obj)
        
    if fruit:
        result = f'{round(result, 2)}ml'
    else:
        result = f'{round(result, 2)}g'
    echo_boxed(result)


@app.command("fortify")
def calc_fortify_volume(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    current_abv: Optional[float] = typer.Option(..., "--current-abv", help="Current ABV in percent"),
    target_abv: Optional[float] = typer.Option(..., "--target-abv", help="Target ABV in percent"),
    spirit_abv: float = typer.Option(40.0, "--spirit-abv", help="Fortifying spirit ABV in percent"),
) -> None:
    try:
        base_must = _must_from_args(
            label="Base must", recipe=recipe, volume=volume, gravity=1.0, ph=None, 
            require_ph=False)
        result = base_must.fortify_volume_simple(
            target_abv=target_abv, current_abv=current_abv, spirit_abv=spirit_abv)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    
    spirit_vol = round(result["spirit_volume"], 2)
    aux_value = round(result["proportion"], 2)
    echo_boxed(
        f'Spirit volume: {spirit_vol}ml\n'
        f'Proportion: {aux_value}'
    )


@app.command("fortify-fg")
def calc_fortify_fg(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    target_abv: Optional[float] = typer.Option(..., "--target-abv", help="Target ABV in percent"),
    target_gravity: float = typer.Option(..., "--target-fg", help="Target final gravity after fortification"),
    spirit_abv: float = typer.Option(40.0, "--spirit-abv", help="Fortifying spirit ABV in percent"),
    method: AbvMethod = typer.Option(AbvMethod.duncan, "--method", help="ABV calculation method"),
) -> None:
    try:
        base_must = _must_from_args(
            label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=None, 
            require_ph=False)
        result = base_must.fortify_volume(
            target_abv=target_abv, target_fg=target_gravity, spirit_abv=spirit_abv, 
            method=method.value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    
    spirit_vol = round(result["spirit_volume"], 2)
    aux_value = round(result["fortify_gravity"], 4)
    echo_boxed(
        f'Spirit volume: {spirit_vol}ml\n'
        f'Fortify gravity: {aux_value}'
    )


@app.command("fortify-abv")
def calc_fortify_abv(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must specific gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fg: float = typer.Option(..., "--fg", help="Final gravity after fermentation"),
    spirit_vol: float = typer.Option(..., "--spirit-vol", help="Volume of fortifying spirit in mL"),
    spirit_abv: float = typer.Option(40.0, "--spirit-abv", help="Fortifying spirit ABV in percent"),
    method: AbvMethod = typer.Option(AbvMethod.duncan, "--method", help="ABV calculation method"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=None, require_ph=False)
    result = base_must.fortify_abv(
        fg=fg, spirit_vol_ml=spirit_vol, spirit_abv=spirit_abv, method=method.value)
    echo_boxed(f'{round(result, 2)}%')


@app.command("prime")
def calc_priming_sugar(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for must"),
    target_co2_vol: float = typer.Option(..., "--co2", help="Target CO2 volumes"),
    temp: float = typer.Option(..., "--temp", help="Fermentation temperature in C"),
    fermentable: str = typer.Option(..., "--fermentable", help="Fermentable for priming",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in FERMENTABLES.keys() if k.startswith(incomplete)]),
) -> None:
    must = _must_from_args(
        label="Must", recipe=recipe, volume=volume, gravity=1.0, ph=None, require_ph=False)
    fermentable_obj = get_fermentable_object(fermentable)
    result = must.priming_sugar(
        fermentable=fermentable_obj, target_volumes=target_co2_vol, temp=temp)
    echo_boxed(f'{round(result, 2)}g')


# ===================================================
#                  New Entries
# ===================================================

@app.command("new-fermentable")
def data_add_fermentable(
    name: str = typer.Option(..., "--name", help="Fermentable name"),
    ppg: int = typer.Option(..., "--ppg", help="Points per pound per gallon"),
    density: float = typer.Option(..., "--density", help="Density in g/mL"),
    ph: float = typer.Option(..., "--ph", help="pH"),
) -> None:
    try:
        result = add_fermentable(name=name, ppg=ppg, density=density, ph=ph)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("new-fruit")
def data_add_fruit_profile(
    name: str = typer.Option(..., "--name", help="Fruit name"),
    brix: float = typer.Option(..., "--brix", help="Brix"),
    moisture: float = typer.Option(..., "--moisture", help="Moisture"),
    ph: float = typer.Option(..., "--ph", help="pH"),
) -> None:
    try:
        result = add_fruit(name=name, brix=brix, moisture_content=moisture, ph=ph)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    

@app.command("new-yeast")
def data_add_yeast_strain(
    name: str = typer.Option(..., "--name", help="Yeast strain name"),
    limit: float = typer.Option(..., "--abv-limit", help="Yeast alcohol tolerance %"),
    nitrogen: str = typer.Option(..., "--nitrogen", help="Nitrogen requirement"),
) -> None:
    try:
        result = add_yeast_strain(name=name, abv_limit=limit, nitrogen_requirement=nitrogen)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    

init_tui(app)


if __name__ == "__main__":
    app()

