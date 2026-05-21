from enum import Enum
import json
import typer
from typing import Optional, List

from mead_tools.core import (
    FERMENTABLES,
    FRUITS,
    YEAST_STRAINS,
    Hydrometer,
    Must,
    Refractometer,
    brix_to_sg,
    original_gravity,
    sg_to_plato,
    parse_recipe,
)


app = typer.Typer(help="Mead tools command-line app")
convert_app = typer.Typer(help="Unit and gravity conversions")
correct_app = typer.Typer(help="Hydrometer and refractometer corrections")
must_app = typer.Typer(help="Must manipulation commands")
calc_app = typer.Typer(help="Brewing calculations")
adjust_app = typer.Typer(help="Adjustment schedules and additions")

app.add_typer(convert_app, name="convert")
app.add_typer(correct_app, name="correct")
app.add_typer(must_app, name="must")
app.add_typer(calc_app, name="calc")
app.add_typer(adjust_app, name="adjust")


class OutputFormat(str, Enum):
    text = "text"
    json = "json"


class AbvMethod(str, Enum):
    standard = "standard"
    alternate = "alternate"
    cutaia = "cutaia"


# Helper functions for dynamic choices
def get_fermentable_choices() -> List[str]:
    return list(FERMENTABLES.keys())


def get_fruit_choices() -> List[str]:
    return list(FRUITS.keys())


def get_yeast_choices() -> List[str]:
    return list(YEAST_STRAINS.keys())


def _validate_must(volume: float, gravity: float, ph: Optional[float] = None) -> None:
    if volume < 0:
        raise typer.BadParameter("volume must be >= 0")
    if gravity <= 0:
        raise typer.BadParameter("gravity must be > 0")
    if ph is not None and (ph < 0 or ph > 14):
        raise typer.BadParameter("pH must be between 0 and 14")


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
#                Conversion Commands
# ===================================================

@convert_app.command("sg-to-plato")
def convert_sg_to_plato(
    gravity: float = typer.Option(..., "--sg", help="Specific gravity"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    result = sg_to_plato(gravity)
    _emit(
        {"sg": gravity, "plato": result} if output == OutputFormat.json else round(result, 2), 
        output
    )


@convert_app.command("brix-to-sg")
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

@correct_app.command("hydrometer")
def correct_hydrometer(
    gravity: float = typer.Option(..., "--sg", help="Measured specific gravity"),
    temperature: float = typer.Option(..., "--temp", help="Measured temperature in C"),
    calibration_temperature: float = typer.Option(..., "--calib-temp", help="Hydrometer calibration temperature in C"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    corrected = Hydrometer(calibration_temperature=calibration_temperature).corrected_gravity(
        gravity=gravity,
        temperature=temperature,
    )
    _emit(
        {
            "measured_gravity": gravity,
            "temperature_c": temperature,
            "calibration_temperature_c": calibration_temperature,
            "corrected_gravity": corrected,
        }
        if output == OutputFormat.json else round(corrected, 4),
        output,
    )


@correct_app.command("refractometer")
def correct_refractometer(
    current_brix: float = typer.Option(..., "--brix", help="Current measured Brix"),
    original_gravity: float = typer.Option(..., "--og", help="Original gravity before fermentation"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    corrected = Refractometer().corrected_gravity(
        current_brix=current_brix,
        original_gravity=original_gravity,
    )
    _emit(
        {
            "current_brix": current_brix,
            "original_gravity": original_gravity,
            "corrected_gravity": corrected,
        }
        if output == OutputFormat.json else round(corrected, 4),
        output,
    )


# ===================================================
#                  Must Commands
# ===================================================

@must_app.command("combine")
def must_combine(
    volume_a: float = typer.Option(..., "--vol1", help="Must A volume in mL"),
    gravity_a: float = typer.Option(..., "--sg1", help="Must A specific gravity"),
    ph_a: float = typer.Option(..., "--ph1", help="Must A pH"),
    volume_b: float = typer.Option(..., "--vol2", help="Must B volume in mL"),
    gravity_b: float = typer.Option(..., "--sg2", help="Must B specific gravity"),
    ph_b: float = typer.Option(..., "--ph2", help="Must B pH"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume_a, gravity_a, ph_a)
    _validate_must(volume_b, gravity_b, ph_b)
    result = Must(volume=volume_a, gravity=gravity_a, ph=ph_a).combine(
        Must(volume=volume_b, gravity=gravity_b, ph=ph_b))
    payload = {"volume_ml": result.volume, "gravity": result.gravity, "ph": result.ph}
    _emit(
        payload if output == OutputFormat.json else str(result), 
        output
    )


@must_app.command("add")
def must_add(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--sg", help="Must specific gravity"),
    ph: float = typer.Option(..., "--ph", help="Must pH"),
    fermentable: str = typer.Option(..., "--fermentable", help="Fermentable name",
        case_sensitive=False, show_choices=True, prompt=True, 
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    mass: float = typer.Option(..., "--mass", help="Fermentable mass in grams"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity, ph)
    if mass < 0:
        raise typer.BadParameter("mass must be >= 0")
    fermentable_key = fermentable.strip().lower()
    if fermentable_key not in FERMENTABLES:
        choices = ", ".join(sorted(FERMENTABLES.keys()))
        raise typer.BadParameter(f"unknown fermentable '{fermentable}'. Choose one of: {choices}")
    result = Must(volume=volume, gravity=gravity, ph=ph).add(
        FERMENTABLES[fermentable_key], mass=mass)
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


@must_app.command("add-water")
def must_add_water(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--sg", help="Must specific gravity"),
    ph: float = typer.Option(..., "--ph", help="Must pH"),
    mass: float = typer.Option(..., "--mass", help="Water mass in grams"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity, ph)
    if mass < 0:
        raise typer.BadParameter("mass must be >= 0")

    result = Must(volume=volume, gravity=gravity, ph=ph).add_water(mass=mass)
    payload = {"mass_g": mass, "volume_ml": result.volume, "gravity": result.gravity, 
               "ph": result.ph}
    _emit(
        payload if output == OutputFormat.json else str(result), 
        output
    )


@must_app.command("add-honey")
def must_add_honey(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--sg", help="Must specific gravity"),
    ph: float = typer.Option(..., "--ph", help="Must pH"),
    mass: float = typer.Option(..., "--mass", help="Honey mass in grams"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity, ph)
    if mass < 0:
        raise typer.BadParameter("mass must be >= 0")

    result = Must(volume=volume, gravity=gravity, ph=ph).add_honey(mass=mass)
    payload = {"mass_g": mass, "volume_ml": result.volume, "gravity": result.gravity, 
               "ph": result.ph}
    _emit(
        payload if output == OutputFormat.json else str(result), 
        output
    )


@must_app.command("add-sugar")
def must_add_sugar(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--sg", help="Must specific gravity"),
    ph: float = typer.Option(..., "--ph", help="Must pH"),
    mass: float = typer.Option(..., "--mass", help="Sugar mass in grams"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity, ph)
    if mass < 0:
        raise typer.BadParameter("mass must be >= 0")

    result = Must(volume=volume, gravity=gravity, ph=ph).add_sugar(mass=mass)
    payload = {"mass_g": mass, "volume_ml": result.volume, "gravity": result.gravity, 
               "ph": result.ph}
    _emit(
        payload if output == OutputFormat.json else str(result), 
        output
    )


@must_app.command("add-fruit")
def must_add_fruit(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--sg", help="Must specific gravity"),
    ph: float = typer.Option(..., "--ph", help="Must pH"),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Preset fruit name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
    mass: float = typer.Option(..., "--mass", help="Fruit mass in grams"),
    extract_yield: float = typer.Option(1.0, "--extract-yield", help="Extracted juice yield from 0 to 1"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity, ph)
    if mass < 0:
        raise typer.BadParameter("mass must be >= 0")
    if extract_yield < 0 or extract_yield > 1:
        raise typer.BadParameter("extract-yield must be between 0 and 1")

    fruit_key = fruit.strip().lower()
    selected_fruit = FRUITS.get(fruit_key)
    if selected_fruit is None:
        choices = ", ".join(sorted(FRUITS.keys()))
        raise typer.BadParameter(f"unknown fruit '{fruit}'. Choose one of: {choices}")
    source = fruit_key
    
    try:
        result = Must(volume=volume, gravity=gravity, ph=ph).add_fruit(
            selected_fruit, mass=mass, extract_yield=extract_yield)
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


@must_app.command("add-fruit-juice")
def must_add_fruit_juice(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--sg", help="Must specific gravity"),
    ph: float = typer.Option(..., "--ph", help="Must pH"),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Preset fruit name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
    juice_volume: float = typer.Option(..., "--juice-vol", help="Fruit juice volume in mL"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity, ph)
    if juice_volume < 0:
        raise typer.BadParameter("juice-vol must be >= 0")
   
    fruit_key = fruit.strip().lower()
    selected_fruit = FRUITS.get(fruit_key)
    if selected_fruit is None:
        choices = ", ".join(sorted(FRUITS.keys()))
        raise typer.BadParameter(f"unknown fruit '{fruit}'. Choose one of: {choices}")
    source = fruit_key

    try:
        result = Must(volume=volume, gravity=gravity, ph=ph).add_fruit_juice(
            selected_fruit, volume=juice_volume)
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


@must_app.command("from-recipe")
def must_from_recipe(
    recipe: str = typer.Argument(..., help="Path to recipe file"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    try:
        must = parse_recipe(recipe)
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

@calc_app.command("fortify-volume")
def calc_fortify_volume(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--og", help="Must specific gravity"),
    target_abv: Optional[float] = typer.Option(..., "--abv", help="Target ABV in percent"),
    target_gravity: float = typer.Option(..., "--fg", help="Target specific gravity after fortification"),
    spirit_abv: float = typer.Option(40.0, "--spirit-abv", help="Fortifying spirit ABV in percent"),
    method: AbvMethod = typer.Option(AbvMethod.cutaia, "--method", help="ABV calculation method"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    if target_gravity <= 0:
        raise typer.BadParameter("target gravity must be > 0")
    if target_abv is not None and target_abv <= 0:
        raise typer.BadParameter("target ABV must be > 0")
    if spirit_abv <= 0:
        raise typer.BadParameter("spirit ABV must be > 0")

    try:
        result = Must(volume=volume, gravity=gravity, ph=None).fortify_volume(
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


@calc_app.command("fortify-abv")
def calc_fortify_abv(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--og", help="Must specific gravity"),
    fg: float = typer.Option(..., "--fg", help="Final gravity after fermentation"),
    spirit_vol: float = typer.Option(..., "--spirit-vol", help="Volume of fortifying spirit in mL"),
    spirit_abv: float = typer.Option(40.0, "--spirit-abv", help="Fortifying spirit ABV in percent"),
    method: AbvMethod = typer.Option(AbvMethod.cutaia, "--method", help="ABV calculation method"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    if fg <= 0:
        raise typer.BadParameter("final gravity must be > 0")
    if spirit_abv <= 0:
        raise typer.BadParameter("spirit ABV must be > 0")

    result = Must(volume=volume, gravity=gravity, ph=None).fortify_abv(
        fg=fg, spirit_vol_ml=spirit_vol, spirit_abv=spirit_abv, method=method.value)
    payload = {"fg": fg, "fortified_abv_percent": result}
    _emit(
        payload if output == OutputFormat.json else f'{round(result, 2)}%',
        output
    )


@calc_app.command("potential-abv")
def calc_potential_abv(
    gravity: float = typer.Option(..., "--og", help="Original gravity"),
    fg: float = typer.Option(1.0, "--fg", help="Final gravity"),
    method: AbvMethod = typer.Option(AbvMethod.cutaia, "--method", help="ABV calculation method"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    volume = 3785.41
    _validate_must(volume, gravity)
    result = Must(volume=volume, gravity=gravity, ph=None).potential_abv(fg=fg, method=method.value)
    payload = {"og": gravity, "fg": fg, "method": method.value, "abv_percent": result}
    _emit(payload if output == OutputFormat.json else f'{round(result, 2)}%', output)


@calc_app.command("attenuation")
def calc_attenuation(
    gravity: float = typer.Option(..., "--og", help="Original gravity"),
    fg: float = typer.Option(..., "--fg", help="Final gravity"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    volume = 3785.41
    _validate_must(volume, gravity)
    result = Must(volume=volume, gravity=gravity, ph=None).attenuation(fg=fg)
    payload = {"og": gravity, "fg": fg, "attenuation_percent": result}
    _emit(payload if output == OutputFormat.json else f'{round(result, 2)}%', output)


@calc_app.command("stalled-gravity")
def calc_stalled_gravity(
    gravity: float = typer.Option(..., "--og", help="Original gravity"),
    yeast: str = typer.Option(..., "--yeast", help="Yeast strain name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_yeast_choices() if k.startswith(incomplete)]),
    method: AbvMethod = typer.Option(AbvMethod.cutaia, "--method", help="ABV calculation method"),
    tol: float = typer.Option(1e-6, "--tol", help="Root finding tolerance"),
    min_fg: float = typer.Option(0.9, "--min-fg", help="Minimum FG for root finding"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    volume = 3785.41
    _validate_must(volume, gravity)
    yeast_obj = YEAST_STRAINS.get(yeast.strip().lower(), None)
    if yeast_obj is None:
        choices = ", ".join(sorted(YEAST_STRAINS.keys()))
        raise typer.BadParameter(f"Invalid yeast strain: {yeast}, choose from: {choices}")
    result = Must(volume=volume, gravity=gravity, ph=None).stalled_final_gravity(
        yeast=yeast_obj,
        method=method.value,
        tol=tol,
        min_fg=min_fg,
    )
    payload = {
        "og": gravity,
        "yeast_abv_limit_percent": yeast_obj.abv_limit,
        "method": method.value,
        "stalled_fg": result,
    }
    _emit(payload if output == OutputFormat.json else round(result, 4), output)


@calc_app.command("original-gravity")
def calc_original_gravity(
    target_abv: float = typer.Option(..., "--abv", help="Target ABV in percent"),
    fg: float = typer.Option(1.0, "--fg", help="Final gravity"),
    method: AbvMethod = typer.Option(AbvMethod.cutaia, "--method", help="ABV calculation method"),
    tol: float = typer.Option(1e-6, "--tol", help="Root finding tolerance"),
    max_og: float = typer.Option(1.3, "--max-og", help="Maximum original gravity bound"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    result = original_gravity(
        target_abv=target_abv,
        fg=fg,
        method=method.value,
        tol=tol,
        max_og=max_og,
    )
    payload = {
        "target_abv_percent": target_abv,
        "fg": fg,
        "method": method.value,
        "original_gravity": result,
    }
    _emit(payload if output == OutputFormat.json else round(result, 4), output)


@calc_app.command("residual-co2")
def calc_residual_co2(
    temp: float = typer.Option(..., "--temp", help="Temperature in Celsius"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    result = Must(volume=1.0, gravity=1.0, ph=None).residual_co2(temp)
    _emit(f'{round(result, 2)} volumes', output)


@calc_app.command("volumes")
def calc_volumes(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--og", help="Must specific gravity"),
    fermentable: str = typer.Option("honey", "--fermentable", help="Fermentable name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    base: str = typer.Option("water", "--base", help="Base fermentable or fruit name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [
            k for k in get_fermentable_choices() + get_fruit_choices() if k.startswith(incomplete)]),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    fermentable_key = fermentable.strip().lower()
    base_key = base.strip().lower()
    if fermentable_key not in FERMENTABLES:
        choices = ", ".join(sorted(FERMENTABLES.keys()))
        raise typer.BadParameter(f"unknown fermentable or base. Choose from: {choices}")
    
    if base_key in FERMENTABLES:
        result = Must(volume=volume, gravity=gravity, ph=None).volumes(
            FERMENTABLES[fermentable_key], base=FERMENTABLES[base_key])
        fruit = False
    elif base_key in FRUITS:
        result = Must(volume=volume, gravity=gravity, ph=None).volumes_with_fruit_juice(
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
        "current_volume_ml": volume,
        "current_gravity": gravity,
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


@calc_app.command("priming-sugar")
def calc_priming_sugar(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    target_co2_vol: float = typer.Option(..., "--co2", help="Target CO2 volumes"),
    temp: float = typer.Option(..., "--temp", help="Fermentation temperature in C for temperature correction"),
    fermentable: str = typer.Option(None, "--fermentable", help="Fermentable for priming sugar",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in FERMENTABLES.keys() if k.startswith(incomplete)]),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, 1.0)
    fermentable_obj = FERMENTABLES.get(fermentable.strip().lower(), None)
    if fermentable_obj is None:
        choices = ", ".join(sorted(FERMENTABLES.keys()))
        raise typer.BadParameter(f"Invalid fermentable: {fermentable}, choose from: {choices}")
    result = Must(volume=volume, gravity=1.0, ph=None).priming_sugar(
        fermentable=fermentable_obj, target_volumes=target_co2_vol, temp=temp)
    _emit(f'{round(result, 2)}g', output)


# ===================================================
#                  Adjust Commands
# ===================================================

@adjust_app.command("gravity")
def adjust_gravity(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--og", help="Must specific gravity"),
    target_sg: float = typer.Option(..., "--target-sg", help="Target specific gravity after dilution"),
    fermentable: str = typer.Option(None, "--fermentable", help="Fermentable name for dilution",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Fruit name for dilution",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    if target_sg <= 0:
        raise typer.BadParameter("target SG must be > 0")
    if fermentable is None:
        if fruit is None:
            raise typer.BadParameter("Either --fermentable or --fruit must be provided")
        result = Must(volume=volume, gravity=gravity, ph=7).adjust_gravity_with_fruit_juice(
            target_sg=target_sg, 
            fruit=FRUITS[fruit.strip().lower()]
        )
    else:
        result = Must(volume=volume, gravity=gravity, ph=7).adjust_gravity(
            target_sg=target_sg, 
            fermentable=FERMENTABLES[fermentable.strip().lower()]
        )
    payload = {
        "current_volume_ml": volume,
        "current_gravity": gravity,
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

@adjust_app.command("tosna3")
def adjust_tosna3(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--og", help="Original gravity"),
    yeast: str = typer.Option(..., "--yeast", help="Yeast strain name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in YEAST_STRAINS.keys() if k.startswith(incomplete)]),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    yeast_obj = YEAST_STRAINS.get(yeast.strip().lower(), None)
    if yeast_obj is None:
        choices = ", ".join(sorted(YEAST_STRAINS.keys()))
        raise typer.BadParameter(f"Invalid yeast strain: {yeast}, choose from: {choices}")
    result = Must(volume=volume, gravity=gravity, ph=None).tosna_3(yeast=yeast_obj)
    _emit(result, output)
    print('Add this amount at 24h, 48h, 72h after pitch, and at 1/3 sugar depletion.')


@adjust_app.command("so2-target")
def adjust_so2_target(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--og", help="Original gravity"),
    target_ppm: float = typer.Option(50.0, "--target-ppm", help="Target SO2 in ppm"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    result = Must(volume=volume, gravity=gravity, ph=None).so2_from_target_ppm(target_ppm=target_ppm)
    _emit(result, output)


@adjust_app.command("so2-ph")
def adjust_so2_ph(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--og", help="Original gravity"),
    ph: float = typer.Option(..., "--ph", help="Must pH"),
    target_mol_so2: float = typer.Option(0.8, "--target-mol-so2", help="Target molecular SO2 in ppm"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity, ph)
    result = Must(volume=volume, gravity=gravity, ph=ph).so2_from_ph(
        target_mol_so2=target_mol_so2)
    _emit(result, output)


if __name__ == "__main__":
    app()
