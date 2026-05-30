from dataclasses import dataclass
from importlib import resources
import json
import math
from pathlib import Path
from typing import List, Tuple

import numpy as np
from scipy.optimize import minimize
from scipy.optimize import root_scalar
    

# ===================================================
#                  HELPER FUNCTIONS
# ===================================================

def root_find(f, a, b, tol=1e-6):
    '''Finds a root of the function f in the interval [a, b] using scipys.'''
    sol = root_scalar(f, bracket=[a, b], method='brentq', xtol=tol)
    if not sol.converged:
        raise ValueError('Root finding did not converge.')
    return sol.root


def root_bracket(f, a, b, expand=2.0, max_bound=1e7):
    '''Returns a bracket [a, b] such that f(a) and f(b) have opposite signs.'''
    fa, fb = f(a), f(b)
    if fa == 0.0:
        return a, b
    while fa * fb > 0 and abs(b) < max_bound:
        b *= expand
        fb = f(b)
    if fa * fb > 0:
        raise ValueError('Unable to bracket root.')
    return a, b


def quadratic_solve(f, x0, bounds, constraints):
    '''Solves a quadratic optimization problem using scipy's minimize function.'''
    result = minimize(f, x0, bounds=bounds, constraints=constraints)
    if not result.success:
        raise RuntimeError(f'Quadratic optimization failed: {result.message}.')
    return result.x


def sg_to_plato(sg: float) -> float:
    '''Converts specific gravity to Plato using the polynomial approximation.'''
    if sg <= 0.0:
        raise ValueError('Specific gravity must be positive.')
    return -616.868 + (1111.14 * sg) - (630.272 * sg ** 2) + (135.997 * sg ** 3)


def brix_to_sg(brix: float) -> float:
    '''Converts Brix to specific gravity using polynomial approximation.'''
    if brix < 0.0:
        raise ValueError('Brix must be non-negative.')
    return 1.0 + (brix / (258.6 - (brix / 258.2) * 227.1))


def spirit_abv_to_sg(abv: float) -> float:
    '''Returns the specific gravity of a spirit given its ABV.
    
    :param abv: the ABV of the spirit in percent
    '''
    if abv < 0 or abv > 100:
        raise ValueError('ABV must be between 0 and 100.')
    x = abv / 100
    return 1.0001 - 0.0431 * x - 0.4524 * x ** 2 + 0.4352 * x ** 3 - 0.1506 * x ** 4 
    

def _load_data_json(filename: str) -> dict:
    path = resources.files('meadery').joinpath('data', filename)
    with path.open('r', encoding='utf-8') as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f'Expected a JSON object in {filename}.')
    return data


# ===================================================
#                  MEASUREMENT TOOLS
# ===================================================

@dataclass
class Hydrometer:
    '''Represents a hydrometer, a device used to measure the specific gravity of a liquid.'''
    calibration_temperature: float

    def corrected_gravity(self, gravity: float, temperature: float) -> float:
        '''Returns the corrected gravity given a measured gravity and temperature.
        
        :param gravity: the measured specific gravity
        :param temperature: the temperature of the liquid in degrees Celsius
        '''
        if gravity <= 0.0:
            raise ValueError('Gravity must be positive.')
        t_m = (temperature * 1.8) + 32.0
        t_c = (self.calibration_temperature * 1.8) + 32.0
        c1, c2, c3, c4 = 1.00130346, -0.000134722124, 0.00000204052596, -0.00000000232820948
        rho_m = c1 + (c2 * t_m) + (c3 * t_m**2) + (c4 * t_m**3)
        rho_c = c1 + (c2 * t_c) + (c3 * t_c**2) + (c4 * t_c**3)
        return gravity * (rho_c / rho_m)


@dataclass
class Refractometer:
    '''Represents a refractometer, a device used to measure the Brix of a liquid.'''

    def corrected_gravity(self, current_brix: float, original_gravity: float) -> float:
        '''Returns the corrected gravity given a measured Brix and original gravity.
        
        :param current_brix: the measured Brix value
        :param original_gravity: the original gravity of the must before fermentation
        '''
        if current_brix < 0.0:
            raise ValueError('Current Brix must be non-negative.')
        if original_gravity <= 0.0:
            raise ValueError('Original gravity must be positive.')
        
        original_brix = sg_to_plato(original_gravity)
        return (1.001843
            - (0.002318474 * original_brix)
            - (0.000007775 * original_brix**2)
            - (0.000000034 * original_brix**3)
            + (0.00574 * current_brix)
            + (0.00003344 * current_brix**2)
            + (0.000000086 * current_brix**3))


# ===================================================
#                  FERMENTABLES
# ===================================================

@dataclass
class Fermentable:
    '''Represents a fermentable that can be added to a must, such as water or honey.'''
    ppg: int
    density: float
    ph: float

    def volume(self, mass: float) -> float:
        '''Returns the volume of the additive given a mass in grams.'''
        if mass < 0.0:
            raise ValueError('Mass must be non-negative.')
        
        return mass / self.density
    

def _load_fermentables() -> dict[str, Fermentable]:
    raw = _load_data_json('fermentables.json')
    loaded = {}
    for name, values in raw.items():
        if not isinstance(name, str):
            raise ValueError('Fermentable names must be strings.')
        if not isinstance(values, dict):
            raise ValueError(f'Fermentable values for {name} must be a JSON object.')
        try:
            loaded[name] = Fermentable(
                ppg=values['ppg'],
                density=values['density'],
                ph=values['ph'],
            )
        except KeyError as exc:
            raise ValueError(f'Missing fermentable field {exc} for {name}.') from exc
    return loaded


FERMENTABLES = _load_fermentables()


def add_fermentable(name: str, ppg: int, density: float, ph: float) -> Fermentable:
    '''Add a fermentable to the JSON data file and refresh `FERMENTABLES`.

    :param name: fermentable name key
    :param ppg: points per pound per gallon
    :param density: density in g/mL
    :param ph: pH value in [0, 14]
    '''
    name_key = name.strip().lower()
    if not name_key:
        raise ValueError('Fermentable name must be non-empty.')
    if ppg < 0:
        raise ValueError('ppg must be non-negative.')
    if density <= 0:
        raise ValueError('density must be positive.')
    if ph < 0 or ph > 14:
        raise ValueError('ph must be between 0 and 14.')

    raw = _load_data_json('fermentables.json')
    if name_key in raw:
        raise ValueError(f"Fermentable '{name_key}' already exists.")
    raw[name_key] = {
        'ppg': int(ppg),
        'density': float(density),
        'ph': float(ph),
    }

    data_path = Path(__file__).resolve().parent / 'data' / 'fermentables.json'
    with data_path.open('w', encoding='utf-8') as fh:
        json.dump(raw, fh, indent=2)
        fh.write('\n')

    FERMENTABLES.clear()
    FERMENTABLES.update(_load_fermentables())


# ===================================================
#                  FRUIT ADDITIONS
# ===================================================

@dataclass
class Fruit:
    '''Represents a solid fruit additive.'''
    brix: float
    moisture_content: float
    ph: float

    def to_fermentable(self, density: float | None=None) -> Fermentable:
        '''Returns a Fermentable representation of this fruit for dilution calculations.'''
        if density is not None and density <= 0.0:
            raise ValueError('Density must be positive if provided.')
        
        ppg_est = 0.46 * self.brix
        density_est = brix_to_sg(self.brix) if density is None else density
        return Fermentable(ppg=ppg_est, density=density_est, ph=self.ph)


def _load_fruits() -> dict[str, Fruit]:
    raw = _load_data_json('fruits.json')
    loaded = {}
    for name, values in raw.items():
        if not isinstance(name, str):
            raise ValueError('Fruit names must be strings.')
        if not isinstance(values, dict):
            raise ValueError(f'Fruit values for {name} must be a JSON object.')
        try:
            loaded[name] = Fruit(
                brix=values['brix'],
                moisture_content=values['moisture_content'],
                ph=values['ph'],
            )
        except KeyError as exc:
            raise ValueError(f'Missing fruit field {exc} for {name}.') from exc
    return loaded


FRUITS = _load_fruits()


def add_fruit(name: str, brix: float, moisture_content: float, ph: float) -> Fruit:
    '''Add a fruit to the JSON data file and refresh `FRUITS`.

    :param name: fruit name key
    :param brix: sugar concentration in Brix
    :param moisture_content: moisture percentage in [0, 100]
    :param ph: pH value in [0, 14]
    '''
    name_key = name.strip().lower()
    if not name_key:
        raise ValueError('Fruit name must be non-empty.')
    if brix < 0:
        raise ValueError('brix must be non-negative.')
    if moisture_content < 0 or moisture_content > 100:
        raise ValueError('moisture_content must be between 0 and 100.')
    if ph < 0 or ph > 14:
        raise ValueError('ph must be between 0 and 14.')

    raw = _load_data_json('fruits.json')
    if name_key in raw:
        raise ValueError(f"Fruit '{name_key}' already exists.")
    raw[name_key] = {
        'brix': float(brix),
        'moisture_content': float(moisture_content),
        'ph': float(ph),
    }

    data_path = Path(__file__).resolve().parent / 'data' / 'fruits.json'
    with data_path.open('w', encoding='utf-8') as fh:
        json.dump(raw, fh, indent=2)
        fh.write('\n')

    FRUITS.clear()
    FRUITS.update(_load_fruits())


# ===================================================
#                  YEAST STRAINS
# ===================================================

@dataclass
class Yeast:
    abv_limit: float
    nitrogen_requirement: str


def _load_yeasts() -> dict[str, Yeast]:
    raw = _load_data_json('yeasts.json')
    loaded = {}
    for name, values in raw.items():
        if not isinstance(name, str):
            raise ValueError('Yeast names must be strings.')
        if not isinstance(values, dict):
            raise ValueError(f'Yeast values for {name} must be a JSON object.')
        try:
            loaded[name] = Yeast(
                abv_limit=values['abv_limit'],
                nitrogen_requirement=values['nitrogen_requirement'],
            )
        except KeyError as exc:
            raise ValueError(f'Missing yeast field {exc} for {name}.') from exc
    return loaded


YEAST_STRAINS = _load_yeasts()


def add_yeast_strain(name: str, abv_limit: float, nitrogen_requirement: str) -> Yeast:
    '''Add a yeast strain to the JSON data file and refresh `YEAST_STRAINS`.

    :param name: yeast strain name key
    :param abv_limit: alcohol tolerance in percent
    :param nitrogen_requirement: relative nitrogen demand label
    '''
    name_key = name.strip().lower()
    if not name_key:
        raise ValueError('Yeast strain name must be non-empty.')
    if abv_limit < 0:
        raise ValueError('abv_limit must be non-negative.')
    requirement = nitrogen_requirement.strip().lower()
    if not requirement:
        raise ValueError('nitrogen_requirement must be non-empty.')

    raw = _load_data_json('yeasts.json')
    if name_key in raw:
        raise ValueError(f"Yeast strain '{name_key}' already exists.")
    raw[name_key] = {
        'abv_limit': float(abv_limit),
        'nitrogen_requirement': requirement,
    }

    data_path = Path(__file__).resolve().parent / 'data' / 'yeasts.json'
    with data_path.open('w', encoding='utf-8') as fh:
        json.dump(raw, fh, indent=2)
        fh.write('\n')

    YEAST_STRAINS.clear()
    YEAST_STRAINS.update(_load_yeasts())


# ===================================================
#                  OTHER ADJUNCTS
# ===================================================

@dataclass
class AcidAddition:
    ta_effect: float


# Acid additions expressed as g/L tartaric-equivalent TA increase per g/L additive.
ACID_ADJUSTMENTS = {
    'tartaric': AcidAddition(ta_effect=1.0),
    'malic': AcidAddition(ta_effect=75.04 / 67.05),
    'citric': AcidAddition(ta_effect=75.04 / 64.04),
}


# ===================================================
#                  MUST FUNCTIONS
# ===================================================

@dataclass
class Must:
    '''Represents a must, a mixture of water and fermentable sugars before fermentation.'''
    volume: float
    gravity: float
    ph: float

    # ====================================================================================
    #                                  Must Manipulation Methods    
    # ====================================================================================

    @staticmethod
    def ph_of_mixture(vol1, ph1, vol2, ph2):
        '''Returns the pH of a mixture of two solutions given their volumes and pH values.'''
        if vol1 < 0 or vol2 < 0:
            raise ValueError('Volumes must be non-negative.')
        if ph1 < 0 or ph1 > 14 or ph2 < 0 or ph2 > 14:
            raise ValueError('pH values must be between 0 and 14.')
        if vol1 + vol2 <= 0:
            raise ValueError('Total volume must be positive to calculate pH of mixture.')
        
        total_h_conc = (10 ** (-ph1) * vol1 + 10 ** (-ph2) * vol2) / (vol1 + vol2)
        return -math.log10(total_h_conc)
    
    def combine(self, other: 'Must') -> 'Must':
        '''Returns a new Must that is the combination of this Must and another Must.'''
        total_volume = self.volume + other.volume
        if total_volume <= 0:
            raise ValueError('Total volume must be positive when combining musts.')
        points_a = (self.gravity - 1.0) * self.volume
        points_b = (other.gravity - 1.0) * other.volume
        new_gravity = 1.0 + (points_a + points_b) / total_volume
        new_ph = self.ph_of_mixture(self.volume, self.ph, other.volume, other.ph)
        return Must(volume=total_volume, gravity=new_gravity, ph=new_ph)

    def add(self, fermentable: Fermentable, mass: float) -> 'Must':
        '''Returns a new Must with the given fermentable added.
        
        :param fermentable: the Fermentable to add
        :param mass: the mass of the fermentable to add in grams
        '''
        if mass < 0:
            raise ValueError('Mass of fermentable must be non-negative.')
        v_total_ml = self.volume + fermentable.volume(mass)
        v_total_gal = v_total_ml / 3785.41
        w_additive_lbs = mass / 453.59
        gravity_added = (w_additive_lbs / v_total_gal) * (fermentable.ppg / 1000)
        points_diluted = (self.gravity - 1) * (self.volume / v_total_ml)
        new_gravity = 1.0 + gravity_added + points_diluted
        new_ph = self.ph_of_mixture(
            self.volume, self.ph, fermentable.volume(mass), fermentable.ph)
        return Must(volume=v_total_ml, gravity=new_gravity, ph=new_ph)

    def add_water(self, mass: float) -> 'Must':
        '''Returns a new Must with the given mass of water added.'''
        return self.add(FERMENTABLES['water'], mass)

    def add_honey(self, mass: float) -> 'Must':
        '''Returns a new Must with the given mass of honey added.'''
        return self.add(FERMENTABLES['honey'], mass)
    
    def add_sugar(self, mass: float) -> 'Must':
        '''Returns a new Must with the given mass of sugar added.'''
        return self.add(FERMENTABLES['table-sugar'], mass)
    
    def add_fruit(self, fruit: Fruit, mass: float, extract_yield: float=1.0) -> 'Must':
        if mass < 0:
            raise ValueError('Fruit mass must be non-negative.')
        if fruit.moisture_content < 0 or fruit.moisture_content > 100:
            raise ValueError('Fruit moisture_content must be between 0 and 100.')
        if fruit.brix < 0 or fruit.brix >= 100:
            raise ValueError('Fruit brix must be between 0 and 100 (exclusive upper bound).')
        if extract_yield < 0 or extract_yield > 1:
            raise ValueError('extract_yield must be between 0 and 1.')

        brix_fraction = fruit.brix / 100.0
        water_mass_g = mass * (fruit.moisture_content / 100.0)
        theoretical_juice_mass_g = water_mass_g / (1.0 - brix_fraction)
        if theoretical_juice_mass_g > mass:
            raise ValueError('Calculated juice mass exceeds total fruit mass.')
        juice_mass_g = theoretical_juice_mass_g * extract_yield
        sg_juice = brix_to_sg(fruit.brix)
        juice_vol_ml = juice_mass_g / sg_juice if juice_mass_g > 0 else 0.0
        juice_must = Must(volume=juice_vol_ml, gravity=sg_juice, ph=fruit.ph)
        return self.combine(juice_must)
    
    def add_fruit_juice(self, fruit: Fruit, volume: float) -> 'Must':
        '''Returns a new Must with the given volume of fruit juice added.
        
        :param fruit: the Fruit profile to use for the juice
        :param volume: the volume of fruit juice to add in milliliters
        '''
        if volume < 0:
            raise ValueError('Fruit juice volume must be non-negative.')
        if fruit.brix < 0 or fruit.brix >= 100:
            raise ValueError('Fruit brix must be between 0 and 100 (exclusive upper bound).')

        sg_juice = brix_to_sg(fruit.brix)
        juice_must = Must(volume=volume, gravity=sg_juice, ph=fruit.ph)
        return self.combine(juice_must)

    def fortify_volume(self, target_abv: float, target_fg: float, spirit_abv: float=40.0,
                       method: str='cutaia', tol: float=1e-6) -> dict:
        '''Returns the volume of spirit needed to fortify this must to a target ABV and FG.
        Also returns the gravity at which to fortify.
        
        :param target_abv: the target ABV in percent
        :param target_fg: the target final gravity after fortification in specific gravity
        :param spirit_abv: the ABV of the spirit used for fortification in percent
        :param method: calculation method for ABV ('standard', 'alternate', or 'cutaia')
        :param tol: tolerance for root finding
        '''
        V = self.volume
        if target_abv < 0 or target_abv > 100:
            raise ValueError('target_abv must be between 0 and 100.')
        if spirit_abv <= target_abv or spirit_abv > 100:
            raise ValueError("Spirit ABV must be between target ABV and 100.")
        if target_fg < 1.0:
            raise ValueError('target_fg must be >= 1.0.')
        if self.potential_abv(fg=target_fg, method=method) >= target_abv:
            raise ValueError("The wine has already fermented past your target ABV.")

        spirit_sg = spirit_abv_to_sg(spirit_abv)

        def fg_before_of_v(v):
            return ((target_fg * (V + v)) - (spirit_sg * v)) / V    
            
        def f_v_to_abv(v):
            post_abv = self.fortify_abv(
                fg=fg_before_of_v(v), spirit_vol_ml=v, spirit_abv=spirit_abv, method=method)
            return post_abv - target_abv

        lo, hi = root_bracket(f_v_to_abv, 0, 1)
        v_needed = root_find(f_v_to_abv, lo, hi, tol=tol)
        if v_needed < 0:
            raise ValueError('Calculated spirit volume is negative.')
        fg_before = fg_before_of_v(v_needed)
        return {"fortify_gravity": fg_before, "spirit_volume": v_needed}

    def fortify_abv(self, fg: float, spirit_vol_ml: float, spirit_abv: float=40.0,
                    method: str='cutaia') -> float:
        '''Return the resulting ABV (%) after fermenting this must from its OG to
        `fg` and then adding `spirit_vol_ml` milliliters of spirit at `spirit_abv` ABV.

        :param fg: the final gravity after fermentation in specific gravity
        :param spirit_vol_ml: the volume of spirit to add in milliliters
        :param spirit_abv: the ABV of the spirit used for fortification in percent
        :param method: calculation method for ABV ('standard', 'alternate', or 'cutaia')
        '''
        if spirit_vol_ml < 0:
            raise ValueError('spirit_vol_ml must be non-negative')
        if spirit_abv < 0 or spirit_abv > 100:
            raise ValueError('spirit_abv must be between 0 and 100')
        if fg < 0.0:
            raise ValueError('Final gravity must be non-negative.')

        produced_abv = self.potential_abv(fg=fg, method=method)
        ethanol_from_must_ml = self.volume * (produced_abv / 100.0)
        ethanol_from_spirit_ml = spirit_vol_ml * (spirit_abv / 100.0)
        total_ethanol_ml = ethanol_from_must_ml + ethanol_from_spirit_ml
        total_volume_ml = self.volume + spirit_vol_ml
        if total_volume_ml <= 0:
            raise ValueError('Total volume after fortification must be positive.')
        return (total_ethanol_ml / total_volume_ml) * 100.0

    # ====================================================================================
    #                              Brewing Calculation Methods    
    # ====================================================================================
    
    def potential_abv(self, fg: float=1.0, method: str='cutaia') -> float:
        '''Returns the potential ABV of the must given a final gravity and method.
        
        :param fg: final gravity to use for the ABV calculation
        :param method: calculation method for ABV ('standard', 'alternate', or 'cutaia')
        '''
        if fg <= 0.0:
            raise ValueError('Final gravity must be positive.')
        
        og = self.gravity
        if fg >= og:
            return 0.0
        elif method == 'standard':
            return (og - fg) * 131.25
        elif method == 'alternate':
            return 76.08 * (og - fg) / (1.775 - og) * (fg / 0.794)
        elif method == 'cutaia':
            oe = sg_to_plato(og)
            ae = sg_to_plato(fg)
            abw = (0.372 + (0.00357 * oe)) * (oe - ae)
            return abw * fg / 0.7907
        else:
            raise ValueError(f'Invalid abv method {method}.')
    
    def attenuation(self, fg: float) -> float:
        '''Returns the apparent attenuation percentage.'''
        if fg <= 0.0:
            raise ValueError('Final gravity must be positive.')
        
        og = self.gravity
        if og <= 1.0:
            return 0.0
        else:
            return ((og - fg) / (og - 1.0)) * 100.0

    def stalled_final_gravity(self, yeast: Yeast, method: str='cutaia', 
                              tol: float=1e-6, min_fg: float=0.9) -> float:
        '''Returns the final gravity at which fermentation will stall given a yeast ABV 
        limit and method.
        
        :param yeast: Yeast object
        :param method: calculation method for ABV ('standard', 'alternate', or 'cutaia')
        :param tol: tolerance for the root-finding algorithm
        :param min_fg: minimum final gravity to consider for root-finding
        '''
        if min_fg <= 0.0:
            raise ValueError('min_fg must be positive.')
        
        def f_fg_to_abv(fg):
            return self.potential_abv(fg=fg, method=method) - yeast.abv_limit
        
        if f_fg_to_abv(min_fg) * f_fg_to_abv(self.gravity) > 0:
            raise ValueError("Yeast ABV limit is not between the potential ABV at min_fg "
                             "and the potential ABV at the must's gravity.")
        return root_find(f_fg_to_abv, min_fg, self.gravity, tol=tol)
     
    def volumes(self, fermentable: Fermentable, base: Fermentable=FERMENTABLES['water']) -> float:
        '''Returns the mass of a fermentable and base required to create this must.'''
        target_points = (self.gravity - 1.0) * 1000.0
        total_mass_g = self.gravity * self.volume
        conversion_factor = 453.592 / 3785.41
        required_combined_points = target_points * conversion_factor * self.volume
        denominator = fermentable.ppg - base.ppg
        mass_ferment_g = (required_combined_points - (total_mass_g * base.ppg)) / denominator
        mass_base_g = total_mass_g - mass_ferment_g
        return mass_ferment_g, mass_base_g

    def volumes_with_fruit_juice(self, fermentable: Fermentable, fruit: Fruit) -> float:
        '''Returns the volume of fruit juice in ml required to dilute the fermentable 
        to create this must.
        
        :param fermentable: the Fermentable to dilute with fruit juice
        :param fruit: the Fruit profile to use for the juice
        '''
        base = fruit.to_fermentable()
        mass_ferment_g, mass_base_g = self.volumes(fermentable=fermentable, base=base)
        vol_base_ml = mass_base_g / base.density
        return mass_ferment_g, vol_base_ml

    def adjust_gravity(self, target_sg: float, fermentable: Fermentable, tol: float=1e-6) -> float:
        '''Compute mass in grams of `fermentable` to add to this must to reach `target_sg`.
        
        :param target_sg: the target specific gravity after dilution
        :param fermentable: the Fermentable to add for dilution
        :param tol: tolerance for the root-finding algorithm
        '''
        if target_sg <= 0.0:
            raise ValueError('target_sg must be positive.')
        if target_sg > self.gravity and fermentable.ppg <= 0:
            raise ValueError('Selected fermentable cannot raise gravity (ppg <= 0).')
        if target_sg <= self.gravity and fermentable.ppg > 0:
            raise ValueError('Selected fermentable will not lower gravity; use water or a diluent (ppg=0).')

        def f_mass_to_abv(m): 
            return self.add(fermentable, m).gravity - target_sg
        
        if abs(f_mass_to_abv(0.0)) < tol:
            return 0.0
        else:
            a, b = root_bracket(f_mass_to_abv, 0, 1)
            return root_find(f_mass_to_abv, a, b, tol=tol)
    
    def adjust_gravity_with_fruit_juice(self, target_sg: float, fruit: Fruit, tol: float=1e-6) -> float:
        '''Compute volume in mL of fruit juice to add to this must to reach `target_sg`.
        
        :param target_sg: the target specific gravity after dilution
        :param fruit: the Fruit profile to use for the juice
        :param tol: tolerance for the root-finding algorithm
        '''
        if target_sg <= 0.0:
            raise ValueError('target_sg must be positive.')
        
        def f_vol_to_abv(v):
            return self.add_fruit_juice(fruit, v).gravity - target_sg
        
        if abs(f_vol_to_abv(0.0)) < tol:
            return 0.0
        else:
            a, b = root_bracket(f_vol_to_abv, 0, 1)
            return root_find(f_vol_to_abv, a, b, tol=tol)

    def backsweeten(self, final_sg: float, target_sg: float, 
                    sweetener: Fermentable, tol: float=1e-6) -> float:
        '''Returns the mass in grams of `sweetener` to add to this must to reach `final_sg'
        after fermentation.
        
        :param final_sg: the target specific gravity after fermentation and backsweetening
        :param target_sg: the specific gravity after fermentation but before backsweetening
        :param sweetener: the Fermentable to add for backsweetening
        :param tol: tolerance for the root-finding algorithm
        '''
        fermented_must = Must(volume=self.volume, gravity=final_sg, ph=self.ph)
        return fermented_must.adjust_gravity(target_sg, sweetener, tol=tol)

    def backsweeten_with_fruit_juice(self, final_sg: float, target_sg: float, 
                                     fruit: Fruit, tol: float=1e-6) -> float:
        '''Returns the volume in mL of fruit juice to add to this must to reach `final_sg' 
        after fermentation.
        
        :param final_sg: the target specific gravity after fermentation and backsweetening
        :param target_sg: the specific gravity after fermentation but before backsweetening
        :param fruit: the Fruit profile to use for the juice
        :param tol: tolerance for the root-finding algorithm
        '''
        fermented_must = Must(volume=self.volume, gravity=final_sg, ph=self.ph)
        return fermented_must.adjust_gravity_with_fruit_juice(target_sg, fruit, tol=tol)
    
    def adjust_ta(self, current_ta: float, target_ta: float, acid: AcidAddition) -> dict:
        '''Return the acid addition required to raise TA to `target_ta`.

        TA values are expressed in g/L as tartaric acid equivalent.

        :param current_ta: current titratable acidity in g/L tartaric equivalent
        :param target_ta: desired titratable acidity in g/L tartaric equivalent
        :param acid: acid profile used for the addition
        '''
        if current_ta < 0 or target_ta < 0:
            raise ValueError('TA values must be non-negative.')
        if target_ta < current_ta:
            raise ValueError('target_ta must be >= current_ta for acid additions.')
        if acid.ta_effect <= 0:
            raise ValueError('Acid TA effect must be positive.')

        ta_increase = target_ta - current_ta
        acid_g_per_l = ta_increase / acid.ta_effect
        total_grams = acid_g_per_l * (self.volume / 1000.0)
        return {
            'current_ta_g_per_l': current_ta,
            'target_ta_g_per_l': target_ta,
            'ta_increase_g_per_l': ta_increase,
            'acid_addition_g_per_l': acid_g_per_l,
            'acid_addition_grams': total_grams,
        }

    # ====================================================================================
    #                           Adjustment Calculation Methods    
    # ====================================================================================
    
    def pitch_rate(self) -> dict:
        '''Returns the recommended yeast and Go-Ferm amounts in grams for this must.'''
        if self.gravity > 1.16:
            pitch_rate = 4
        elif self.gravity >= 1.13:
            pitch_rate = 3
        elif self.gravity >= 1.10:
            pitch_rate = 2
        else:
            pitch_rate = 1
        yeast_g = pitch_rate * (self.volume / 3785.41)
        go_ferm_g = 1.25 * yeast_g
        return {
            'yeast_g': yeast_g,
            'goferm_g': go_ferm_g
        }

    def tosna_3(self, yeast: Yeast) -> dict:
        '''Returns the TOSNA 3.0 schedule for nutrient additions using fermaid O.'''
        plato = sg_to_plato(self.gravity)
        demand_map = { 'low': 0.75, 'medium': 0.9, 'high': 1.25 }
        total_fermaid_o_g = (plato * 10) * demand_map[yeast.nitrogen_requirement] / 50
        total_grams = total_fermaid_o_g * (self.volume / 3785.41)
        return {
            'total_grams':          total_grams,
            'staggered_dose_grams': total_grams / 4,
            'sugar_break_gravity':  1.0 + ((self.gravity - 1.0) * (2.0 / 3.0))
        }
        
    def so2_from_target_ppm(self, target_ppm: float=50.0) -> dict:
        '''Calculates SO2 additions needed for must/wine preservation.'''
        if target_ppm < 0:
            raise ValueError('target_ppm must be non-negative.')
        
        volume_L = self.volume / 1000.0
        so2_grams = (volume_L * target_ppm) / 1000.0
        return {
            'so2_grams':    round(so2_grams, 2),
            'k2s2o5_grams': round(so2_grams / 0.57, 2),
            'khso3_grams':  round(so2_grams / 0.61, 2),
            'target_ppm':   round(target_ppm, 2)
        }
    
    def so2_from_ph(self, target_mol_so2: float=0.8) -> dict:
        '''Calculates SO2 additions needed for must/wine preservation based on pH.

        :param target_mol_so2: the target molecular SO2 concentration in ppm
        '''
        target_ppm = target_mol_so2 * (1.0 + (10.0 ** (self.ph - 1.81)))
        return self.so2_from_target_ppm(target_ppm=target_ppm)

    @staticmethod
    def residual_co2(temp: float) -> float:
        '''Returns the residual CO2 given the temperature of the liquid in Celsius.'''
        temp_f = (temp * 9.0 / 5.0) + 32.0
        return 3.0378 - (0.050062 * temp_f) + (0.00026555 * temp_f ** 2)
        
    def priming_sugar(self, fermentable: Fermentable, target_volumes: float, temp: float) -> float:
        '''Return mass in grams of priming fermentable to reach `target_volumes` CO2.

        :param fermentable: the Fermentable to use for priming
        :param target_volumes: the target CO2 volumes for carbonation
        :param temp: the max post-ferment temperature of the liquid in degrees Celsius
        '''
        if target_volumes < 0:
            raise ValueError('target_volumes must be non-negative.')
        
        volume_l = self.volume / 1000.0
        wine_co2 = self.residual_co2(temp)
        sucrose_g = ((target_volumes * 2) - (wine_co2 * 2)) * 2 * volume_l
        if fermentable.ppg <= 0:
            raise ValueError('Selected fermentable cannot be used for priming (ppg <= 0).')
        multiplier = FERMENTABLES['table-sugar'].ppg / fermentable.ppg
        return max(0, sucrose_g * multiplier)
        
    def __str__(self):
        if self.ph is None:
            return f"Must(volume={self.volume:.2f}ml, gravity={self.gravity:.4f})"
        else:
            return f"Must(volume={self.volume:.2f}ml, gravity={self.gravity:.4f}, ph={self.ph:.2f})"


def parse_recipe(path: str) -> Must:
    """Parse a simple recipe file and return the resulting Must.

    Recipe format (one instruction per line):
      <ingredient>=<quantity>
    - fermentables and whole fruit quantities are in grams
    - fruit juice quantities are in milliliters; write as "<fruit> juice"
    - lines starting with '#' or blank lines are ignored
    """
    must = Must(volume=0.0, gravity=1.0, ph=7.0)
    with open(path, 'r', encoding='utf-8') as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.split('#', 1)[0].strip()
            if not line:
                continue
            if '=' not in line:
                raise ValueError(f"Line {lineno}: missing '=' separator.")
            
            # strip statement of the form lhs = rhs
            lhs, rhs = [s.strip() for s in line.split('=', 1)]
            if not lhs:
                raise ValueError(f"Line {lineno}: empty ingredient.")
            try:
                qty = float(rhs)
            except Exception:
                raise ValueError(f"Line {lineno}: invalid quantity '{rhs}'.")
            
            # convert ingredient name to lowercase for consistent lookup
            key = lhs.lower()
            if key.endswith(' juice'):
                fruit_name = key[:-6].strip()
                fruit = FRUITS.get(fruit_name)
                if fruit is None:
                    raise ValueError(f"Line {lineno}: unknown fruit '{fruit_name}'.")
                must = must.add_fruit_juice(fruit, volume=qty)
            elif key in FERMENTABLES:
                fermentable = FERMENTABLES[key]
                must = must.add(fermentable, qty)
            elif key in FRUITS:
                fruit = FRUITS[key]
                must = must.add_fruit(fruit, qty)
            else:
                raise ValueError(f"Line {lineno}: unknown ingredient '{lhs}'.")
    return must


def original_gravity(target_abv: float, fg: float, 
                     method: str='cutaia', tol: float=1e-6, max_og: float=1.3) -> float:
    '''Returns the original gravity needed to achieve a target ABV given a final gravity 
    and method.
    
    :param target_abv: the target ABV in percent
    :param fg: the final gravity to use for the ABV calculation
    :param method: calculation method for ABV ('standard', 'alternate', or 'cutaia')
    :param tol: tolerance for the root-finding algorithm
    :param max_og: maximum original gravity to consider for root-finding
    '''
    if target_abv < 0 or target_abv > 100:
        raise ValueError('target_abv must be between 0 and 100.')
    if fg <= 0.0:
        raise ValueError('Final gravity must be positive.')
    if max_og <= fg:
        raise ValueError('max_og must be greater than final gravity.')
    
    def f_og_to_abv(og):
        return Must(volume=1, gravity=og, ph=7).potential_abv(fg=fg, method=method) - target_abv
    
    if f_og_to_abv(fg) * f_og_to_abv(max_og) > 0:
        raise ValueError("Target ABV is not between the potential ABV at the final gravity "
                         "and the potential ABV at max_og.")
    return root_find(f_og_to_abv, fg, max_og, tol=tol)
    

def blend_to_gravity(fg1: float, fg2: float, target_fg: float) -> float:
    '''Returns the proportion of wine/mead 1 needed to blend to a target gravity.
    
    :param fg1: final gravity of the first must in specific gravity
    :param fg2: final gravity of the second must in specific gravity
    :param target_fg: the target specific gravity after blending
    '''
    if fg1 <= 0 or fg2 <= 0 or target_fg <= 0:
        raise ValueError('Gravities must be positive.')
    if (target_fg - fg1) * (target_fg - fg2) >= 0:
        raise ValueError('Target gravity must be between the two input gravities.')
    if abs(fg1 - fg2) < 1e-12:
        raise ValueError('Input gravities must be different for blending.')
    
    return (target_fg - fg2) / (fg1 - fg2)


def blend_to_abv(abv1: float, abv2: float, target_abv: float) -> float:
    '''Returns the proportion of wine/mead 1 needed to blend to a target ABV.
    
    :param abv1: ABV of the first must in percent
    :param abv2: ABV of the second must in percent
    :param target_abv: the target ABV after blending in percent
    '''
    if abv1 < 0 or abv2 < 0 or target_abv < 0:
        raise ValueError('ABV values must be non-negative.')
    if (target_abv - abv1) * (target_abv - abv2) >= 0:
        raise ValueError('Target ABV must be between the two input ABVs.')
    if abs(abv1 - abv2) < 1e-12:
        raise ValueError('Input ABVs must be different for blending.')
    
    return (target_abv - abv2) / (abv1 - abv2)


def blend_nearest(abvs: List[float], fgs: List[float], 
                  target_abv: float, target_fg: float, target_vol: float, 
                  w_abv: float=1.0, w_fg: float=1.0, 
                  limits: List[Tuple[float, float]] | None=None) -> dict:
    '''Returns the blending proportions of musts with given ABVs and FGs to achieve a 
    target ABV and FG, giving nearest solutions when exact solutions are infeasible.
    
    :param abvs: list of ABVs of the musts to blend in percent
    :param fgs: list of final gravities of the musts to blend in specific gravity
    :param target_abv: the target ABV after blending in percent
    :param target_fg: the target final gravity after blending in specific gravity
    :param target_vol: the target total volume of the blend in milliliters
    :param w_abv: weight for ABV in the optimization
    :param w_fg: weight for FG in the optimization
    '''
    abvs = np.array(abvs, dtype=float)
    fgs = np.array(fgs, dtype=float)
    N = len(abvs)
    if limits is None:
        limits = [(0.0, 1.0) for _ in range(N)]
    if len(fgs) != N:
        raise ValueError('Length of abvs and fgs must be the same.')
    if len(limits) != N:
        raise ValueError('Length of limits must match number of musts.')
    if np.any(abvs < 0) or np.any(fgs <= 0):
        raise ValueError('ABV values must be non-negative and FG values must be positive.')
    if any(lim[0] < 0 or lim[1] > 1 or lim[0] > lim[1] for lim in limits):
        raise ValueError('Limits must be between 0 and 1 and lower bound must be <= upper bound.')
    if target_abv < 0:
        raise ValueError('target_abv must be non-negative.')
    if target_fg <= 0:
        raise ValueError('target_fg must be positive.')

    # Min-max normalization for ABV and FG
    abv_min = min(np.min(abvs), target_abv)
    abv_max = max(np.max(abvs), target_abv)
    fg_min = min(np.min(fgs), target_fg)
    fg_max = max(np.max(fgs), target_fg)
    abvs_norm = (abvs - abv_min) / (abv_max - abv_min) if abv_max > abv_min else abvs * 0
    fgs_norm = (fgs - fg_min) / (fg_max - fg_min) if fg_max > fg_min else fgs * 0
    target_abv_norm = (target_abv - abv_min) / (abv_max - abv_min) if abv_max > abv_min else 0
    target_fg_norm = (target_fg - fg_min) / (fg_max - fg_min) if fg_max > fg_min else 0

    def objective(lambdas):
        blend_abv = np.dot(lambdas, abvs_norm)
        blend_fg = np.dot(lambdas, fgs_norm)
        return w_abv * (blend_abv - target_abv_norm) ** 2 + w_fg * (blend_fg - target_fg_norm) ** 2

    lambdas = quadratic_solve(
        objective,
        x0=np.ones(N) / N,
        bounds=limits,
        constraints=[{'type': 'eq', 'fun': lambda l: np.sum(l) - 1.0}]
    )
    volumes = lambdas * target_vol
    blend_abv = np.dot(lambdas, abvs)
    blend_fg = np.dot(lambdas, fgs)
    return {
        'volumes': volumes.tolist(),
        'proportions': lambdas.tolist(),
        'blend_abv': float(blend_abv),
        'blend_fg': float(blend_fg)
    }
