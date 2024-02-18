import random
from typing import Literal, Optional

from bson.objectid import ObjectId

from data.models import Species

MALE_OVERRIDES = [521, 592, 593, 668, 678, 876, 916]


def generate_gender(species: Species, *, _id: Optional[ObjectId] = None) -> Literal["Unknown", "Male", "Female"]:
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

    if species.default_gender is not None:
        gender = species.default_gender
    elif _id is not None:
        if species.id in MALE_OVERRIDES:
            return "Male"
        seconds = int(_id.generation_time.timestamp())
        gender = "Male" if seconds % int(10 * sum(species.gender_ratios)) < 10 * species.gender_ratios[0] else "Female"
    else:
        gender = random.choices(["Male", "Female"], species.gender_ratios, k=1)[0]

    return gender
