import random


async def generate_gender(species):
    gender = "Unknown"
    match species.gender_rate:
        case 0:
            gender = "Male"
        case 8:
            gender = "Female"
        case other:
            random_gender_chance = random.randint(1, 99)
            if random_gender_chance > species.gender_ratios[0]:
                gender = "Female"
            else:
                gender = "Male"
    return gender
