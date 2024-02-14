import random


def generate_gender(species):
    if species.gender_rate == -1:
        gender = "Unknown"
    else:
        gender = random.choices(["Male", "Female"], species.gender_ratios, k=1)[0]
    return gender
