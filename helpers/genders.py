import random
from typing import Literal, Optional

from bson.objectid import ObjectId

from data.models import Species


MALE_OVERRIDES = [521, 592, 593, 668, 678, 876, 916]


def generate_gender(species: Species, *, objectid: Optional[ObjectId] = None) -> Literal["Unknown", "Male", "Female"]:
    """Generates gender weighted by its species' gender data.

    Parameters
    ----------
    species : data.models.Species
        Species object for which to generate a gender, based on its gender_rate and gender_ratios.
    objectid : Optional[bson.objectid.ObjectId]
        If provided, it will generate a gender based on an ObjectId.
        Gender for a particular ObjectId will always be the same.

    Returns
    -------
    Literal["Unknown", "Male", "Female"]
        Generates and returns one of the 3 genders available based on the various conditions.
    """

    if species.gender_rate == -1:
        gender = "Unknown"
    elif objectid is not None:
        if species.id in MALE_OVERRIDES:
            return "Male"

        _id = int(str(objectid), 16)
        male_term = species.gender_ratios[0]
        gender = "Male" if (_id % 1000) < (male_term * 10) else "Female"
    else:
        gender = random.choices(["Male", "Female"], species.gender_ratios, k=1)[0]
    return gender
