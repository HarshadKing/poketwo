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

    pokepass = FlavorString("Poképass")
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
            description = f"Spend {count} {FlavorStrings.pokecoins} on the market"

        case "market_sell":
            description = f"Earn {count} {FlavorStrings.pokecoins} from the market"

        case "trade":
            description = f"Trade {count} times"

        case "battle_start":
            if condition:
                if type := condition.get("type"):
                    description = f"Battle {count} times with {type}-type pokémon"
            else:
                description = f"Battle {count} times"

        case "release":
            description = f"Release {count} pokémon"

        case _:
            description = f"{event} {count}"

    return description


def make_quest(event: str, count_range: range, **condition):
    return lambda: {
        "event": event,
        "count": random.choice(count_range),
        "condition": {k: v() if callable(v) else v for k, v in condition.items()},
    }


DAILY_QUESTS = {
    make_quest("catch", range(20, 31)): 15,  # Any catch quest
    make_quest("catch", range(10, 21), type=lambda: random.choice(TYPES)): 15,  # Type pokemon quests
    make_quest("catch", range(10, 21), region=lambda: random.choice(REGIONS)): 10,  # Region pokemon quests
    make_quest("catch", range(5, 11), rarity="event"): 10,  # Event pokemon quests
    make_quest("catch", range(10, 21), rarity="paradox"): 5,  # Paradox pokemon quests
    make_quest("market_buy", [500, 1000]): 5,  # Market Purchase quest
    make_quest("market_sell", [500, 1000]): 10,  # Market Sale quest
    make_quest("open_box", range(1, 2)): 10,  # Voting box quest
    make_quest("trade", range(3, 6)): 5,  # Trading quest
    make_quest("battle_start", range(3, 6), type=lambda: random.choice(TYPES)): 10,  # Battling with certain types quest
    make_quest("release", range(5, 11)): 5,  # Releasing quest
}

WEEKLY_QUESTS = {
    make_quest("catch", range(60, 71)): 15,  # Any catch quest
    make_quest("catch", range(40, 61), type=lambda: random.choice(TYPES)): 10,  # Type pokemon quests
    make_quest("catch", range(40, 51), region=lambda: random.choice(REGIONS)): 5,  # Region pokemon quests
    make_quest("catch", range(1, 4), rarity=lambda: random.choice(RARITIES)): 15,  # Rare pokemon quests
    make_quest("catch", range(1, 4), form=lambda: random.choice(FORMS)): 10,  # Regional form pokemon quests
    make_quest("catch", range(15, 26), rarity="event"): 5,  # Event pokemon quests
    make_quest("market_buy", [4000, 5000, 5500]): 10,  # Market Purchase quest
    make_quest("market_sell", [4000, 5000, 5500]): 10,  # Market Sale quest
    make_quest("open_box", range(4, 7)): 15,  # Voting box quest
    make_quest(
        "battle_start", range(10, 16), type=lambda: random.choice(TYPES)
    ): 10,  # Battling with certain types quest
}


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

        embed = self.bot.Embed(title=f"Christmas 2023 - The Poké Express", description="<INSERT TEXT>")

        await ctx.send(embed=embed)

    async def fetch_quests(self, member: Union[discord.User, discord.Member]) -> List[Dict[str, Any]]:
        member_info = await self.bot.mongo.fetch_member_info(member)

        quests = [q for q in member_info[QUESTS_ID] if datetime.now() < q["expires"]]

        daily_quests = [q for q in quests if q["type"] == "daily"]
        weekly_quests = [q for q in quests if q["type"] == "weekly"]

        if not daily_quests:
            quests.extend(
                [
                    {
                        **q(),
                        "_id": str(uuid.uuid4()),
                        "progress": 0,
                        "type": "daily",
                        "expires": datetime.now() + timedelta(days=1),
                    }
                    for q in random.choices(list(DAILY_QUESTS.keys()), list(DAILY_QUESTS.values()), k=5)
                ]
            )

        if not weekly_quests:
            quests.extend(
                [
                    {
                        **q(),
                        "_id": str(uuid.uuid4()),
                        "progress": 0,
                        "type": "weekly",
                        "expires": datetime.now() + timedelta(days=7),
                    }
                    for q in random.choices(list(WEEKLY_QUESTS.keys()), list(WEEKLY_QUESTS.values()), k=5)
                ]
            )

        if not daily_quests or not weekly_quests:
            await self.bot.mongo.update_member(member, {"$set": {QUESTS_ID: quests}})

        return quests

    @checks.has_started()
    @christmas.command(aliases=["q"])
    async def quests(self, ctx: commands.Context):
        """View Poképass quests."""

        embed = self.bot.Embed(
            title=f"{FlavorStrings.pokepass} Quests",
            description=f"Complete these quests to earn {FlavorStrings.pokepass} XP!",
        )

        all_quests = await self.fetch_quests(ctx.author)

        key = lambda q: q["type"]
        groups = itertools.groupby(sorted(all_quests, key=key), key)  # Group by daily/weekly

        for group, quests in groups:
            expires = None
            value = []
            for q in quests:
                description = get_quest_description(q)

                # TODO: Experimental
                # Underline the description to represent a progress bar
                dl = list(f"\u200b{description}")
                dl.insert(0, "__")
                dl.insert(max(round(q["progress"] / q["count"] * len(dl)), 2), "__")

                value.append(f"{'`☑`' if q.get('completed') else '`☐`'} {''.join(dl)} `{q['progress']}/{q['count']}`")
                expires = q["expires"]

            ts = f"<t:{int(expires.timestamp())}:{{0}}>"
            embed.add_field(
                name=q["type"].capitalize(),
                value="\n".join([f"Resets {ts.format('R')}"] + value),
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.is_owner()
    @christmas.command()
    async def setprogress(self, ctx: PoketwoContext, index: int, progress: int):
        quests = await self.fetch_quests(ctx.author)
        if not quests:
            return await ctx.send("No quests")

        q = quests[index]
        q["progress"] = progress
        q["completed"] = progress >= q["count"]
        await self.bot.mongo.db.member.update_one(
            {"_id": ctx.author.id, f"{QUESTS_ID}._id": q["_id"]},
            {"$set": {f"{QUESTS_ID}.$": q}},
        )

        await self.bot.redis.hdel("db:member", ctx.author.id)
        await ctx.message.add_reaction("✅")

    async def check_quests(self, user: Union[discord.User, discord.Member]):
        quests = await self.fetch_quests(user)
        if not quests:
            return

        for q in quests:
            if q["progress"] >= q["count"] and not q.get("completed"):
                await self.bot.mongo.db.member.update_one(
                    {"_id": user.id, f"{QUESTS_ID}._id": q["_id"]},
                    {"$set": {f"{QUESTS_ID}.$.completed": True}},
                )
                await self.bot.redis.hdel("db:member", user.id)

                inc_xp = QUEST_REWARDS[q["type"]]
                with contextlib.suppress(discord.HTTPException):
                    # TODO: Decide user instead of ctx
                    # await self.give_xp(user, inc_xp)
                    await user.send(
                        f"You completed the {FlavorStrings.pokepass} quest **{get_quest_description(q)}**! You received **{inc_xp}XP**!"
                    )

    def verify_condition(self, condition: dict, species: Species):
        if condition is not None:
            for k, v in condition.items():
                if k == "type" and v not in species.types:
                    return False
                elif k == "region" and v != species.region:
                    return False
                elif k in ("rarity", "form") and species.id not in getattr(self.bot.data, f"list_{v}"):
                    return False
        return True

    async def on_quest_event(self, user: Union[discord.User, discord.Member], event: str, to_verify: list, *, count=1):
        quests = await self.fetch_quests(user)
        if not quests:
            return

        for q in quests:
            if q["event"] != event:
                continue

            if (
                len(to_verify) == 0
                or any(self.verify_condition(q.get("condition"), x) for x in to_verify)
                and not q.get("completed")
            ):
                await self.bot.mongo.db.member.update_one(
                    {"_id": user.id, f"{QUESTS_ID}._id": q["_id"]},
                    {"$inc": {f"{QUESTS_ID}.$.progress": min(count, q["count"])}},
                )

        await self.bot.redis.hdel("db:member", user.id)
        await self.check_quests(user)

    @commands.Cog.listener()
    async def on_catch(self, ctx, species, id):
        await self.on_quest_event(ctx.author, "catch", [species])

    @commands.Cog.listener()
    async def on_market_buy(self, user, pokemon):
        await self.on_quest_event(user, "market_buy", [], count=pokemon["market_data"]["price"])
        await self.on_quest_event(await self.bot.fetch_user(pokemon["owner_id"]), "market_sell", [], count=pokemon["market_data"]["price"])

    @commands.Cog.listener()
    async def on_trade(self, trade):
        a, b = trade["users"]
        await self.on_quest_event(a, "trade", [])
        await self.on_quest_event(b, "trade", [])

    @commands.Cog.listener()
    async def on_battle_start(self, ba):
        self.ba = ba
        await self.on_quest_event(ba.trainers[0].user, "battle_start", [x.species for x in ba.trainers[0].pokemon])
        await self.on_quest_event(ba.trainers[1].user, "battle_start", [x.species for x in ba.trainers[1].pokemon])

    @commands.Cog.listener()
    async def on_release(self, user, count):
        await self.on_quest_event(user, "release", [], count=count)

    @commands.Cog.listener()
    async def on_open_box(self, user, count):
        await self.on_quest_event(user, "open_box", [], count=count)


async def setup(bot: commands.Bot):
    await bot.add_cog(Christmas(bot))
