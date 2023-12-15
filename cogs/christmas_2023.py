from __future__ import annotations
import contextlib

from datetime import datetime, timedelta
import random
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union
import uuid

import discord
from discord.ext import commands

from cogs import mongo
from cogs.mongo import Member, Pokemon
from data.models import Species
from helpers import checks
from helpers.context import PoketwoContext
from helpers.converters import ItemAndQuantityConverter
from helpers.utils import FlavorString

if TYPE_CHECKING:
    from bot import ClusterBot


CHRISTMAS_PREFIX = "christmas_2023_"
QUESTS_ID = f"{CHRISTMAS_PREFIX}quests"


XP_REQUIREMENT = 1000


class FlavorStrings:
    """Holds various flavor strings"""

    pokecoins = FlavorString("Pokécoins")


# Command strings
CMD_CHRISTMAS = "`{0} christmas`"


QUEST_REWARDS = {
    "daily": 1100,
    "weekly": 2800
}


TYPES = [
    "Normal",
    "Fighting",
    "Flying",
    "Poison",
    "Ground",
    "Rock",
    "Bug",
    "Ghost",
    "Steel",
    "Fire",
    "Water",
    "Grass",
    "Electric",
    "Psychic",
    "Ice",
    "Dragon",
    "Dark",
    "Fairy",
]

REGIONS = ("kanto", "johto", "hoenn", "sinnoh", "unova", "kalos", "alola", "galar")

RARITIES = ("mythical", "legendary", "ub", "event", "paradox")

FORMS = ("alolan", "galarian", "hisuian")

def make_catch_quest(
    count_range: range,
    *,
    type: Optional[TYPES] = None,
    region: Optional[REGIONS] = None,
    rarity: Optional[RARITIES] = None,
    form: Optional[FORMS] = None,
):
    if type:
        condition = {"type": type}
        description = f"Catch {{count}} {type}-type pokémon"
    elif region:
        condition = {"region": region}
        description = f"Catch {{count}} pokémon from the {region.title()} region"
    elif rarity:
        condition = {"rarity": rarity}

        title = rarity.replace("_", " ").title()
        description = f"Catch {{count}} {title} pokémon"
    elif form:
        condition = {"form": form}

        title = "Ultra Beast" if rarity == "ub" else rarity.title()
        description = f"Catch {{count}} {title} pokémon"
    else:
        condition = {}
        description = f"Catch {{count}} pokémon"

    def quest():
        return {
            "event": "catch",
            "count": (count := random.choice(count_range)),
            "condition": condition,
            "description": description.format(count=count),
        }
    return quest

def make_voting_box_quest(count_range: range):
    return lambda: {
        "event": "open_box",
        "count": (count := random.choice(count_range)),
        "description": f"Open {count} voting box",
    }

def make_market_quest(count_range: range, action: Literal["buy", "sell"]):
    if action == "buy":
        description = "Purchase {count} pokémon from the market"
    elif action == "sell":
        description = "Sell {count} pokémon on the market"

    return lambda: {
        "event": f"market_buy",
        "count": (count := random.choice(count_range)),
        "condition": {"action": action},
        "description": description.format(count=count),
    }

def make_trading_quest(count_range: range):
    return {
        "event": "trade",
        "count": (count := random.choice(count_range)),
        "description": f"Trade {count} times",
    }

def make_battling_quest(count_range: range):
    return {
        "event": "battle_win",
        "count": (count := random.choice(count_range)),
        "description": f"Win {count} battles",
    }

def make_release_quest(count_range: range):
    return {
        "event": "release",
        "count": (count := random.choice(count_range)),
        "description": f"Release {count} pokémon",
    }


DAILY_QUESTS = [
    make_catch_quest(range(20, 31)),  # Any catch quest
    *[make_catch_quest(range(10, 21), type=type) for type in TYPES],  # Type pokemon quests
    *[make_catch_quest(range(10, 21), region=region) for region in REGIONS],  # Region pokemon quests
    make_catch_quest(range(5, 11), rarity="event"),  # Event pokemon quests
    make_catch_quest(range(10, 21), rarity="paradox"),  # Paradox pokemon quests

    *[make_market_quest(action, range(5, 11)) for action in ("buy", "sell")],  # Market Purchase/Sale quests

    make_voting_box_quest(range(1, 2)),  # Voting box quest
    make_trading_quest(range(3, 6)),  # Trading quest
    make_battling_quest(range(3, 6)),  # Winning battles quest
    make_release_quest(range(5, 11)),  # Releasing quest
]

WEEKLY_QUESTS = [
    make_catch_quest(range(60, 71)),  # Any catch quest
    *[make_catch_quest(range(50, 71), type=type) for type in TYPES],  # Type pokemon quests
    *[make_catch_quest(range(50, 71), region=region) for region in REGIONS],  # Region pokemon quests
    *[make_catch_quest(range(1, 4), rarity=rarity) for rarity in RARITIES],  # Rare pokemon quests
    *[make_catch_quest(range(1, 4), form=form) for form in FORMS],  # Regional form pokemon quests

    make_voting_box_quest(range(4, 7))  # Voting box quest
    *[make_market_quest(range(15, 21), action=action) for action in ("buy", "sell")],  # Market Purchase/Sale quests
    make_battling_quest(range(10, 14)),  # Winning battles quest
]


class Christmas(commands.Cog):
    """Christmas event commands."""

    def __init__(self, bot):
        self.bot: ClusterBot = bot

    async def make_pokemon(
        self, owner: discord.User | discord.Member, member: Member, *, species: Species, shiny_boost: Optional[int] = 1
    ):
        ivs = [mongo.random_iv() for _ in range(6)]
        shiny = member.determine_shiny(species, boost=shiny_boost)
        return {
            "owner_id": member.id,
            "owned_by": "user",
            "species_id": species.id,
            "level": min(max(int(random.normalvariate(20, 10)), 1), 50),
            "xp": 0,
            "nature": mongo.random_nature(),
            "iv_hp": ivs[0],
            "iv_atk": ivs[1],
            "iv_defn": ivs[2],
            "iv_satk": ivs[3],
            "iv_sdef": ivs[4],
            "iv_spd": ivs[5],
            "iv_total": sum(ivs),
            "shiny": shiny,
            "idx": await self.bot.mongo.fetch_next_idx(owner),
        }

    @checks.has_started()
    @commands.group(aliases=("event", "ev"), invoke_without_command=True, case_insensitive=True)
    async def christmas(self, ctx: PoketwoContext):
        """View christmas event main menu."""

        embed = self.bot.Embed(
            title=f"Christmas 2023 - The Poké Express",
            description="<INSERT TEXT>"
        )

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Christmas(bot))