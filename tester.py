from simulator import simulate_design
from optimizer import random_design
from environment import create_daily_rainfall_data, daily_hours_of_sunlight
from utils import print_design
from rich import print

print("Generating parameters...")
design1 = random_design()
design2 = random_design()
rainfall_data = create_daily_rainfall_data()
sunlight_data = daily_hours_of_sunlight()
print("Simulating design...")
result1 = simulate_design(design1, rainfall_data, sunlight_data)
result2 = simulate_design(design2, rainfall_data, sunlight_data)
print("Design parameters (Design 1):")
print_design(design1)
print("Simulation result for random design (Design 1):")
print(result1)
print("\n" + "="*50 + "\n")
print("Design parameters (Design 2):")
print_design(design2)
print("Simulation result for random design (Design 2):")
print(result2)