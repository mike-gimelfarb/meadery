from enum import Enum
import io
import os
import shlex
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Optional, List 

import click
import typer
from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets._rich_log import RichLog
from trogon.trogon import Trogon, CommandBuilder
from trogon.typer import init_tui 

from meadery.core import (
    ACID_ADJUSTMENTS, BASE_ADJUSTMENTS, FERMENTABLES, FRUITS, YEAST_STRAINS,
    Hydrometer, Must, Refractometer,
    add_fermentable, add_fruit, add_yeast_strain,
    brix_to_sg, original_gravity, sg_to_brix, parse_recipe, solve_recipe,
    blend_to_gravity, blend_to_abv, blend_to_ph, blend_nearest, spirit_abv_to_sg,
    PH_BUFFERING_WARNING, GRAVITY_WARNING
)


# ===================================================
#                  Application Base
# ===================================================

app = typer.Typer(help="Meadery tools command-line app")


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


def get_base_choices() -> List[str]:
    return list(BASE_ADJUSTMENTS.keys())


def _validate_must(volume: float, gravity: float, ph: Optional[float]=None,
                   pKa: Optional[float]=None, c_buf: Optional[float]=None) -> None:
    if volume < 0:
        raise typer.BadParameter("volume must be >= 0")
    if gravity <= 0:
        raise typer.BadParameter("gravity must be > 0")
    if ph is not None and (ph < 0 or ph > 14):
        raise typer.BadParameter("pH must be between 0 and 14")
    if pKa is not None and (pKa < 0 or pKa > 14):
        raise typer.BadParameter("pKa must be between 0 and 14")
    if c_buf is not None and c_buf < 0:
        raise typer.BadParameter("Buffering capacity must be non-negative")


def _recipe_path(recipe: str) -> str:
    recipe_path = Path(recipe)
    if not recipe_path.is_absolute():
        recipe_path = Path(os.getcwd()) / recipe_path
    return str(recipe_path)


def _must_from_args(*, label: str, recipe: Optional[str], volume: Optional[float],
                    gravity: Optional[float], ph: Optional[float], 
                    pKa: Optional[float], c_buf: Optional[float], require_ph: bool=True) -> Must:
    """Build a Must from either a recipe path or explicit volume/gravity/pH arguments."""
    manual_values = [volume, gravity, ph, pKa, c_buf] if require_ph else [volume, gravity]
    has_manual = any(value is not None for value in manual_values)

    # recipe takes priority
    if recipe is not None:
        try:
            return parse_recipe(_recipe_path(recipe))
        except Exception as exc:
            raise typer.BadParameter(str(exc)) from exc

    # check manual inputs
    if not has_manual:
        req_args = "--vol, --sg, --ph, --pka, --cbuf" if require_ph else "--vol and --sg"
        raise typer.BadParameter(f"{label} requires either --recipe or manual inputs ({req_args}).")
    if any(value is None for value in manual_values):
        req_args = "--vol, --sg, --ph, --pka, --cbuf" if require_ph else "--vol and --sg"
        raise typer.BadParameter(f"{label} manual mode requires {req_args} together.")

    _validate_must(volume, gravity, ph, pKa, c_buf)
    return Must(volume=volume, gravity=gravity, ph=ph, pka=pKa, c_buf=c_buf)


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


def get_acid_object(acid: str) -> object:
    acid_key = acid.strip().lower()
    acid_obj = ACID_ADJUSTMENTS.get(acid_key)
    if acid_obj is None:
        choices = ", ".join(sorted(ACID_ADJUSTMENTS.keys()))
        raise typer.BadParameter(f"Unknown acid: {acid_key}, choose from: {choices}")
    return acid_obj


def get_base_object(base: str) -> object:
    base_key = base.strip().lower()
    base_obj = BASE_ADJUSTMENTS.get(base_key)
    if base_obj is None:
        choices = ", ".join(sorted(BASE_ADJUSTMENTS.keys()))
        raise typer.BadParameter(f"Unknown base: {base_key}, choose from: {choices}")
    return base_obj


# ===================================================
#              Conversion and Calibration
# ===================================================

@app.command("brix-to-sg", help="Convert Brix to specific gravity")
def convert_brix_to_sg(
    brix: float = typer.Option(..., "--brix", help="Brix value"),
) -> None:
    result = brix_to_sg(brix)
    echo_boxed(f'{round(result, 4)}')


@app.command("sg-to-brix", help="Convert specific gravity to Brix")
def convert_sg_to_brix(
    gravity: float = typer.Option(..., "--sg", help="Specific gravity"),
) -> None:
    result = sg_to_brix(gravity)
    echo_boxed(f'{round(result, 2)}')


@app.command("spirit-gravity", help="Convert spirit ABV to specific gravity")
def convert_spirit_abv_to_sg(
    abv: float = typer.Option(..., "--abv", help="Spirit ABV in percent"),
) -> None:
    result = spirit_abv_to_sg(abv)
    echo_boxed(f'{round(result, 4)}')


@app.command("hydrometer", help="Correct hydrometer reading based on temperature")
def correct_hydrometer(
    gravity: float = typer.Option(..., "--sg", help="Measured specific gravity"),
    temperature: float = typer.Option(..., "--temp", help="Measured temperature in C"),
    calibration_temp: float = typer.Option(..., "--calib-temp", help="Hydrometer calibration temperature in C"),
) -> None:
    corrected = Hydrometer(calibration_temperature=calibration_temp).corrected_gravity(
        gravity=gravity, temperature=temperature)
    echo_boxed(f'{round(corrected, 4)}')


@app.command("refractometer", help="Correct refractometer reading based on original gravity")
def correct_refractometer(
    gravity: float = typer.Option(..., "--og", help="Original gravity"),
    brix: float = typer.Option(..., "--brix", help="Current measured Brix"),
) -> None:
    corrected = Refractometer().corrected_gravity(current_brix=brix, original_gravity=gravity)
    echo_boxed(f'{round(corrected, 4)}')


# ===================================================
#           Planning and Calculations
# ===================================================

@app.command("attenuation", help="Calculate apparent attenuation from gravity")
def calc_attenuation(
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fg: float = typer.Option(..., "--fg", help="Final gravity"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=3785.41, gravity=gravity, 
        ph=None, pKa=None, c_buf=None, require_ph=False)
    result = base_must.attenuation(fg=fg)
    echo_boxed(f'{round(result, 2)}%\n\n{GRAVITY_WARNING}')


@app.command("load-recipe", help="Load a recipe from a file")
def must_load_recipe(
    recipe: str = typer.Argument(..., help="Path to recipe file"),
) -> None:
    recipe_path = _recipe_path(recipe)
    try:
        must = parse_recipe(recipe_path)
    except Exception as exc:
        raise typer.BadParameter(str(exc)) from exc
    echo_boxed(f"{str(must)}\n\n{PH_BUFFERING_WARNING}\n{GRAVITY_WARNING}")


@app.command("solve-recipe", help="Solve a recipe with variables to match target OG, volume, and/or pH")
def must_solve_recipe(
    recipe: str = typer.Argument(..., help="Path to recipe file"),
    target_og: float | None = typer.Option(None, "--target-og", help="Target original gravity"),
    target_vol: float | None = typer.Option(None, "--target-vol", help="Target volume in milliliters"),
    target_ph: float | None = typer.Option(None, "--target-ph", help="Target pH"),
) -> None:
    recipe_path = _recipe_path(recipe)
    try:
        result = solve_recipe(
            recipe_path, target_og=target_og, target_vol=target_vol, target_ph=target_ph)
    except Exception as exc:
        raise typer.BadParameter(str(exc)) from exc

    variable_lines = "\n".join(
        f"{name} = {value:.6f}" for name, value in result['variables'].items()
    ) or "(no variables)"
    echo_boxed(
        f"Solved variables:\n{variable_lines}\n\n"
        f"Resulting must:\n{result['must']}\n\n{PH_BUFFERING_WARNING}\n{GRAVITY_WARNING}"
    )


@app.command("original-gravity", help="Calculate original gravity from target ABV and final gravity")
def calc_original_gravity(
    target_abv: float = typer.Option(..., "--target-abv", help="Target ABV in percent"),
    fg: float = typer.Option(..., "--target-fg", help="Target final gravity"),
    method: AbvMethod = typer.Option(AbvMethod.duncan.value, "--method", help="ABV calculation method"),
    tol: float = typer.Option(1e-6, "--tol", help="Root finding tolerance"),
    max_og: float = typer.Option(1.3, "--max-og", help="Maximum original gravity bound"),
) -> None:
    result = original_gravity(
        target_abv=target_abv, fg=fg, method=method.value, tol=tol, max_og=max_og)
    echo_boxed(f'{round(result, 4)}')


@app.command("abv", help="Calculate ABV from original and final gravity")
def calc_abv(
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fg: float = typer.Option(..., "--fg", help="Final gravity"),
    method: AbvMethod = typer.Option(AbvMethod.duncan.value, "--method", help="ABV calculation method"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=3785.41, gravity=gravity, 
        ph=None, pKa=None, c_buf=None, require_ph=False)
    result = base_must.abv(fg=fg, method=method.value)
    echo_boxed(f'{round(result, 2)}%\n\n{GRAVITY_WARNING}')


@app.command("abv-potential", help="Calculate potential ABV from original gravity")
def calc_potential_abv(
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    method: PotentialAbvMethod = typer.Option(PotentialAbvMethod.cooke.value, "--method", help="Potential ABV calculation method"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=3785.41, gravity=gravity, 
        ph=None, pKa=None, c_buf=None, require_ph=False)
    result = base_must.abv_potential(method=method.value)
    echo_boxed(f'{round(result, 2)}%\n\n{GRAVITY_WARNING}')


@app.command("residual-co2", help="Calculate residual CO2 based on temperature")
def calc_residual_co2(
    temp: float = typer.Option(..., "--temp", help="Temperature in C"),
) -> None:
    result = Must.residual_co2(temp)
    echo_boxed(f'{round(result, 2)}volumes, {round(result * 1.96, 3)}g/L')


@app.command("stalled-gravity", help="Calculate stalled gravity based on yeast and must")
def calc_stalled_gravity(
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    yeast: str = typer.Option(..., "--yeast", help="Yeast strain name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_yeast_choices() if k.startswith(incomplete)]),
    method: AbvMethod = typer.Option(AbvMethod.duncan.value, "--method", help="ABV calculation method"),
    tol: float = typer.Option(1e-6, "--tol", help="Root finding tolerance"),
    min_fg: float = typer.Option(0.9, "--min-fg", help="Minimum FG for root finding"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=3785.41, gravity=gravity, 
        ph=None, pKa=None, c_buf=None, require_ph=False)
    yeast_obj = get_yeast_obj(yeast)
    result = base_must.stalled_final_gravity(
        yeast=yeast_obj, method=method.value, tol=tol, min_fg=min_fg)
    echo_boxed(f'{round(result, 4)}\n\n{GRAVITY_WARNING}')


# ===================================================
#           Must Addition and Combination
# ===================================================

@app.command("add", help="Add a fermentable to the must")
def must_add(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    pKa: Optional[float] = typer.Option(3.40, "--pka", help="Must pKa"),
    c_buf: Optional[float] = typer.Option(40.0, "--cbuf", help="Must buffering capacity in mmol/L"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fermentable: str = typer.Option(..., "--fermentable", help="Fermentable name",
        case_sensitive=False, show_choices=True, prompt=False, 
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    mass: float = typer.Option(..., "--mass", help="Fermentable mass in grams"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=ph, pKa=pKa, c_buf=c_buf)
    fermentable_obj = get_fermentable_object(fermentable)
    result = base_must.add(fermentable_obj, mass=mass)
    echo_boxed(f"{str(result)}\n\n{PH_BUFFERING_WARNING}\n{GRAVITY_WARNING}")


@app.command("add-acid", help="Add an acid to the must")
def must_add_acid(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    pKa: Optional[float] = typer.Option(3.40, "--pka", help="Must pKa"),
    c_buf: Optional[float] = typer.Option(40.0, "--cbuf", help="Must buffering capacity in mmol/L"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    acid: str = typer.Option("acid-blend", "--acid", help="Acid name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_acid_choices() if k.startswith(incomplete)]),
    mass: float = typer.Option(..., "--mass", help="Acid mass in grams"),
    tol: float = typer.Option(1e-6, "--tol", help="Tolerance for root finding in pH calculation"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=ph, pKa=pKa, c_buf=c_buf)
    acid_obj = get_acid_object(acid)
    result = base_must.add_acid(acid_grams=mass, acid=acid_obj, tol=tol)
    echo_boxed(f"{str(result)}\n\n{PH_BUFFERING_WARNING}\n{GRAVITY_WARNING}")


@app.command("add-base", help="Add a base to the must")
def must_add_base(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    pKa: Optional[float] = typer.Option(3.40, "--pka", help="Must pKa"),
    c_buf: Optional[float] = typer.Option(40.0, "--cbuf", help="Must buffering capacity in mmol/L"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    base: str = typer.Option("potassium-bicarbonate", "--base", help="Base name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_base_choices() if k.startswith(incomplete)]),
    mass: float = typer.Option(..., "--mass", help="Base mass in grams"),
    tol: float = typer.Option(1e-6, "--tol", help="Tolerance for root finding in pH calculation"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=ph, pKa=pKa, c_buf=c_buf)
    base_obj = get_base_object(base)
    result = base_must.add_base(base_grams=mass, base=base_obj, tol=tol)
    echo_boxed(f"{str(result)}\n\n{PH_BUFFERING_WARNING}\n{GRAVITY_WARNING}")


@app.command("add-fruit", help="Add a fruit to the must")
def must_add_fruit(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    pKa: Optional[float] = typer.Option(3.40, "--pka", help="Must pKa"),
    c_buf: Optional[float] = typer.Option(40.0, "--cbuf", help="Must buffering capacity in mmol/L"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Preset fruit name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
    mass: float = typer.Option(..., "--mass", help="Fruit mass in grams"),
    extract_yield: float = typer.Option(1.0, "--extract-yield", help="Extracted juice yield from 0 to 1"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=ph, pKa=pKa, c_buf=c_buf)
    if fruit is None:
        raise typer.BadParameter("--fruit is required")
    selected_fruit = get_fruit_object(fruit)
    try:
        result = base_must.add_fruit(selected_fruit, mass=mass, extract_yield=extract_yield)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    echo_boxed(f"{str(result)}\n\n{PH_BUFFERING_WARNING}\n{GRAVITY_WARNING}")


@app.command("add-fruit-juice", help="Add fruit juice to the must")
def must_add_fruit_juice(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    pKa: Optional[float] = typer.Option(3.40, "--pka", help="Must pKa"),
    c_buf: Optional[float] = typer.Option(40.0, "--cbuf", help="Must buffering capacity in mmol/L"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Preset fruit name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
    juice_volume: float = typer.Option(..., "--juice-vol", help="Fruit juice volume in mL"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=ph, pKa=pKa, c_buf=c_buf)
    if fruit is None:
        raise typer.BadParameter("--fruit is required")
    selected_fruit = get_fruit_object(fruit)    
    try:
        result = base_must.add_fruit_juice(selected_fruit, volume=juice_volume)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    echo_boxed(f"{str(result)}\n\n{PH_BUFFERING_WARNING}\n{GRAVITY_WARNING}")


@app.command("add-honey", help="Add honey to the must")
def must_add_honey(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    pKa: Optional[float] = typer.Option(3.40, "--pka", help="Must pKa"),
    c_buf: Optional[float] = typer.Option(40.0, "--cbuf", help="Must buffering capacity in mmol/L"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    mass: float = typer.Option(..., "--mass", help="Honey mass in grams"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=ph, pKa=pKa, c_buf=c_buf)
    result = base_must.add_honey(mass=mass)
    echo_boxed(f"{str(result)}\n\n{PH_BUFFERING_WARNING}\n{GRAVITY_WARNING}")


@app.command("add-sugar", help="Add sugar to the must")
def must_add_sugar(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    pKa: Optional[float] = typer.Option(3.40, "--pka", help="Must pKa"),
    c_buf: Optional[float] = typer.Option(40.0, "--cbuf", help="Must buffering capacity in mmol/L"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    mass: float = typer.Option(..., "--mass", help="Sugar mass in grams"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=ph, pKa=pKa, c_buf=c_buf)
    result = base_must.add_sugar(mass=mass)
    echo_boxed(f"{str(result)}\n\n{PH_BUFFERING_WARNING}\n{GRAVITY_WARNING}")


@app.command("add-water", help="Add spring water to the must")
def must_add_water(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    pKa: Optional[float] = typer.Option(3.40, "--pka", help="Must pKa"),
    c_buf: Optional[float] = typer.Option(40.0, "--cbuf", help="Must buffering capacity in mmol/L"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    mass: float = typer.Option(..., "--mass", help="Water mass in grams"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=ph, pKa=pKa, c_buf=c_buf)
    result = base_must.add_spring_water(mass=mass)
    echo_boxed(f"{str(result)}\n\n{PH_BUFFERING_WARNING}\n{GRAVITY_WARNING}")


@app.command("adjust-gravity", help="Adjust the gravity of the must")
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
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=None, pKa=None, c_buf=None, require_ph=False)
    if fermentable is None:
        if fruit is None:
            raise typer.BadParameter("Either --fermentable or --fruit must be provided")
        fruit_obj = get_fruit_object(fruit)
        result = base_must.adjust_gravity_with_fruit_juice(target_sg=target_sg, fruit=fruit_obj)
    else:
        fermentable_obj = get_fermentable_object(fermentable)
        result = base_must.adjust_gravity(target_sg=target_sg, fermentable=fermentable_obj)
    if fruit:
        result = f'{round(result, 2)}ml\n\n{GRAVITY_WARNING}'
    else:
        result = f'{round(result, 2)}g\n\n{GRAVITY_WARNING}'
    echo_boxed(result)


@app.command("combine", help="Combine two musts")
def must_combine(
    volume_a: Optional[float] = typer.Option(None, "--vol1", help="Must A volume in mL"),
    gravity_a: Optional[float] = typer.Option(None, "--og1", help="Must A original gravity"),
    ph_a: Optional[float] = typer.Option(None, "--ph1", help="Must A pH"),
    pKa_a: Optional[float] = typer.Option(3.40, "--pka1", help="Must A pKa"),
    c_buf_a: Optional[float] = typer.Option(40.0, "--cbuf1", help="Must A buffering capacity in mmol/L"),
    recipe1: Optional[str] = typer.Option(None, "--recipe1", help="Path to recipe for must A"),
    volume_b: Optional[float] = typer.Option(None, "--vol2", help="Must B volume in mL"),
    gravity_b: Optional[float] = typer.Option(None, "--og2", help="Must B original gravity"),
    ph_b: Optional[float] = typer.Option(None, "--ph2", help="Must B pH"),
    pKa_b: Optional[float] = typer.Option(3.40, "--pka2", help="Must B pKa"),
    c_buf_b: Optional[float] = typer.Option(40.0, "--cbuf2", help="Must B buffering capacity in mmol/L"),
    recipe2: Optional[str] = typer.Option(None, "--recipe2", help="Path to recipe for must B"),
) -> None:
    must_a = _must_from_args(
        label="Must A", recipe=recipe1, volume=volume_a, gravity=gravity_a, 
        ph=ph_a, pKa=pKa_a, c_buf=c_buf_a)
    must_b = _must_from_args(
        label="Must B", recipe=recipe2, volume=volume_b, gravity=gravity_b, 
        ph=ph_b, pKa=pKa_b, c_buf=c_buf_b)

    result = must_a.combine(must_b)
    echo_boxed(f"{str(result)}\n\n{PH_BUFFERING_WARNING}\n{GRAVITY_WARNING}")


@app.command("volumes", help="Calculate volumes of fermentable and base to achieve a target gravity")
def calc_volumes(
    gravity: Optional[float] = typer.Option(None, "--target-og", help="Target original gravity"),
    volume: Optional[float] = typer.Option(None, "--target-vol", help="Target volume in mL"),
    fermentable: str = typer.Option("honey", "--fermentable", help="Fermentable name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    base: str = typer.Option("spring-water", "--base", help="Base fermentable or fruit name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [
            k for k in get_fermentable_choices() + get_fruit_choices() if k.startswith(incomplete)]),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=None, volume=volume, gravity=gravity, 
        ph=None, pKa=None, c_buf=None, require_ph=False)
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
        f'{base_key}: {round(result[1], 2)}{base_units}\n\n{GRAVITY_WARNING}'
    )


# ===================================================
#           Adjuncts and Adjustments
# ===================================================

@app.command("acidify", help="Calculate acid addition to reduce pH")
def acidify(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must current pH"),
    pka: Optional[float] = typer.Option(3.40, "--pka", help="Must pKa"),
    c_buf: Optional[float] = typer.Option(40.0, "--cbuf", help="Must buffering capacity in mmol/L"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for must"),
    target_ph: float = typer.Option(..., "--target-ph", help="Target pH of the must"),
    acid: str = typer.Option("acid-blend", "--acid", help="Acid to add",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_acid_choices() if k.startswith(incomplete)]),
) -> None:
    acid_key = acid.strip().lower()
    adj_obj = get_acid_object(acid_key)
    must = _must_from_args(
        label="Must", recipe=recipe, volume=volume, gravity=1.0, 
        ph=ph, pKa=pka, c_buf=c_buf, require_ph=True)
    try:
        result = must.acidify(target_ph=target_ph, acid=adj_obj)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    print_str = (
        f'Must pH: {round(must.ph, 2)}\n'
        f'Amount: {round(result, 2)}g {acid_key}\n\n{PH_BUFFERING_WARNING}'
    )
    if result / (must.volume / 3785) > 3.8:
        print_str += (
            "\nWarning: acid addition exceeds the recommended maximum "
            "of 3.8 g/gallon, which may lead to off-flavors or other issues."
        )
    echo_boxed(print_str)


@app.command("acidify-ta", help="Adjust titratable acidity (TA) of the must")
def adjust_ta(
    volume: Optional[float] = typer.Option(None, "--vol", help="Batch volume in mL"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for must"),
    current_ta: float = typer.Option(..., "--current-ta", help="Current TA in g/L as tartaric equivalent"),
    target_ta: float = typer.Option(..., "--target-ta", help="Target TA in g/L as tartaric equivalent"),
    acid: str = typer.Option("acid-blend", "--acid", help="Acid to add",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_acid_choices() if k.startswith(incomplete)]),
) -> None:
    acid_key = acid.strip().lower()
    acid_obj = get_acid_object(acid_key)
    must = _must_from_args(
        label="Must", recipe=recipe, volume=volume, gravity=1.0, 
        ph=None, pKa=None, c_buf=None, require_ph=False)
    try:
        result = must.adjust_ta(current_ta=current_ta, target_ta=target_ta, acid=acid_obj)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    echo_boxed(
        f'Mass: {round(result["acid_addition_grams"], 2)}g {acid_key}\n'
        f'Rate: {round(result["acid_addition_g_per_l"], 3)}g/L\n\n{PH_BUFFERING_WARNING}'
    )


@app.command("adjust-ph-strip", help="Adjustment of test strip pH for dilution")
def adjust_ph_strip(
    ph: Optional[float] = typer.Option(None, "--ph", help="Must current pH"),
    pka: Optional[float] = typer.Option(3.40, "--pka", help="Must pKa"),
    c_buf: Optional[float] = typer.Option(40.0, "--cbuf", help="Must buffering capacity in mmol/L"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for must"),
    ph_strip: float = typer.Option(..., "--ph-strip", help="pH reading from test strip after dilution"),
    parts_water: int = typer.Option(5, "--parts-water", help="Parts water added for dilution"),
    water: str = typer.Option("water", "--fermentable", help="Medium used for dilution",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
) -> None:
    must = _must_from_args(
        label="Must", recipe=recipe, volume=1.0, gravity=1.0, 
        ph=ph, pKa=pka, c_buf=c_buf, require_ph=True)
    water_key = water.strip().lower()
    water_obj = get_fermentable_object(water_key)
    try:
        result = must.ph_dilution_correction(
            parts_water=parts_water, strip_ph=ph_strip, fermentable=water_obj)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    echo_boxed(
        f'{round(result, 2)}\n\n{PH_BUFFERING_WARNING}'
    )

@app.command("deacidify", help="Calculate base addition to raise pH")
def deacidify(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must current pH"),
    pka: Optional[float] = typer.Option(3.40, "--pka", help="Must pKa"),
    c_buf: Optional[float] = typer.Option(40.0, "--cbuf", help="Must buffering capacity in mmol/L"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for must"),
    target_ph: float = typer.Option(..., "--target-ph", help="Target pH of the must"),
    base: str = typer.Option("potassium-bicarbonate", "--base", help="Base to add",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_base_choices() if k.startswith(incomplete)]),
) -> None:
    base_key = base.strip().lower()
    adj_obj = get_base_object(base_key)
    must = _must_from_args(
        label="Must", recipe=recipe, volume=volume, gravity=1.0, 
        ph=ph, pKa=pka, c_buf=c_buf, require_ph=True)
    try:
        result = must.deacidify(target_ph=target_ph, base=adj_obj)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    print_str = (
        f'Must pH: {round(must.ph, 2)}\n'
        f'Amount: {round(result, 2)}g {base_key}\n\n{PH_BUFFERING_WARNING}'
    )
    if result / (must.volume / 3785) > 3.8:
        print_str += (
            "\nWarning: base addition exceeds the recommended "
            "maximum of 3.8 g/gallon, which may lead to off-flavors or other issues."
        )
    echo_boxed(print_str)


@app.command("pitch", help="Calculate yeast and nutrient amounts for pitching")
def adjust_pitching_rate(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=None, pKa=None, c_buf=None, require_ph=False)
    result = base_must.pitch_rate()
    echo_boxed(
        f'Yeast: {round(result["yeast_g"], 2)}g\n'
        f'Go-Ferm: {round(result["goferm_g"], 2)}g\n'
        f'Water: {round(result["water_ml"], 2)}ml\n\n{GRAVITY_WARNING}'
    )


@app.command("sulfite-ph", help="Adjust SO2 based on pH")
def adjust_so2_ph(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    target_mol_so2: float = typer.Option(0.8, "--target-mol-so2", help="Target molecular SO2 in ppm"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=1.0, 
        ph=ph, pKa=3.40, c_buf=40.0, require_ph=not recipe)
    result = base_must.so2_from_ph(target_mol_so2=target_mol_so2)
    lines = [f'{key}: {round(val, 4)}' for key, val in result.items()]
    lines.append('')
    lines.append(PH_BUFFERING_WARNING)
    echo_boxed('\n'.join(lines))


@app.command("sulfite-ppm", help="Adjust SO2 based on target ppm")
def adjust_so2_target(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    target_ppm: float = typer.Option(50.0, "--target-ppm", help="Target SO2 in ppm"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=1.0, 
        ph=None, pKa=None, c_buf=None, require_ph=False)
    result = base_must.so2_from_target_ppm(target_ppm=target_ppm)
    result_str = '\n'.join(f'{key}: {round(val, 4)}' for key, val in result.items())
    echo_boxed(result_str + '\n\n' + PH_BUFFERING_WARNING)


@app.command("tosna", help="Calculate nutrient requirements based on yeast and must")
def adjust_tosna3(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    yeast: str = typer.Option(..., "--yeast", help="Yeast strain name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in YEAST_STRAINS.keys() if k.startswith(incomplete)]),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=None, pKa=None, c_buf=None, require_ph=False)
    yeast_obj = get_yeast_obj(yeast)
    result = base_must.tosna_3(yeast=yeast_obj)
    result_str = '\n'.join(f'{key}: {round(val, 4)}' for key, val in result.items())
    echo_boxed(result_str + '\n\n' + GRAVITY_WARNING)
    

# ===================================================
#                 Wine/Mead Blending
# ===================================================

@app.command("blend-to-abv", help="Calculate blend proportions to achieve a target ABV")
def blend_to_abv_cli(
    abv_a: float = typer.Option(..., "--abv1", help="ABV of must A (percent)"),
    abv_b: float = typer.Option(..., "--abv2", help="ABV of must B (percent)"),
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

@app.command("blend-to-gravity", help="Calculate blend proportions to achieve a target final gravity")
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


@app.command("blend-to-ph", help="Calculate blend proportions to achieve a target pH")
def blend_to_ph_cli(
    ph_a: float = typer.Option(None, "--ph1", help="pH of must A"),
    pka_a: float = typer.Option(3.40, "--pka1", help="pKa of must A"),
    c_buf_a: float = typer.Option(40.0, "--cbuf1", help="Buffering capacity of must A"),
    recipe_a: Optional[str] = typer.Option(None, "--recipe1", help="Path to recipe for must A"),
    ph_b: float = typer.Option(None, "--ph2", help="pH of must B"),
    pka_b: float = typer.Option(3.40, "--pka2", help="pKa of must B"),
    c_buf_b: float = typer.Option(40.0, "--cbuf2", help="Buffering capacity of must B"),
    recipe_b: Optional[str] = typer.Option(None, "--recipe2", help="Path to recipe for must B"),
    target_ph: float = typer.Option(..., "--target-ph", help="Target blend pH"),
    total_volume: float = typer.Option(..., "--target-vol", help="Total blend volume (mL)"),
    tol: float = typer.Option(1e-6, "--tol", help="Tolerance for root finding in pH calculation"),
) -> None:
    try:
        must1 = _must_from_args(
            label="Must A", recipe=recipe_a, volume=3785.41, gravity=1.0, 
            ph=ph_a, pKa=pka_a, c_buf=c_buf_a, require_ph=True)
        must2 = _must_from_args(
            label="Must B", recipe=recipe_b, volume=3785.41, gravity=1.0, 
            ph=ph_b, pKa=pka_b, c_buf=c_buf_b, require_ph=True)
        p_a = blend_to_ph(must1, must2, target_ph, tol=tol)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    p_b = 1 - p_a
    v_a = p_a * total_volume
    v_b = p_b * total_volume
    
    echo_boxed(
        f'Batch 1: {round(p_a * 100, 2)}%, {round(v_a, 2)}mL\n'
        f'Batch 2: {round(p_b * 100, 2)}%, {round(v_b, 2)}mL\n\n{PH_BUFFERING_WARNING}'
    )


@app.command("blend-nearest", help="Calculate blend proportions to achieve target ABV and FG")
def blend_nearest_cli(
    abvs: List[float] = typer.Option(..., "--abvs", help="ABVs of musts; repeat --abvs for each value"),
    fgs: List[float] = typer.Option(..., "--fgs", help="FGs of musts; repeat --fgs for each value"),
    target_abv: float = typer.Option(..., "--target-abv", help="Target blend ABV (percent)"),
    target_fg: float = typer.Option(..., "--target-fg", help="Target blend FG"),
    total_volume: float = typer.Option(..., "--target-vol", help="Total blend volume (mL)"),
    w_abv: float = typer.Option(1.0, "--w-abv", help="Weight for ABV in optimization (default 1.0)"),
    w_fg: float = typer.Option(1.0, "--w-fg", help="Weight for FG in optimization (default 1.0)"),
    extra_limit: float = typer.Option(0.0, "--extra-limit", help="Limit for adding water, 40 abv ethanol and a fermentable as extras to achieve targets"),
    extra_fermentable: str = typer.Option("honey", "--extra-fermentable", help="Fermentable extra component when --extra-limit is set",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    extra_spirit_abv: float = typer.Option(40.0, "--extra-spirit-abv", help="ABV of spirit extra component when --extra-limit is set")
) -> None:
    try:
        abv_list = abvs
        fg_list = fgs
        limits = [(0, 1)] * len(abv_list)
        fermentable_sg = 1.0
        
        if extra_limit > 0:
            fermentable_key = extra_fermentable.strip().lower()
            if fermentable_key in FERMENTABLES:
                fermentable_obj = FERMENTABLES[fermentable_key]
                fermentable_sg = fermentable_obj.specific_gravity()
            else:
                choices = ", ".join(sorted(get_fermentable_choices()))
                raise typer.BadParameter(f"Unknown extra fermentable: {fermentable_key}. Choose from: {choices}")
            abv_list = list(abv_list) + [0.0, extra_spirit_abv, 0.0]
            fg_list = list(fg_list) + [1.0, spirit_abv_to_sg(extra_spirit_abv), fermentable_sg]
            limits.extend([(0, extra_limit)] * 3)
        
        result = blend_nearest(
            abvs=abv_list, fgs=fg_list,
            target_abv=target_abv, target_fg=target_fg, target_vol=total_volume,
            w_abv=w_abv, w_fg=w_fg, limits=limits
        )
    except Exception as exc:
        raise typer.BadParameter(str(exc)) from exc
    
    if extra_limit > 0:
        volumes, extra_volumes = result['volumes'][:-3], result['volumes'][-3:]
        proportions, extra_proportions = result['proportions'][:-3], result['proportions'][-3:]
    else:
        volumes, proportions = result['volumes'], result['proportions']
        extra_volumes = [0, 0, 0]
        extra_proportions = [0, 0, 0]
    volumes = ', '.join([f"{round(v, 1)}mL" for v in volumes])
    proportions = ', '.join([f"{round(100 * p, 2)}%" for p in proportions])
    
    lines = [
        f"Volumes: {volumes}",
        f"Proportions: {proportions}",
        f"Water: {round(extra_volumes[0], 1)}mL ({round(100 * extra_proportions[0], 2)}%)",
        f"Spirit: {round(extra_volumes[1], 1)}mL ({round(100 * extra_proportions[1], 2)}%)",
        f"Fermentable: {round(extra_volumes[2] * fermentable_sg, 1)}g ({round(100 * extra_proportions[2], 2)}%)",
        f"Blend ABV: {round(result['blend_abv'], 2)}%",
        f"Blend FG: {round(result['blend_fg'], 4)}"
    ]
    echo_boxed("\n".join(lines))
    

# ===================================================
#           Fortification and Backsweetening
# ===================================================

@app.command("backsweeten", help="Calculate backsweetening requirements to achieve target gravity")
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
        label="Base must", recipe=recipe, volume=volume, gravity=1.0, 
        ph=7, pKa=3.40, c_buf=40.0, require_ph=False)
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
        result = f'{round(result, 2)}ml\n\n{GRAVITY_WARNING}'
    else:
        result = f'{round(result, 2)}g\n\n{GRAVITY_WARNING}'
    echo_boxed(result)


@app.command("fortify", help="Calculate spirit volume to achieve target ABV")
def calc_fortify_volume(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    current_abv: Optional[float] = typer.Option(..., "--current-abv", help="Current ABV in percent"),
    target_abv: Optional[float] = typer.Option(..., "--target-abv", help="Target ABV in percent"),
    spirit_abv: float = typer.Option(40.0, "--spirit-abv", help="Fortifying spirit ABV in percent"),
) -> None:
    try:
        base_must = _must_from_args(
            label="Base must", recipe=recipe, volume=volume, gravity=1.0, 
            ph=None, pKa=None, c_buf=None, require_ph=False)
        result = base_must.fortify_volume_simple(
            target_abv=target_abv, current_abv=current_abv, spirit_abv=spirit_abv)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    
    echo_boxed(
        f'Spirit volume: {round(result["spirit_volume"], 2)}ml\n'
        f'Proportion: {round(100 * result["proportion"], 2)}%'
    )


@app.command("fortify-fg", help="Calculate spirit volume to achieve target ABV and FG")
def calc_fortify_fg(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    target_abv: Optional[float] = typer.Option(..., "--target-abv", help="Target ABV in percent"),
    target_gravity: float = typer.Option(..., "--target-fg", help="Target final gravity after fortification"),
    spirit_abv: float = typer.Option(40.0, "--spirit-abv", help="Fortifying spirit ABV in percent"),
    method: AbvMethod = typer.Option(AbvMethod.duncan.value, "--method", help="ABV calculation method"),
) -> None:
    try:
        base_must = _must_from_args(
            label="Base must", recipe=recipe, volume=volume, gravity=gravity,
            ph=None, pKa=None, c_buf=None, require_ph=False)
        result = base_must.fortify_volume(
            target_abv=target_abv, target_fg=target_gravity, spirit_abv=spirit_abv, 
            method=method.value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    
    echo_boxed(
        f'Spirit volume: {round(result["spirit_volume"], 2)}ml\n'
        f'Proportion: {round(100 * result["proportion"], 2)}%\n'
        f'Fortify gravity: {round(result["fortify_gravity"], 4)}\n'
        f'Fortify abv: {round(result["fortify_abv"], 2)}%\n\n{GRAVITY_WARNING}'
    )


@app.command("fortify-abv", help="Calculate ABV after fortification")
def calc_fortify_abv(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must specific gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fg: float = typer.Option(..., "--fg", help="Final gravity after fermentation"),
    spirit_vol: float = typer.Option(..., "--spirit-vol", help="Volume of fortifying spirit in mL"),
    spirit_abv: float = typer.Option(40.0, "--spirit-abv", help="Fortifying spirit ABV in percent"),
    method: AbvMethod = typer.Option(AbvMethod.duncan.value, "--method", help="ABV calculation method"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=None, pKa=None, c_buf=None, require_ph=False)
    result = base_must.fortify_abv(
        fg=fg, spirit_vol_ml=spirit_vol, spirit_abv=spirit_abv, method=method.value)
    echo_boxed(f'{round(result, 2)}%\n\n{GRAVITY_WARNING}')


@app.command("prime", help="Calculate priming sugar required to achieve target carbonation")
def calc_priming_sugar(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for must"),
    target_co2_vol: float = typer.Option(..., "--co2", help="Target CO2 volumes"),
    temp: float = typer.Option(..., "--temp", help="Fermentation temperature in C"),
    fermentable: str = typer.Option(..., "--fermentable", help="Fermentable for priming",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in FERMENTABLES.keys() if k.startswith(incomplete)]),
) -> None:
    must = _must_from_args(
        label="Must", recipe=recipe, volume=volume, gravity=1.0, 
        ph=None, pKa=None, c_buf=None, require_ph=False)
    fermentable_obj = get_fermentable_object(fermentable)
    result = must.priming_sugar(
        fermentable=fermentable_obj, target_volumes=target_co2_vol, temp=temp)
    echo_boxed(f'{round(result, 2)}g\n\n{GRAVITY_WARNING}')


# ===================================================
#                  New Entries
# ===================================================

@app.command("new-fermentable", help="Add a new fermentable to the database")
def data_add_fermentable(
    name: str = typer.Option(..., "--name", help="Fermentable name"),
    ppg: int = typer.Option(..., "--ppg", help="Points per pound per gallon"),
    density: float = typer.Option(..., "--density", help="Density in g/mL"),
    ph: float = typer.Option(..., "--ph", help="pH"),
    pka: float = typer.Option(3.40, "--pka", help="pKa"),
    c_buf: float = typer.Option(40.0, "--cbuf", help="Buffering capacity in mmol/L"),
) -> None:
    try:
        result = add_fermentable(
            name=name, ppg=ppg, density=density, ph=ph, pka=pka, c_buf=c_buf)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command("new-fruit", help="Add a new fruit profile to the database")
def data_add_fruit_profile(
    name: str = typer.Option(..., "--name", help="Fruit name"),
    brix: float = typer.Option(..., "--brix", help="Brix"),
    moisture: float = typer.Option(..., "--moisture", help="Moisture"),
    ph: float = typer.Option(..., "--ph", help="pH"),
    pka: float = typer.Option(3.40, "--pka", help="pKa"),
    c_buf: float = typer.Option(40.0, "--cbuf", help="Buffering capacity in mmol/L")
) -> None:
    try:
        result = add_fruit(
            name=name, brix=brix, moisture_content=moisture, ph=ph, pka=pka, c_buf=c_buf)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    

@app.command("new-yeast", help="Add a new yeast strain to the database")
def data_add_yeast_strain(
    name: str = typer.Option(..., "--name", help="Yeast strain name"),
    limit: float = typer.Option(..., "--abv-limit", help="Yeast alcohol tolerance %"),
    nitrogen: str = typer.Option(..., "--nitrogen", help="Nitrogen requirement"),
) -> None:
    try:
        result = add_yeast_strain(name=name, abv_limit=limit, nitrogen_requirement=nitrogen)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    


class CommandBuilderWithHistory(CommandBuilder):
    DEFAULT_CSS = """
    #home-history {
        height: 30%;
        max-height: 30%;
        min-height: 8;
    }
    """

    def compose(self) -> ComposeResult:
        yield from super().compose()

    async def on_mount(self, event: events.Mount) -> None:
        body = self.query_one("#home-body", Vertical)
        await body.mount(RichLog(id="home-history"))
        self.history = self.query_one("#home-history", RichLog)
        self.history.write("Command history")
        self.history.write("Press Ctrl+R to execute the selected command and preserve output.")

    def action_close_and_run(self) -> None:
        if self.command_data is None:
            return

        args = self.command_data.to_cli_args(include_root_command=not self.is_grouped_cli)
        self.history.write("\n$ " + " ".join(shlex.quote(arg) for arg in args))

        with io.StringIO() as buffer:
            try:
                with redirect_stdout(buffer), redirect_stderr(buffer):
                    self.cli.main(
                        args=args, prog_name=self.click_app_name, standalone_mode=False)
            except SystemExit as exc:
                output = buffer.getvalue().strip()
                if output:
                    self.history.write(output)
                if exc.code not in (None, 0):
                    self.history.write(f"Command exited with code {exc.code}")
            except Exception as exc:
                output = buffer.getvalue().strip()
                if output:
                    self.history.write(output)
                self.history.write(f"Error: {exc}")
            else:
                output = buffer.getvalue().strip()
                if output:
                    self.history.write(output)


class MeaderyTrogon(Trogon):
    def get_default_screen(self) -> CommandBuilder:
        return CommandBuilderWithHistory(self.cli, self.app_name, self.command_name)


def init_tui(app: typer.Typer, name: str | None = None):
    def wrapped_tui():
        MeaderyTrogon(
            typer.main.get_group(app),
            app_name=name,
            click_context=click.get_current_context(),
        ).run()
    app.command("tui", help="Open Textual TUI.")(wrapped_tui)
    return app


# launch gui
init_tui(app)


if __name__ == "__main__":
    app()

