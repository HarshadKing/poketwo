from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

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


class FlavorStrings:
    """Holds various flavor strings"""

    pokecoins = FlavorString("Pokécoins")


# Command strings
CMD_CHRISTMAS = "`{0} christmas`"


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