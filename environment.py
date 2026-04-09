from constants import *
from random import uniform

def create_daily_rainfall_data(years: int = YEARS_OF_OPERATION):
    # Random data for now. 5 years of daily rainfall data (in mm)
    rainfall_data = []
    for day in range(365*years):
        # Simulate seasonal rainfall patterns with some randomness
        if 60 <= day % 365 <= 150:  # Rainy season
            rainfall = uniform(5, 20)  # mm/day
        else:  # Dry season
            rainfall = uniform(0, 10)  # mm/day
        rainfall_data.append(rainfall)
    return rainfall_data

def daily_hours_of_sunlight(years: int = YEARS_OF_OPERATION):
    # Gives back daily hours of sunlight for 5 years.
    return (
        [8.50]  * 31 +  # January
        [10.0]  * 28 +  # February
        [11.8]  * 31 +  # March
        [13.6]  * 30 +  # April
        [15.3]  * 31 +  # May
        [16.0]  * 30 +  # June
        [15.75] * 31 +  # July
        [14.2]  * 31 +  # August
        [12.5]  * 30 +  # September
        [10.75] * 31 +  # October
        [9.0]   * 30 +  # November
        [8.25]  * 31    # December
    ) * years