from constants import *
from RWHSystem import Design
from utils import print_design

def simulate_design(design: Design):
    tracked = {
        "cost": 0.0,
        "days_without_water": 0,
    }