import json

from typing import Optional, List
from enum import Enum

import typer

from mead_tools.core import (
    FERMENTABLES,
    FRUITS,
    Fruit,
    Hydrometer,
    Must,
    Refractometer,
    brix_to_sg,
    original_gravity,
    sg_to_plato,
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


class YeastDemand(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


# Helper functions for dynamic choices
def get_fermentable_choices() -> List[str]:
    return list(FERMENTABLES.keys())

def get_fruit_choices() -> List[str]:
    return list(FRUITS.keys())


def _validate_must(volume: float, gravity: float) -> None:
    if volume < 0:
        raise typer.BadParameter("volume must be >= 0")
    if gravity <= 0:
        raise typer.BadParameter("gravity must be > 0")


def _emit(value, output: OutputFormat) -> None:
    if output == OutputFormat.json:
        typer.echo(json.dumps(value, indent=2, sort_keys=True))
        return
    if isinstance(value, dict):
        for key, val in value.items():
            typer.echo(f"{key}: {val}")
        return
    typer.echo(str(value))


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


@must_app.command("combine")
def must_combine(
    volume_a: float = typer.Option(..., "--vol1", help="Must A volume in mL"),
    gravity_a: float = typer.Option(..., "--sg1", help="Must A specific gravity"),
    volume_b: float = typer.Option(..., "--vol2", help="Must B volume in mL"),
    gravity_b: float = typer.Option(..., "--sg2", help="Must B specific gravity"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume_a, gravity_a)
    _validate_must(volume_b, gravity_b)
    result = Must(volume=volume_a, gravity=gravity_a).combine(
        Must(volume=volume_b, gravity=gravity_b))
    payload = {"volume_ml": result.volume, "gravity": result.gravity}
    _emit(
        payload if output == OutputFormat.json 
        else f"vol={round(result.volume, 2)}ml\nsg={round(result.gravity, 4)}", 
        output
    )


@must_app.command("add")
def must_add(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--sg", help="Must specific gravity"),
    fermentable: str = typer.Option(..., "--fermentable", help="Fermentable name",
        case_sensitive=False, show_choices=True, prompt=True, 
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    mass: float = typer.Option(..., "--mass", help="Fermentable mass in grams"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    if mass < 0:
        raise typer.BadParameter("mass must be >= 0")
    fermentable_key = fermentable.strip().lower()
    if fermentable_key not in FERMENTABLES:
        choices = ", ".join(sorted(FERMENTABLES.keys()))
        raise typer.BadParameter(f"unknown fermentable '{fermentable}'. Choose one of: {choices}")
    result = Must(volume=volume, gravity=gravity).add(FERMENTABLES[fermentable_key], mass=mass)
    payload = {
        "fermentable": fermentable_key,
        "mass_g": mass,
        "volume_ml": result.volume,
        "gravity": result.gravity,
    }
    _emit(
        payload if output == OutputFormat.json
        else f"vol={round(result.volume, 2)}ml\nsg={round(result.gravity, 4)}", 
        output
    )


@must_app.command("add-water")
def must_add_water(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--sg", help="Must specific gravity"),
    mass: float = typer.Option(..., "--mass", help="Water mass in grams"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    if mass < 0:
        raise typer.BadParameter("mass must be >= 0")

    result = Must(volume=volume, gravity=gravity).add_water(mass=mass)
    payload = {"mass_g": mass, "volume_ml": result.volume, "gravity": result.gravity}
    _emit(
        payload if output == OutputFormat.json 
        else f"vol={round(result.volume, 2)}ml\nsg={round(result.gravity, 4)}", 
        output
    )


@must_app.command("add-honey")
def must_add_honey(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--sg", help="Must specific gravity"),
    mass: float = typer.Option(..., "--mass", help="Honey mass in grams"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    if mass < 0:
        raise typer.BadParameter("mass must be >= 0")

    result = Must(volume=volume, gravity=gravity).add_honey(mass=mass)
    payload = {"mass_g": mass, "volume_ml": result.volume, "gravity": result.gravity}
    _emit(
        payload if output == OutputFormat.json 
        else f"vol={round(result.volume, 2)}ml\nsg={round(result.gravity, 4)}", 
        output
    )


@must_app.command("add-sugar")
def must_add_sugar(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--sg", help="Must specific gravity"),
    mass: float = typer.Option(..., "--mass", help="Sugar mass in grams"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    if mass < 0:
        raise typer.BadParameter("mass must be >= 0")

    result = Must(volume=volume, gravity=gravity).add_sugar(mass=mass)
    payload = {"mass_g": mass, "volume_ml": result.volume, "gravity": result.gravity}
    _emit(
        payload if output == OutputFormat.json 
        else f"vol={round(result.volume, 2)}ml\nsg={round(result.gravity, 4)}", 
        output
    )


@must_app.command("add-fruit")
def must_add_fruit(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--sg", help="Must specific gravity"),
    mass: float = typer.Option(..., "--mass", help="Fruit mass in grams"),
    fruit: Optional[str] = typer.Option(None, "--fruit", help="Preset fruit name",
        case_sensitive=False, show_choices=True, prompt=False,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fruit_choices() if k.startswith(incomplete)]),
    brix: Optional[float] = typer.Option(None, "--brix", help="Custom fruit juice Brix"),
    moisture: Optional[float] = typer.Option(None, "--moisture", help="Custom fruit moisture percentage"),
    extract_yield: float = typer.Option(1.0, "--extract-yield", help="Extracted juice yield from 0 to 1"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    if mass < 0:
        raise typer.BadParameter("mass must be >= 0")
    if extract_yield < 0 or extract_yield > 1:
        raise typer.BadParameter("extract-yield must be between 0 and 1")

    selected_fruit = None
    source = "custom"
    if fruit is not None:
        fruit_key = fruit.strip().lower()
        selected_fruit = FRUITS.get(fruit_key)
        if selected_fruit is None:
            choices = ", ".join(sorted(FRUITS.keys()))
            raise typer.BadParameter(f"unknown fruit '{fruit}'. Choose one of: {choices}")
        source = fruit_key
    else:
        if brix is None or moisture is None:
            raise typer.BadParameter("provide either --fruit or both --brix and --moisture")
        selected_fruit = Fruit(brix=brix, moisture_content=moisture)

    try:
        result = Must(volume=volume, gravity=gravity).add_fruit(
            selected_fruit,
            mass=mass,
            extract_yield=extract_yield,
        )
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
    }
    _emit(
        payload if output == OutputFormat.json
        else f"vol={round(result.volume, 2)}ml\nsg={round(result.gravity, 4)}",
        output,
    )


@must_app.command("fortify-volume")
def must_fortify_volume(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--sg", help="Must specific gravity"),
    target_abv: Optional[float] = typer.Option(None, "--target-abv", help="Target ABV in percent"),
    target_gravity: float = typer.Option(..., "--target-fg", help="Target specific gravity after fortification"),
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

    result = Must(volume=volume, gravity=gravity).fortify_volume(
        target_abv=target_abv, target_fg=target_gravity, spirit_abv=spirit_abv, method=method.value)
    payload = {"target_abv": target_abv, "target_gravity": target_gravity, 
               "fortified_volume_ml": result}
    _emit(
        payload if output == OutputFormat.json else f'{round(result, 2)}ml',
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
    result = Must(volume=volume, gravity=gravity).potential_abv(fg=fg, method=method.value)
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
    result = Must(volume=volume, gravity=gravity).attenuation(fg=fg)
    payload = {"og": gravity, "fg": fg, "attenuation_percent": result}
    _emit(payload if output == OutputFormat.json else f'{round(result, 2)}%', output)


@calc_app.command("stalled-gravity")
def calc_stalled_gravity(
    gravity: float = typer.Option(..., "--og", help="Original gravity"),
    yeast_abv_limit: float = typer.Option(..., "--max-abv", help="Yeast ABV limit in percent"),
    method: AbvMethod = typer.Option(AbvMethod.cutaia, "--method", help="ABV calculation method"),
    tol: float = typer.Option(1e-6, "--tol", help="Root finding tolerance"),
    min_fg: float = typer.Option(0.9, "--min-fg", help="Minimum FG for root finding"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    volume = 3785.41
    _validate_must(volume, gravity)
    result = Must(volume=volume, gravity=gravity).stalled_final_gravity(
        yeast_abv_limit=yeast_abv_limit,
        method=method.value,
        tol=tol,
        min_fg=min_fg,
    )
    payload = {
        "og": gravity,
        "yeast_abv_limit_percent": yeast_abv_limit,
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


@calc_app.command("dilution")
def calc_dilution(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--og", help="Must specific gravity"),
    fermentable: str = typer.Option("honey", "--fermentable", help="Fermentable name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    base: str = typer.Option("water", "--base", help="Base fermentable name",
        case_sensitive=False, show_choices=True, prompt=True,
        autocompletion=lambda ctx, args, incomplete: [k for k in get_fermentable_choices() if k.startswith(incomplete)]),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    fermentable_key = fermentable.strip().lower()
    base_key = base.strip().lower()
    if fermentable_key not in FERMENTABLES or base_key not in FERMENTABLES:
        choices = ", ".join(sorted(FERMENTABLES.keys()))
        raise typer.BadParameter(f"unknown fermentable or base. Choose from: {choices}")
    result = Must(volume=volume, gravity=gravity).dilution(
        FERMENTABLES[fermentable_key], base=FERMENTABLES[base_key])
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
    _emit(
        payload if output == OutputFormat.json 
        else f'{fermentable_key}={masses["fermentable"]}g\nbase={masses["base"]}g', 
        output
    )


@adjust_app.command("tosna3")
def adjust_tosna3(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--og", help="Original gravity"),
    yeast_demand: YeastDemand = typer.Option(YeastDemand.medium, "--yeast-demand", help="Yeast nutrient demand"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    result = Must(volume=volume, gravity=gravity).tosna_3(yeast_demand=yeast_demand.value)
    _emit(result, output)


@adjust_app.command("so2-target")
def adjust_so2_target(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--og", help="Original gravity"),
    target_ppm: float = typer.Option(50.0, "--target-ppm", help="Target SO2 in ppm"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    result = Must(volume=volume, gravity=gravity).so2_from_target_ppm(target_ppm=target_ppm)
    _emit(result, output)


@adjust_app.command("so2-ph")
def adjust_so2_ph(
    volume: float = typer.Option(..., "--vol", help="Must volume in mL"),
    gravity: float = typer.Option(..., "--og", help="Original gravity"),
    ph: float = typer.Option(..., "--ph", help="Measured pH"),
    target_mol_so2: float = typer.Option(0.8, "--target-mol-so2", help="Target molecular SO2 in ppm"),
    output: OutputFormat = typer.Option(OutputFormat.text, "--format", help="Output format"),
) -> None:
    _validate_must(volume, gravity)
    result = Must(volume=volume, gravity=gravity).so2_from_ph(ph=ph, target_mol_so2=target_mol_so2)
    _emit(result, output)


if __name__ == "__main__":
    app()
