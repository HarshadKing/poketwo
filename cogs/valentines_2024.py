from __future__ import annotations
import asyncio
from collections import defaultdict, namedtuple
from functools import cached_property
import math
import contextlib
from textwrap import dedent

from datetime import datetime, timedelta
import itertools
import random
import textwrap
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Tuple, Union
from urllib.parse import urljoin
import uuid

import discord
from discord.ext import commands, tasks
import humanfriendly

from cogs import mongo
from cogs.mongo import Member, PokemonBase
from data.models import Species
from helpers import checks
from helpers.utils import FlavorString
from helpers.context import PoketwoContext


if TYPE_CHECKING:
    from bot import ClusterBot

# GENERAL

VALENTINES_PREFIX = "valentines_2024"
EMBED_COLOR = 0x890000

BOX_ID = f"{VALENTINES_PREFIX}_boxes"
CATCH_ID = f"{VALENTINES_PREFIX}_catches"
REQUIRED_CATCHES = 10

BOX_CHANCES = {
    "pokecoins": 0.50,
    "shards": 0.25,
    "redeems": 0.025,
    "event_pokemon": 0.05,
    "non-event": 0.174,
    "non-event-shiny": 0.001,
}
BOX_REWARD_AMOUNTS = {
    "pokecoins": range(2000, 4000),
    "shards": range(5, 20),
    "redeems": [1],
    "event_pokemon": [1],
    "non-event": [1],
    "non-event-shiny": [1],
}

BOX_REWARDS = [*BOX_CHANCES.keys()]
BOX_WEIGHTS = [*BOX_CHANCES.values()]

## EVENT POKEMON IDS
EVENT_UNFEZANT = 50156
EVENT_MEOWSTIC = 50157

EVENT_CHANCES = {
    # These have been separated for ease of use
    EVENT_UNFEZANT: 0.5,
    EVENT_MEOWSTIC: 0.5,
}

EVENT_REWARDS = [*EVENT_CHANCES.keys()]
EVENT_WEIGHTS = [*EVENT_CHANCES.values()]


class FlavorStrings:
    """Holds various flavor strings."""

    box = FlavorString("Chocolate Box", "<:ValentinesBox:1206998432779206737>", "Chocolate Boxes")

    pokecoins = FlavorString("Pokécoins", "<:pokecoins:1185296751012356126>")
    event_pokemon = FlavorString("Event Pokémon")
    shards = FlavorString("Shards", "<:shards:1185296789918728263>")
    redeem = FlavorString("Redeem")


CMD_OPEN = "`{0} valentines open <qty>`"


class Valentines(commands.Cog):
    """Valentines event commands."""

    def __init__(self, bot):
        self.bot: ClusterBot = bot

    async def cog_load(self):
        self.bot.Embed.CUSTOM_COLOR = EMBED_COLOR  # Set custom embed color for this event

    async def cog_unload(self):
        self.bot.Embed.CUSTOM_COLOR = None  # Unset custom embed color

    @cached_property
    def pools(self) -> Dict[str, List[Species]]:
        p = {
            "event_pokemon": EVENT_REWARDS,
            "non-event": self.bot.data.pokemon.keys(),
        }
        return {k: [self.bot.data.species_by_number(i) for i in v] for k, v in p.items()}

    async def make_reward_pokemon(
        self,
        reward: str,
        user: discord.User | discord.Member,
    ) -> PokemonBase:
        """Function to build specific kinds of pokémon."""

        shiny_boost = 1
        match reward:
            case "event_pokemon":
                population = self.pools["event_pokemon"]
                weights = EVENT_WEIGHTS
                shiny_boost = 5
            case "non-event" | "non-event-shiny":
                population = [x for x in self.pools["non-event"] if x.catchable]
                weights = [x.abundance for x in population]
                if reward == "non-event-shiny":
                    shiny_boost = 4096  # Guarantee shiny

        species = random.choices(population, weights, k=1)[0]
        return await self.bot.mongo.make_pokemon(user, species, shiny_boost=shiny_boost)

    @checks.has_started()
    @commands.group(aliases=("event", "ev"), invoke_without_command=True, case_insensitive=True)
    async def valentines(self, ctx: PoketwoContext):
        """View valentines event main menu."""

        prefix = ctx.clean_prefix.strip()
        embed = self.bot.Embed(
            title=f"Valentine's 2024",
            description=dedent(
                f"""
                In between the cold days there is a special day full of love, Valentine's Day!
                During this 2 week event you can catch several Winter Pokémon in the wild and find Valentine's chocolate boxes along the way!

                During the event, every 10 catches earns you a {FlavorStrings.box:b}.
                To open a box, use {CMD_OPEN.format(prefix)}
                """
            ),
            color=EMBED_COLOR,
        )
        member = await self.bot.mongo.fetch_member_info(ctx.author)
        catches = await self.bot.redis.hget("valentines_catch_count", ctx.author.id)
        catches = int(catches) if catches is not None else 0
        embed.add_field(name=f"{FlavorStrings.box:sb}:", value=f"{member[BOX_ID]:,}", inline=False)
        embed.add_field(
            name=f"Catch progress",
            value=f"{catches}/{REQUIRED_CATCHES}",
        )

        await ctx.send(embed=embed)

    @commands.Cog.listener(name="on_catch")
    async def drop_box(self, ctx: PoketwoContext, species: Species, _id: int):
        count = await self.bot.redis.hincrby("valentines_catch_count", ctx.author.id, 1)
        if count >= REQUIRED_CATCHES:
            await self.bot.mongo.update_member(ctx.author, {"$inc": {f"{VALENTINES_PREFIX}_boxes": 1}})
            await self.bot.mongo.update_member(ctx.author, {"$inc": {f"{VALENTINES_PREFIX}_boxes_total": 1}})
            await self.bot.redis.hdel("valentines_catch_count", ctx.author.id)

            await ctx.send(
                f"You've earned a {FlavorStrings.box}!  Use {CMD_OPEN.format(ctx.clean_prefix.strip())} to open it."
            )

    @checks.has_started()
    @valentines.command(aliases=("o",))
    async def open(self, ctx: PoketwoContext, qty: Optional[int] = 1):
        """Command to open presents. Max qty at a time is 15."""

        if qty <= 0:
            return await ctx.send(f"Nice try...")
        elif qty > 15:
            return await ctx.send(f"You can only open up to 15 {FlavorStrings.box:s!e} at once!")

        member = await self.bot.mongo.fetch_member_info(ctx.author)

        boxes = member[BOX_ID]

        if boxes < qty:
            return await ctx.send(
                f"You don't have enough {FlavorStrings.box:sb}! {FlavorStrings.box:s!e} are earned for every {REQUIRED_CATCHES} catches."
            )

        # GO
        await self.bot.mongo.update_member(ctx.author, {"$inc": {BOX_ID: -qty}})

        embed = self.bot.Embed(
            title=f"You open {qty} {FlavorStrings.box:{'s' if qty > 1 else ''}}...",
            description=None,
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)

        update = {"$inc": {"balance": 0, "premium_balance": 0, "redeems": 0}}
        inserts = []
        text = []

        for reward in random.choices(BOX_REWARDS, weights=BOX_WEIGHTS, k=qty):
            count = random.choice(BOX_REWARD_AMOUNTS[reward])
            match reward:
                case "pokecoins":
                    flavor = getattr(FlavorStrings, reward)
                    text.append(f"- {flavor.emoji} {count} {flavor:!e}")
                    update["$inc"]["balance"] += count
                case "shards":
                    flavor = getattr(FlavorStrings, reward)
                    text.append(f"- {flavor.emoji} {count} {flavor:!e}")
                    update["$inc"]["premium_balance"] += count
                case "redeems":
                    flavor = FlavorStrings.redeem
                    text.append(f"- {count} {flavor:!e{'' if count == 1 else 's'}}")
                    update["$inc"]["redeems"] += count
                case "event_pokemon" | "non-event" | "non-event-shiny":
                    pokemon = await self.make_reward_pokemon(reward, ctx.author)
                    pokemon_obj = self.bot.mongo.Pokemon.build_from_mongo(pokemon)
                    text.append(f"- {pokemon_obj:liPg}")
                    inserts.append(pokemon)

        await self.bot.mongo.update_member(ctx.author, update)
        if len(inserts) > 0:
            await self.bot.mongo.db.pokemon.insert_many(inserts)

        embed.description = "\n".join(text)
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(Valentines(bot))
