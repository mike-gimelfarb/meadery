from enum import Enum
import json
import os
from pathlib import Path
import typer
from typing import Optional, List

from mead_tools.core import (
    ACID_ADJUSTMENTS, FERMENTABLES, FRUITS, YEAST_STRAINS,
    Hydrometer, Must, Refractometer,
    add_fermentable, add_fruit, add_yeast_strain,
    brix_to_sg, original_gravity, sg_to_plato, parse_recipe,
)


app = typer.Typer(help="Mead tools command-line app")


class OutputFormat(str, Enum):
    text = "text"
    json = "json"


class AbvMethod(str, Enum):
    standard = "standard"
    alternate = "alternate"
    cutaia = "cutaia"


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

    if recipe is not None:
        if has_manual:
            raise typer.BadParameter(f"Do not mix --recipe for {label} with manual inputs.")
        try:
            return parse_recipe(_recipe_path(recipe))
        except Exception as exc:
            raise typer.BadParameter(str(exc)) from exc

    if not has_manual:
        req_args = "--vol, --sg, and --ph" if require_ph else "--vol and --sg"
        raise typer.BadParameter(f"{label} requires either --recipe or manual inputs ({req_args}).")
    if any(value is None for value in manual_values):
        req_args = "--vol, --sg, and --ph" if require_ph else "--vol and --sg"
        raise typer.BadParameter(f"{label} manual mode requires {req_args} together.")

    _validate_must(volume, gravity, ph)
    return Must(volume=volume, gravity=gravity, ph=ph)


def _emit(value, output: OutputFormat) -> None:
    if output == OutputFormat.json:
        typer.echo(json.dumps(value, indent=2, sort_keys=True))
        return
    if isinstance(value, dict):
        for key, val in value.items():
            if isinstance(val, float):
                val = round(val, 4)
            typer.echo(f"{key}: {val}")
        return
    typer.echo(str(value))


# ===================================================
#                  Data Commands
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
    

# ===================================================
#                Conversion Commands
# ===================================================

@app.command("sg-to-plato")
def convert_sg_to_plato(
    gravity: float = typer.Option(..., "--sg", help="Specific gravity"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    result = sg_to_plato(gravity)
    _emit(
        {"sg": gravity, "plato": result} if output == OutputFormat.json else round(result, 2), 
        output
    )


@app.command("brix-to-sg")
def convert_brix_to_sg(
    brix: float = typer.Option(..., "--brix", help="Brix value"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    result = brix_to_sg(brix)
    _emit(
        {"brix": brix, "sg": result} if output == OutputFormat.json else round(result, 4), 
        output
    )


# ===================================================
#                Correction Commands
# ===================================================

@app.command("hydrometer")
def correct_hydrometer(
    gravity: float = typer.Option(..., "--sg", help="Measured specific gravity"),
    temperature: float = typer.Option(..., "--temp", help="Measured temperature in C"),
    calibration_temp: float = typer.Option(..., "--calib-temp", help="Hydrometer calibration temperature in C"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    corrected = Hydrometer(calibration_temperature=calibration_temp).corrected_gravity(
        gravity=gravity, temperature=temperature)
    _emit(
        {
            "measured_gravity": gravity,
            "temperature_c": temperature,
            "calibration_temperature_c": calibration_temp,
            "corrected_gravity": corrected,
        }
        if output == OutputFormat.json else round(corrected, 4),
        output,
    )


@app.command("refractometer")
def correct_refractometer(
    brix: float = typer.Option(..., "--brix", help="Current measured Brix"),
    gravity: float = typer.Option(..., "--og", help="Original gravity"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    corrected = Refractometer().corrected_gravity(current_brix=brix, original_gravity=gravity)
    _emit(
        {
            "current_brix": brix,
            "original_gravity": gravity,
            "corrected_gravity": corrected,
        }
        if output == OutputFormat.json else round(corrected, 4),
        output,
    )


# ===================================================
#                  Must Commands
# ===================================================

@app.command("combine")
def must_combine(
    volume_a: Optional[float] = typer.Option(None, "--vol1", help="Must A volume in mL"),
    gravity_a: Optional[float] = typer.Option(None, "--sg1", help="Must A specific gravity"),
    ph_a: Optional[float] = typer.Option(None, "--ph1", help="Must A pH"),
    recipe1: Optional[str] = typer.Option(None, "--recipe1", help="Path to recipe for must A"),
    volume_b: Optional[float] = typer.Option(None, "--vol2", help="Must B volume in mL"),
    gravity_b: Optional[float] = typer.Option(None, "--sg2", help="Must B specific gravity"),
    ph_b: Optional[float] = typer.Option(None, "--ph2", help="Must B pH"),
    recipe2: Optional[str] = typer.Option(None, "--recipe2", help="Path to recipe for must B"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    must_a = _must_from_args(
        label="Must A", recipe=recipe1, volume=volume_a, gravity=gravity_a, ph=ph_a)
    must_b = _must_from_args(
        label="Must B", recipe=recipe2, volume=volume_b, gravity=gravity_b, ph=ph_b)

    result = must_a.combine(must_b)
    payload = {"volume_ml": result.volume, "gravity": result.gravity, "ph": result.ph}
    _emit(
        payload if output == OutputFormat.json else str(result), 
        output
    )


@app.command("add")
def must_add(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--sg", help="Must specific gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fermentable: str = typer.Option(..., "--fermentable", help="Fermentable name",
        case_sensitive=False, show_choices=True, prompt=True, 
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    mass: float = typer.Option(..., "--mass", help="Fermentable mass in grams"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=ph)
    fermentable_key = fermentable.strip().lower()
    if fermentable_key not in FERMENTABLES:
        choices = ", ".join(sorted(FERMENTABLES.keys()))
        raise typer.BadParameter(f"unknown fermentable '{fermentable}'. Choose one of: {choices}")
    
    result = base_must.add(FERMENTABLES[fermentable_key], mass=mass)
    payload = {
        "fermentable": fermentable_key,
        "mass_g": mass,
        "volume_ml": result.volume,
        "gravity": result.gravity,
        "ph": result.ph,
    }
    _emit(
        payload if output == OutputFormat.json else str(result), 
        output
    )


@app.command("add-water")
def must_add_water(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--sg", help="Must specific gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    mass: float = typer.Option(..., "--mass", help="Water mass in grams"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=ph)
    result = base_must.add_water(mass=mass)
    payload = {"mass_g": mass, "volume_ml": result.volume, "gravity": result.gravity, 
               "ph": result.ph}
    _emit(
        payload if output == OutputFormat.json else str(result), 
        output
    )


@app.command("add-honey")
def must_add_honey(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--sg", help="Must specific gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    mass: float = typer.Option(..., "--mass", help="Honey mass in grams"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=ph)
    result = base_must.add_honey(mass=mass)
    payload = {"mass_g": mass, "volume_ml": result.volume, "gravity": result.gravity, 
               "ph": result.ph}
    _emit(
        payload if output == OutputFormat.json else str(result), 
        output
    )


@app.command("add-sugar")
def must_add_sugar(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--sg", help="Must specific gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    mass: float = typer.Option(..., "--mass", help="Sugar mass in grams"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=ph)
    result = base_must.add_sugar(mass=mass)
    payload = {"mass_g": mass, "volume_ml": result.volume, "gravity": result.gravity, 
               "ph": result.ph}
    _emit(
        payload if output == OutputFormat.json else str(result), 
        output
    )


@app.command("add-fruit")
def must_add_fruit(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--sg", help="Must specific gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Preset fruit name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
    mass: float = typer.Option(..., "--mass", help="Fruit mass in grams"),
    extract_yield: float = typer.Option(1.0, "--extract-yield", help="Extracted juice yield from 0 to 1"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=ph)
    if fruit is None:
        raise typer.BadParameter("--fruit is required")
    fruit_key = fruit.strip().lower()
    selected_fruit = FRUITS.get(fruit_key)
    if selected_fruit is None:
        choices = ", ".join(sorted(FRUITS.keys()))
        raise typer.BadParameter(f"unknown fruit '{fruit}'. Choose one of: {choices}")
    source = fruit_key
    
    try:
        result = base_must.add_fruit(selected_fruit, mass=mass, extract_yield=extract_yield)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    payload = {
        "fruit": source,
        "brix": selected_fruit.brix,
        "moisture_content": selected_fruit.moisture_content,
        "extract_yield": extract_yield,
        "mass_g": mass,
        "volume_ml": result.volume,
        "gravity": result.gravity,
        "ph": result.ph,
    }
    _emit(
        payload if output == OutputFormat.json else str(result),
        output,
    )


@app.command("add-fruit-juice")
def must_add_fruit_juice(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--sg", help="Must specific gravity"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Preset fruit name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
    juice_volume: float = typer.Option(..., "--juice-vol", help="Fruit juice volume in mL"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=ph)
    if fruit is None:
        raise typer.BadParameter("--fruit is required")
    fruit_key = fruit.strip().lower()
    selected_fruit = FRUITS.get(fruit_key)
    if selected_fruit is None:
        choices = ", ".join(sorted(FRUITS.keys()))
        raise typer.BadParameter(f"unknown fruit '{fruit}'. Choose one of: {choices}")
    source = fruit_key

    try:
        result = base_must.add_fruit_juice(selected_fruit, volume=juice_volume)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    payload = {
        "fruit": source,
        "brix": selected_fruit.brix,
        "juice_volume_ml": juice_volume,
        "volume_ml": result.volume,
        "gravity": result.gravity,
        "ph": result.ph,
    }
    _emit(
        payload if output == OutputFormat.json else str(result),
        output,
    )


@app.command("load-recipe")
def must_load_recipe(
    recipe: str = typer.Argument(..., help="Path to recipe file"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    recipe_path = _recipe_path(recipe)
    try:
        must = parse_recipe(recipe_path)
    except Exception as exc:
        raise typer.BadParameter(str(exc)) from exc
    payload = {"volume_ml": must.volume, "gravity": must.gravity, "ph": must.ph}
    _emit(
        payload if output == OutputFormat.json else str(must),
        output,
    )


# ===================================================
#                  Calc Commands
# ===================================================

@app.command("fortify-volume")
def calc_fortify_volume(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    target_abv: Optional[float] = typer.Option(..., "--abv", help="Target ABV in percent"),
    target_gravity: float = typer.Option(..., "--fg", help="Target specific gravity after fortification"),
    spirit_abv: float = typer.Option(40.0, "--spirit-abv", help="Fortifying spirit ABV in percent"),
    method: AbvMethod = typer.Option(AbvMethod.cutaia, "--method", help="ABV calculation method"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=None, 
        require_ph=False)
    try:
        result = base_must.fortify_volume(
            target_abv=target_abv, target_fg=target_gravity, spirit_abv=spirit_abv, 
            method=method.value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    payload = {"target_abv": target_abv, "target_gravity": target_gravity, **result}
    spirit_vol = round(result["spirit_volume"], 2)
    fortify_gravity = round(result["fortify_gravity"], 4)
    _emit(
        payload if output == OutputFormat.json 
        else f'spirit_volume={spirit_vol}ml\nfortify_gravity={fortify_gravity}',
        output
    )


@app.command("fortify-abv")
def calc_fortify_abv(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must specific gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fg: float = typer.Option(..., "--fg", help="Final gravity after fermentation"),
    spirit_vol: float = typer.Option(..., "--spirit-vol", help="Volume of fortifying spirit in mL"),
    spirit_abv: float = typer.Option(40.0, "--spirit-abv", help="Fortifying spirit ABV in percent"),
    method: AbvMethod = typer.Option(AbvMethod.cutaia, "--method", help="ABV calculation method"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=None,
        require_ph=False)
    result = base_must.fortify_abv(
        fg=fg, spirit_vol_ml=spirit_vol, spirit_abv=spirit_abv, method=method.value)
    payload = {"fg": fg, "fortified_abv_percent": result}
    _emit(
        payload if output == OutputFormat.json else f'{round(result, 2)}%',
        output
    )


@app.command("potential-abv")
def calc_potential_abv(
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fg: float = typer.Option(1.0, "--fg", help="Final gravity"),
    method: AbvMethod = typer.Option(AbvMethod.cutaia, "--method", help="ABV calculation method"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=None if gravity is None else 3785.41, 
        gravity=gravity, ph=None, require_ph=False)
    result = base_must.potential_abv(fg=fg, method=method.value)
    payload = {"og": base_must.gravity, "fg": fg, "method": method.value, "abv_percent": result}
    _emit(payload if output == OutputFormat.json else f'{round(result, 2)}%', output)


@app.command("attenuation")
def calc_attenuation(
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fg: float = typer.Option(..., "--fg", help="Final gravity"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=None if gravity is None else 3785.41, 
        gravity=gravity, ph=None, require_ph=False)
    result = base_must.attenuation(fg=fg)
    payload = {"og": base_must.gravity, "fg": fg, "attenuation_percent": result}
    _emit(payload if output == OutputFormat.json else f'{round(result, 2)}%', output)


@app.command("stalled-gravity")
def calc_stalled_gravity(
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    yeast: str = typer.Option(..., "--yeast", help="Yeast strain name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_yeast_choices() if k.startswith(incomplete)]),
    method: AbvMethod = typer.Option(AbvMethod.cutaia, "--method", help="ABV calculation method"),
    tol: float = typer.Option(1e-6, "--tol", help="Root finding tolerance"),
    min_fg: float = typer.Option(0.9, "--min-fg", help="Minimum FG for root finding"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=None if gravity is None else 3785.41, 
        gravity=gravity, ph=None, require_ph=False)
    yeast_obj = YEAST_STRAINS.get(yeast.strip().lower(), None)
    if yeast_obj is None:
        choices = ", ".join(sorted(YEAST_STRAINS.keys()))
        raise typer.BadParameter(f"Invalid yeast strain: {yeast}, choose from: {choices}")
    
    result = base_must.stalled_final_gravity(
        yeast=yeast_obj, method=method.value, tol=tol, min_fg=min_fg)
    payload = {
        "og": base_must.gravity,
        "yeast_abv_limit_percent": yeast_obj.abv_limit,
        "method": method.value,
        "stalled_fg": result,
    }
    _emit(payload if output == OutputFormat.json else round(result, 4), output)


@app.command("original-gravity")
def calc_original_gravity(
    target_abv: float = typer.Option(..., "--abv", help="Target ABV in percent"),
    fg: float = typer.Option(1.0, "--fg", help="Final gravity"),
    method: AbvMethod = typer.Option(AbvMethod.cutaia, "--method", help="ABV calculation method"),
    tol: float = typer.Option(1e-6, "--tol", help="Root finding tolerance"),
    max_og: float = typer.Option(1.3, "--max-og", help="Maximum original gravity bound"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    result = original_gravity(
        target_abv=target_abv, fg=fg, method=method.value, tol=tol, max_og=max_og)
    payload = {
        "target_abv_percent": target_abv,
        "fg": fg,
        "method": method.value,
        "original_gravity": result,
    }
    _emit(payload if output == OutputFormat.json else round(result, 4), output)


@app.command("residual-co2")
def calc_residual_co2(
    temp: float = typer.Option(..., "--temp", help="Temperature in C"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    result = Must(volume=1.0, gravity=1.0, ph=None).residual_co2(temp)
    _emit(f'{round(result, 2)} volumes, {round(result * 1.96, 3)} g/L', output)


@app.command("volumes")
def calc_volumes(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must specific gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    fermentable: str = typer.Option("honey", "--fermentable", help="Fermentable name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    base: str = typer.Option("water", "--base", help="Base fermentable or fruit name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [
            k for k in get_fermentable_choices() + get_fruit_choices() if k.startswith(incomplete)]),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=None, 
        require_ph=False)
    fermentable_key = fermentable.strip().lower()
    base_key = base.strip().lower()
    if fermentable_key not in FERMENTABLES:
        choices = ", ".join(sorted(FERMENTABLES.keys()))
        raise typer.BadParameter(f"unknown fermentable or base. Choose from: {choices}")
    
    if base_key in FERMENTABLES:
        result = base_must.volumes(FERMENTABLES[fermentable_key], base=FERMENTABLES[base_key])
        fruit = False
    elif base_key in FRUITS:
        result = base_must.volumes_with_fruit_juice(
            FERMENTABLES[fermentable_key], fruit=FRUITS[base_key])
        fruit = True
    else:
        choices = ", ".join(sorted(get_fermentable_choices() + get_fruit_choices()))
        raise typer.BadParameter(f"unknown base '{base}'. Choose from: {choices}")
        
    masses = {
        "fermentable": round(result[0], 2),
        "base": round(result[1], 2),
    }
    payload = {
        "current_volume_ml": base_must.volume,
        "current_gravity": base_must.gravity,
        "fermentable": fermentable_key,
        "base": base_key,
        "mass_g": masses,
    }
    base_units = "ml" if fruit else "g"
    _emit(
        payload if output == OutputFormat.json 
        else f'{fermentable_key}={masses["fermentable"]}g\nbase={masses["base"]}{base_units}', 
        output
    )


@app.command("priming")
def calc_priming_sugar(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for must"),
    target_co2_vol: float = typer.Option(..., "--co2", help="Target CO2 volumes"),
    temp: float = typer.Option(..., "--temp", help="Fermentation temperature in C"),
    fermentable: str = typer.Option(None, "--fermentable", help="Fermentable for priming",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in FERMENTABLES.keys() if k.startswith(incomplete)]),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    gravity = None if volume is None else 1.0
    must = _must_from_args(label="Must", recipe=recipe, volume=volume, gravity=gravity, 
                           ph=None, require_ph=False)
    fermentable_obj = FERMENTABLES.get(fermentable.strip().lower(), None)
    if fermentable_obj is None:
        choices = ", ".join(sorted(FERMENTABLES.keys()))
        raise typer.BadParameter(f"Invalid fermentable: {fermentable}, choose from: {choices}")
    result = must.priming_sugar(
        fermentable=fermentable_obj, target_volumes=target_co2_vol, temp=temp)
    _emit(f'{round(result, 2)}g', output)


# ===================================================
#                  Adjust Commands
# ===================================================

@app.command("adjust-gravity")
def adjust_gravity(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must specific gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    target_sg: float = typer.Option(..., "--target-sg", help="Target specific gravity after dilution"),
    fermentable: str = typer.Option(None, "--fermentable", help="Fermentable name for dilution",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Fruit name for dilution",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=7, require_ph=False)
    if fermentable is None:
        if fruit is None:
            raise typer.BadParameter("Either --fermentable or --fruit must be provided")
        result = base_must.adjust_gravity_with_fruit_juice(
            target_sg=target_sg, 
            fruit=FRUITS[fruit.strip().lower()]
        )
    else:
        result = base_must.adjust_gravity(
            target_sg=target_sg, 
            fermentable=FERMENTABLES[fermentable.strip().lower()]
        )
    payload = {
        "current_volume_ml": base_must.volume,
        "current_gravity": base_must.gravity,
        "target_gravity": target_sg,
        "fermentable_g": fermentable.strip().lower() if fermentable else None,
        'fruit_juice_ml': fruit.strip().lower() if fruit else None,
        "added_fermentable_g": round(result, 2),
    }
    if fruit:
        result = f'{round(result, 2)}ml'
    else:
        result = f'{round(result, 2)}g'
    _emit(
        payload if output == OutputFormat.json else result,
        output
    )


@app.command("backsweeten")
def backsweeten(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    final_sg: float = typer.Option(..., "--final-sg", help="Final gravity before backsweetening"),
    target_sg: float = typer.Option(..., "--target-sg", help="Target gravity after backsweetening"),
    fermentable: str = typer.Option(None, "--fermentable", help="Fermentable name for backsweetening",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Fruit name for backsweetening",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    volume = None if recipe is not None else volume
    gravity = None if recipe is not None else 1.0
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=7, 
        require_ph=False)
    if fermentable is None:
        if fruit is None:
            raise typer.BadParameter("Either --fermentable or --fruit must be provided")
        result = base_must.backsweeten_with_fruit_juice(
            final_sg=final_sg, target_sg=target_sg,
            fruit=FRUITS[fruit.strip().lower()])
    else:
        result = base_must.backsweeten(
            final_sg=final_sg, target_sg=target_sg,
            sweetener=FERMENTABLES[fermentable.strip().lower()])
        
    payload = {
        "current_volume_ml": base_must.volume,
        "final_gravity": final_sg,
        "target_gravity": target_sg,
        "fermentable_g": fermentable.strip().lower() if fermentable else None,
        'fruit_juice_ml': fruit.strip().lower() if fruit else None,
        "added_fermentable_g": round(result, 2),
    }
    if fruit:
        result = f'{round(result, 2)}ml'
    else:
        result = f'{round(result, 2)}g'
    _emit(
        payload if output == OutputFormat.json else result,
        output
    )
    

@app.command("adjust-ta")
def adjust_ta(
    volume: Optional[float] = typer.Option(None, "--vol", help="Batch volume in mL"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for must"),
    current_ta: float = typer.Option(..., "--current-ta", help="Current TA in g/L as tartaric equivalent"),
    target_ta: float = typer.Option(..., "--target-ta", help="Target TA in g/L as tartaric equivalent"),
    acid: str = typer.Option("tartaric", "--acid", help="Acid to add",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_acid_choices() if k.startswith(incomplete)]),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    acid_key = acid.strip().lower()
    acid_obj = ACID_ADJUSTMENTS.get(acid_key)
    if acid_obj is None:
        choices = ", ".join(sorted(ACID_ADJUSTMENTS.keys()))
        raise typer.BadParameter(f"unknown acid '{acid}'. Choose one of: {choices}")

    must = _must_from_args(label="Must", recipe=recipe, volume=volume, 
                           gravity=None if recipe else 1.0, ph=None, require_ph=False)
    try:
        result = must.adjust_ta(
            current_ta=current_ta,
            target_ta=target_ta,
            acid=acid_obj,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    payload = {"acid": acid_key, "volume_ml": must.volume, **result}
    _emit(
        payload if output == OutputFormat.json else (
            f"Total: {round(result['acid_addition_grams'], 2)}g {acid_key}\n"
            f"Rate: {round(result['acid_addition_g_per_l'], 3)}g/L"
        ),
        output,
    )


@app.command("pitching")
def adjust_pitching_rate(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=None, require_ph=False)
    result = base_must.pitch_rate()
    _emit(
        result if output == OutputFormat.json else 
        f"Yeast: {round(result['yeast_g'], 2)}g\nGo-Ferm: {round(result['goferm_g'], 2)}g",
        output
    )


@app.command("tosna")
def adjust_tosna3(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    yeast: str = typer.Option(..., "--yeast", help="Yeast strain name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in YEAST_STRAINS.keys() if k.startswith(incomplete)]),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=None, require_ph=False)
    yeast_obj = YEAST_STRAINS.get(yeast.strip().lower(), None)
    if yeast_obj is None:
        choices = ", ".join(sorted(YEAST_STRAINS.keys()))
        raise typer.BadParameter(f"Invalid yeast strain: {yeast}, choose from: {choices}")
    result = base_must.tosna_3(yeast=yeast_obj)
    _emit(result, output)
    print('Add this amount at 24h, 48h, 72h after pitch, and at 1/3 sugar depletion.')


@app.command("so2-target")
def adjust_so2_target(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    target_ppm: float = typer.Option(50.0, "--target-ppm", help="Target SO2 in ppm"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, 
        ph=None, require_ph=False)
    result = base_must.so2_from_target_ppm(target_ppm=target_ppm)
    _emit(result, output)


@app.command("so2-ph")
def adjust_so2_ph(
    volume: Optional[float] = typer.Option(None, "--vol", help="Must volume in mL"),
    gravity: Optional[float] = typer.Option(None, "--og", help="Must original gravity"),
    recipe: Optional[str] = typer.Option(None, "--recipe", help="Path to recipe for base must"),
    ph: Optional[float] = typer.Option(None, "--ph", help="Must pH"),
    target_mol_so2: float = typer.Option(0.8, "--target-mol-so2", help="Target molecular SO2 in ppm"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    if recipe and ph is not None:
        raise typer.BadParameter("Do not pass --ph when using --recipe.")
    require_ph = not recipe
    base_must = _must_from_args(
        label="Base must", recipe=recipe, volume=volume, gravity=gravity, ph=ph, 
        require_ph=require_ph)
    result = base_must.so2_from_ph(
        target_mol_so2=target_mol_so2)
    _emit(result, output)


if __name__ == "__main__":
    app()
