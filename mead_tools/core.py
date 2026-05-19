from dataclasses import dataclass
import math


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
    ph: float

    def volume(self, mass: float) -> float:
        '''Returns the volume of the additive given a mass in grams.'''
        return mass / self.density


# Define some common additives with their PPG and density in g/mL.
FERMENTABLES = {
    'water': Fermentable(ppg=0,  density=1.00, ph=7.0),
    'honey': Fermentable(ppg=35, density=1.42, ph=3.9),
    'maple': Fermentable(ppg=30, density=1.33, ph=5.2),
    'agave': Fermentable(ppg=34, density=1.42, ph=4.5),
    'molasses': Fermentable(ppg=36, density=1.40, ph=5.5),
    'table-sugar': Fermentable(ppg=46, density=1.59, ph=6.0),
    'brown-sugar': Fermentable(ppg=45, density=1.54, ph=5.5),
    'liquid-malt-extract': Fermentable(ppg=36, density=1.42, ph=5.5),
}


@dataclass
class Fruit:
    '''Represents a solid fruit additive.'''
    brix: float
    moisture_content: float
    ph: float

    def to_fermentable(self, density: float | None=None) -> Fermentable:
        '''Returns a Fermentable representation of this fruit for dilution calculations.'''
        ppg_est = 0.46 * self.brix
        density_est = brix_to_sg(self.brix) if density is None else density
        return Fermentable(ppg=ppg_est, density=density_est, ph=self.ph)


# Common whole-fruit profiles for recipe planning.
FRUITS = {
    'apple': Fruit(brix=12.0, moisture_content=86.0, ph=3.5),
    'pear': Fruit(brix=13.0, moisture_content=84.0, ph=3.6),
    'peach': Fruit(brix=11.0, moisture_content=88.0, ph=3.7),
    'plum': Fruit(brix=12.0, moisture_content=86.0, ph=3.5),
    'apricot': Fruit(brix=13.0, moisture_content=84.0, ph=3.8),
    'cherry-bing': Fruit(brix=18.0, moisture_content=80.0, ph=4.0),
    'cherry-montmorency': Fruit(brix=13.0, moisture_content=82.0, ph=3.5),
    'strawberry': Fruit(brix=8.0, moisture_content=90.0, ph=3.5),
    'raspberry': Fruit(brix=9.0, moisture_content=86.0, ph=3.5),
    'blackberry': Fruit(brix=10.0, moisture_content=88.0, ph=3.5),
    'blueberry': Fruit(brix=12.0, moisture_content=85.0, ph=3.2),
    'cranberry': Fruit(brix=8.0, moisture_content=87.0, ph=2.5),
    'elderberry': Fruit(brix=11.0, moisture_content=80.0, ph=4.9),
    'grape-niagara': Fruit(brix=16.0, moisture_content=82.0, ph=3.2),
    'grape-concord': Fruit(brix=17.0, moisture_content=82.0, ph=3.4),
    'grape-cabernet': Fruit(brix=24.0, moisture_content=73.0, ph=3.4),
    'grape-late-harvest': Fruit(brix=28.0, moisture_content=65.0, ph=3.6),
    'banana': Fruit(brix=20.0, moisture_content=75.0, ph=4.9),
    'pomegranate': Fruit(brix=16.0, moisture_content=80.0, ph=3.1),
    'watermelon': Fruit(brix=10.0, moisture_content=92.0, ph=5.3),
    'cantaloupe': Fruit(brix=12.0, moisture_content=90.0, ph=6.3),
    'fig': Fruit(brix=20.0, moisture_content=80.0, ph=5.5),
    'mango': Fruit(brix=15.0, moisture_content=83.0, ph=4.0),
}


@dataclass
class Yeast:
    abv_limit: float
    nitrogen_requirement: str


# common yeast profiles for recipe planning
YEAST_STRAINS = {
    '71b': Yeast(abv_limit=14.5, nitrogen_requirement='low'),
    'ec1118': Yeast(abv_limit=18.0, nitrogen_requirement='low'),
    'k1v1116': Yeast(abv_limit=18.0, nitrogen_requirement='low'),
    'qa23': Yeast(abv_limit=16.0, nitrogen_requirement='low'),
    'd47': Yeast(abv_limit=15.0, nitrogen_requirement='medium'),
    's04': Yeast(abv_limit=11.0, nitrogen_requirement='high'),
    'm05': Yeast(abv_limit=18.0, nitrogen_requirement='medium'),
    'rc212': Yeast(abv_limit=16.0, nitrogen_requirement='medium'),
    'voss-kveik': Yeast(abv_limit=12.0, nitrogen_requirement='high'),
}


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

    def stalled_final_gravity(self, yeast: Yeast, method: str='cutaia', 
                              tol: float=1e-6, min_fg: float=0.9) -> float:
        '''Returns the final gravity at which fermentation will stall given a yeast ABV 
        limit and method.
        
        :param yeast: Yeast object
        :param method: calculation method for ABV ('standard', 'alternate', or 'cutaia')
        :param tol: tolerance for the root-finding algorithm
        :param min_fg: minimum final gravity to consider for root-finding
        '''
        def f_fg_to_abv(fg):
            return self.potential_abv(fg=fg, method=method) - yeast.abv_limit
        return root_find(f_fg_to_abv, min_fg, self.gravity, tol=tol)
     
    def dilution(self, fermentable: Fermentable, base: Fermentable=FERMENTABLES['water']) -> float:
        '''Returns the mass of a fermentable and base required to create this must.'''
        target_points = (self.gravity - 1.0) * 1000.0
        total_mass_g = self.gravity * self.volume
        conversion_factor = 453.592 / 3785.41
        required_combined_points = target_points * conversion_factor * self.volume
        denominator = fermentable.ppg - base.ppg
        mass_ferment_g = (required_combined_points - (total_mass_g * base.ppg)) / denominator
        mass_base_g = total_mass_g - mass_ferment_g
        return mass_ferment_g, mass_base_g

    def dilution_with_fruit_juice(self, fermentable: Fermentable, fruit: Fruit) -> float:
        '''Returns the volume of fruit juice in ml required to dilute the fermentable 
        to create this must.
        
        :param fermentable: the Fermentable to dilute with fruit juice
        :param fruit: the Fruit profile to use for the juice
        '''
        base = fruit.to_fermentable()
        mass_ferment_g, mass_base_g = self.dilution(fermentable=fermentable, base=base)
        vol_base_ml = mass_base_g / base.density
        return mass_ferment_g, vol_base_ml

    def adjust_gravity(self, target_sg: float, fermentable: Fermentable, tol: float=1e-6) -> float:
        '''Compute mass in grams of `fermentable` to add to this must to reach `target_sg`.
        
        :param target_sg: the target specific gravity after dilution
        :param fermentable: the Fermentable to add for dilution
        :param tol: tolerance for the root-finding algorithm
        '''
        def f_mass_to_abv(m):
            return self.add(fermentable, m).gravity - target_sg

        if target_sg <= 0.0:
            raise ValueError('target_sg must be positive.')
        if abs(f_mass_to_abv(0.0)) < tol:
            return 0.0
        need_increase = (target_sg > self.gravity)
        if need_increase and fermentable.ppg <= 0:
            raise ValueError('Selected fermentable cannot raise gravity (ppg <= 0).')
        if (not need_increase) and fermentable.ppg > 0:
            raise ValueError('Selected fermentable will not lower gravity; use water or a diluent (ppg=0).')

        a0, b0 = 0.0, 100.0
        a, b = root_bracket(f_mass_to_abv, a0, b0)
        return root_find(f_mass_to_abv, a, b, tol=tol)
    
    def adjust_gravity_with_fruit_juice(self, target_sg: float, fruit: Fruit, tol: float=1e-6) -> float:
        '''Compute volume in mL of fruit juice to add to this must to reach `target_sg`.
        
        :param target_sg: the target specific gravity after dilution
        :param fruit: the Fruit profile to use for the juice
        :param tol: tolerance for the root-finding algorithm
        '''
        def f_vol_to_abv(v):
            return self.add_fruit_juice(fruit, v).gravity - target_sg

        if target_sg <= 0.0:
            raise ValueError('target_sg must be positive.')
        if abs(f_vol_to_abv(0.0)) < tol:
            return 0.0

        a0, b0 = 0.0, 1000.0
        a, b = root_bracket(f_vol_to_abv, a0, b0)
        return root_find(f_vol_to_abv, a, b, tol=tol)

    # ====================================================================================
    #                           Adjustment Calculation Methods    
    # ====================================================================================
    
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
    
    def __str__(self):
        if self.ph is None:
            return f"Must(volume={self.volume:.2f}ml, gravity={self.gravity:.4f})"
        else:
            return f"Must(volume={self.volume:.2f}ml, gravity={self.gravity:.4f}, ph={self.ph:.2f})"


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
        return Must(volume=1, gravity=og, ph=7).potential_abv(fg=fg, method=method) - target_abv
    return root_find(f_og_to_abv, fg, max_og, tol=tol)
    

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
            lhs, rhs = [s.strip() for s in line.split('=', 1)]
            if not lhs:
                raise ValueError(f"Line {lineno}: empty ingredient.")
            try:
                qty = float(rhs)
            except Exception:
                raise ValueError(f"Line {lineno}: invalid quantity '{rhs}'.")
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
