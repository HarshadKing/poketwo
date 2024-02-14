import random
from typing import Optional

from bson.objectid import ObjectId

from data.models import Species


def generate_gender(species: Species, *, objectid: Optional[ObjectId] = None) -> str:
    """Generates gender weighted by its species' gender data.

    Parameters
    ----------
    species : data.models.Species
        Species object for which to generate a gender, based on its gender_rate and gender_ratios.
    objectid : Optional[bson.objectid.ObjectId]
        If provided, it will generate a gender based on an ObjectId.
        Gender for a particular ObjectId will always be the same.
    """

    if species.gender_rate == -1:
        gender = "Unknown"
    elif objectid is not None:
        _id = int(str(objectid), 16)
        male_term = species.gender_ratios[0]
        gender = "Male" if (_id % 1000) < (male_term * 10) else "Female"
    else:
        gender = random.choices(["Male", "Female"], species.gender_ratios, k=1)[0]
    return gender
