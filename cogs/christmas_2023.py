from __future__ import annotations
import contextlib

from datetime import datetime, timedelta
import itertools
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


QUEST_REWARDS = {"daily": 1100, "weekly": 2800}


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

RARITIES = ("mythical", "legendary", "ub")

FORMS = ("alolan", "galarian", "hisuian")


def get_quest_description(quest: dict):
    count = quest["count"]
    event = quest["event"]
    condition = quest.get("condition")

    match event:
        case "catch":
            if condition:
                if type := condition.get("type"):
                    description = f"Catch {count} {type}-type pokémon"
                elif region := condition.get("region"):
                    description = f"Catch {count} pokémon from the {region.title()} region"
                elif rarity := condition.get("rarity"):
                    title = "Ultra Beast" if rarity == "ub" else rarity.title()
                    description = f"Catch {count} {title} pokémon"
                elif form := condition.get("form"):
                    title = form.title()
                    description = f"Catch {count} {title} pokémon"
            else:
                description = f"Catch {count} pokémon"

        case "open_box":
            description = f"Open {count} Voting box{'' if count == 1 else 'es'}"

        case "market_buy":
            action = condition["action"]
            if action == "buy":
                description = f"Purchase {count} pokémon from the market"
            elif action == "sell":
                description = f"Sell {count} pokémon on the market"

        case "trade":
            description = f"Trade {count} times"

        case "battle_win":
            description = f"Win {count} battles"

        case "release":
            description = f"Release {count} pokémon"

    return description


def make_quest(event: str, count_range: range, **condition):
    return lambda: {
        "event": event,
        "count": random.choice(count_range),
        "condition": condition,
    }


DAILY_QUESTS = [
    make_quest("catch", range(20, 31)),  # Any catch quest
    *[make_quest("catch", range(10, 21), type=type) for type in TYPES],  # Type pokemon quests
    *[make_quest("catch", range(10, 21), region=region) for region in REGIONS],  # Region pokemon quests
    make_quest("catch", range(5, 11), rarity="event"),  # Event pokemon quests
    make_quest("catch", range(10, 21), rarity="paradox"),  # Paradox pokemon quests
    *[
        make_quest("market_buy", range(5, 11), action=action) for action in ("buy", "sell")
    ],  # Market Purchase/Sale quests
    make_quest("open_box", range(1, 2)),  # Voting box quest
    make_quest("trade", range(3, 6)),  # Trading quest
    make_quest("battle_win", range(3, 6)),  # Winning battles quest
    make_quest("release", range(5, 11)),  # Releasing quest
]

WEEKLY_QUESTS = [
    make_quest("catch", range(60, 71)),  # Any catch quest
    *[make_quest("catch", range(40, 61), type=type) for type in TYPES],  # Type pokemon quests
    *[make_quest("catch", range(40, 51), region=region) for region in REGIONS],  # Region pokemon quests
    *[make_quest("catch", range(1, 4), rarity=rarity) for rarity in RARITIES],  # Rare pokemon quests
    *[make_quest("catch", range(1, 4), form=form) for form in FORMS],  # Regional form pokemon quests
    make_quest("catch", range(15, 26), rarity="event"),  # Event pokemon quests
    make_quest("open_box", range(4, 7)),  # Voting box quest
    *[
        make_quest("market_buy", range(15, 21), action=action) for action in ("buy", "sell")
    ],  # Market Purchase/Sale quests
    make_quest("battle_win", range(10, 14)),  # Winning battles quest
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