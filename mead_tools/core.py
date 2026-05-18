from dataclasses import dataclass


def root_find(f, a, b, tol=1e-6):
    '''Finds a root of the function f in the interval [a, b] using the regula falsi method.'''
    fa, fb = f(a), f(b)
    while True:
        c = (a * fb - b * fa) / (fb - fa)
        fc = f(c)
        if abs(fc) < tol or abs(b - a) < tol:
            return c
        elif fc * fb < 0:
            a, fa = b, fb
            b, fb = c, fc
        else:
            fa = fa / 2.0  
            b, fb = c, fc


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


def sg_to_plato(sg: float) -> float:
    '''Converts specific gravity to Plato using the polynomial approximation.'''
    return -616.868 + (1111.14 * sg) - (630.272 * sg ** 2) + (135.997 * sg ** 3)


def brix_to_sg(brix: float) -> float:
    '''Converts Brix to specific gravity using polynomial approximation.'''
    return 1.0 + (brix / (258.6 - (brix / 258.2) * 227.1))


@dataclass
class Hydrometer:
    '''Represents a hydrometer, a device used to measure the specific gravity of a liquid.'''
    calibration_temperature: float

    def corrected_gravity(self, gravity: float, temperature: float) -> float:
        '''Returns the corrected gravity given a measured gravity and temperature.
        
        :param gravity: the measured specific gravity
        :param temperature: the temperature of the liquid in degrees Celsius
        '''
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
        original_brix = sg_to_plato(original_gravity)
        return (1.001843
            - (0.002318474 * original_brix)
            - (0.000007775 * original_brix**2)
            - (0.000000034 * original_brix**3)
            + (0.00574 * current_brix)
            + (0.00003344 * current_brix**2)
            + (0.000000086 * current_brix**3))


@dataclass
class Fermentable:
    '''Represents a fermentable that can be added to a must, such as water or honey.'''
    ppg: int
    density: float

    def volume(self, mass: float) -> float:
        '''Returns the volume of the additive given a mass in grams.'''
        return mass / self.density


# Define some common additives with their PPG and density in g/mL.
FERMENTABLES = {
    'water': Fermentable(ppg=0,  density=1.00),
    'white-grape-juice': Fermentable(ppg=5, density=1.06),
    'honey': Fermentable(ppg=35, density=1.42),
    'maple': Fermentable(ppg=30, density=1.33),
    'agave': Fermentable(ppg=34, density=1.42),
    'molasses': Fermentable(ppg=36, density=1.40),
    'table-sugar': Fermentable(ppg=46, density=1.59),
    'brown-sugar': Fermentable(ppg=45, density=1.54),
    'liquid-malt-extract': Fermentable(ppg=36, density=1.42),
}


@dataclass
class Fruit:
    '''Represents a solid fruit additive.'''
    brix: float
    moisture_content: float


# Common whole-fruit profiles for recipe planning.
FRUITS = {
    'apple': Fruit(brix=12.0, moisture_content=86.0),
    'pear': Fruit(brix=13.0, moisture_content=84.0),
    'peach': Fruit(brix=11.0, moisture_content=88.0),
    'plum': Fruit(brix=12.0, moisture_content=86.0),
    'apricot': Fruit(brix=13.0, moisture_content=84.0),
    'cherry-bing': Fruit(brix=18.0, moisture_content=80.0),
    'cherry-montmorency': Fruit(brix=13.0, moisture_content=82.0),
    'strawberry': Fruit(brix=8.0, moisture_content=90.0),
    'raspberry': Fruit(brix=9.0, moisture_content=86.0),
    'blackberry': Fruit(brix=10.0, moisture_content=88.0),
    'blueberry': Fruit(brix=12.0, moisture_content=85.0),
    'cranberry': Fruit(brix=8.0, moisture_content=87.0),
    'elderberry': Fruit(brix=11.0, moisture_content=80.0),
    'grape-wine': Fruit(brix=24.0, moisture_content=74.0),
    'grape-late-harvest': Fruit(brix=28.0, moisture_content=68.0),
    'banana': Fruit(brix=20.0, moisture_content=75.0),
    'pomegranate': Fruit(brix=16.0, moisture_content=80.0),
    'watermelon': Fruit(brix=10.0, moisture_content=92.0)
}


@dataclass
class Must:
    '''Represents a must, a mixture of water and fermentable sugars before fermentation.'''
    volume: float
    gravity: float

    # ====================================================================================
    #                                  Must Manipulation Methods    
    # ====================================================================================

    def combine(self, other: 'Must') -> 'Must':
        '''Returns a new Must that is the combination of this Must and another Must.'''
        total_volume = self.volume + other.volume
        if total_volume <= 0:
            raise ValueError('Total volume must be positive when combining musts.')
        points_a = (self.gravity - 1.0) * self.volume
        points_b = (other.gravity - 1.0) * other.volume
        new_gravity = 1.0 + (points_a + points_b) / total_volume
        return Must(volume=total_volume, gravity=new_gravity)
    
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
        return Must(volume=v_total_ml, gravity=new_gravity)

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
        juice_must = Must(volume=juice_vol_ml, gravity=sg_juice)
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
        if spirit_abv <= target_abv:
            raise ValueError("Spirit ABV must be strictly higher than the target ABV.")
        if target_fg < 1.0:
            raise ValueError('target_fg must be >= 1.0.')
        if self.potential_abv(fg=target_fg, method=method) >= target_abv:
            raise ValueError("The wine has already fermented past your target ABV.")

        def fg_before_of_v(v):
            return 1.0 + (target_fg - 1.0) * (V + v) / V

        def f_v_to_abv(v):
            post_abv = self.fortify_abv(
                fg=fg_before_of_v(v), spirit_vol_ml=v, spirit_abv=spirit_abv, method=method)
            return post_abv - target_abv

        lo, hi = root_bracket(f_v_to_abv, 0.0, max(V, 1))
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
        og = self.gravity
        if og <= 1.0:
            return 0.0
        else:
            return ((og - fg) / (og - 1.0)) * 100.0

    def stalled_final_gravity(self, yeast_abv_limit: float, method: str='cutaia', 
                              tol: float=1e-6, min_fg: float=0.9) -> float:
        '''Returns the final gravity at which fermentation will stall given a yeast ABV 
        limit and method.
        
        :param yeast_abv_limit: ABV limit of the yeast in percent
        :param method: calculation method for ABV ('standard', 'alternate', or 'cutaia')
        :param tol: tolerance for the root-finding algorithm
        :param min_fg: minimum final gravity to consider for root-finding
        '''
        def f_fg_to_abv(fg):
            return self.potential_abv(fg=fg, method=method) - yeast_abv_limit
        return root_find(f_fg_to_abv, min_fg, self.gravity, tol=tol)
     
    def dilution(self, fermentable: Fermentable, base: Fermentable=FERMENTABLES['water']) -> float:
        '''Returns the mass of a fermentable and base required to create this must.'''
        og = self.gravity
        target_points = (og - 1.0) * 1000.0
        total_mass_g = og * self.volume
        conversion_factor = 453.592 / 3785.41
        required_combined_points = target_points * conversion_factor * self.volume
        ppg_f = fermentable.ppg
        ppg_b = base.ppg
        denominator = ppg_f - ppg_b
        mass_ferment_g = (required_combined_points - (total_mass_g * ppg_b)) / denominator
        mass_base_g = total_mass_g - mass_ferment_g
        return mass_ferment_g, mass_base_g

    def dilute_to_sg(self, target_sg: float, fermentable: Fermentable=FERMENTABLES['water'], 
                     tol: float=1e-6) -> float:
        '''Compute mass in grams of `fermentable` to add to this must to reach `target_sg`.
        
        :param target_sg: the target specific gravity after dilution
        :param fermentable: the Fermentable to add for dilution
        :param tol: tolerance for the root-finding algorithm
        '''
        if target_sg >= self.gravity:
            raise ValueError('target_sg must be lower than current must gravity.')
        
        def f_mass_to_abv(m):
            return self.add(fermentable, m).gravity - target_sg
        
        a0, b0 = 0.0, 100.0
        if f_mass_to_abv(a0) <= 0:
            return 0.0
        else:
            a, b = root_bracket(f_mass_to_abv, a0, b0)
            return root_find(f_mass_to_abv, a, b, tol=tol)
        
    # ====================================================================================
    #                           Adjustment Calculation Methods    
    # ====================================================================================
    
    def tosna_3(self, yeast_demand: str='medium') -> dict:
        '''Returns the TOSNA 3.0 schedule for nutrient additions using fermaid O.'''
        og = self.gravity
        plato = sg_to_plato(og)
        demand_map = { 'low': 7.5, 'medium': 9.0, 'high': 12.5 }
        target_yan = plato * demand_map[yeast_demand.lower().strip()]
        grams_per_liter = target_yan / 152.0
        total_grams = grams_per_liter * self.volume / 1000.0
        return {
            'total_grams':          total_grams,
            'staggered_dose_grams': total_grams / 4,
            'target_yan_ppm':       target_yan,
            'sugar_break_gravity':  1.0 + ((og - 1.0) * (2.0 / 3.0))
        }
        
    def so2_from_target_ppm(self, target_ppm: float=50.0) -> dict:
        '''Calculates SO2 additions needed for must/wine preservation.'''
        volume_L = self.volume / 1000.0
        so2_grams = (volume_L * target_ppm) / 1000.0
        return {
            'so2_grams':    round(so2_grams, 2),
            'k2s2o5_grams': round(so2_grams / 0.57, 2),
            'khso3_grams':  round(so2_grams / 0.61, 2),
            'target_ppm':   round(target_ppm, 2)
        }
    
    def so2_from_ph(self, ph: float, target_mol_so2: float=0.8) -> dict:
        '''Calculates SO2 additions needed for must/wine preservation based on pH.

        :param ph: the pH of the must/wine
        :param target_mol_so2: the target molecular SO2 concentration in ppm
        '''
        target_ppm = target_mol_so2 * (1.0 + (10.0 ** (ph - 1.81)))
        return self.so2_from_target_ppm(target_ppm=target_ppm)


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
    def f_og_to_abv(og):
        return Must(1, og).potential_abv(fg=fg, method=method) - target_abv
    return root_find(f_og_to_abv, fg, max_og, tol=tol)
    

if __name__ == "__main__":
    must = Must(volume=3400, gravity=1.11)
    print(must.dilute_to_sg(1.1))
    