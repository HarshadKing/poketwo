from datetime import datetime, timezone
from textwrap import dedent

import discord
from discord.ext import commands

from helpers import checks


class Event(commands.Cog):
    """Cog for simple events that don't have special mechanics and don't need a dedicated cog"""

    def __init__(self, bot):
        self.bot = bot

    @checks.has_started()
    @commands.command(aliases=("ev",))
    async def event(self, ctx):
        """Command to show any currently running event, if any."""

        ends_at = datetime(2024, 3, 27, 21, tzinfo=timezone.utc)
        embed = self.bot.Embed(
            title="Spring Overgrown 🌱",
            description=dedent(
                f"""
                Spring came earlier than expected, which seems to be affecting many Pokémon. Three Pokémon in particular show these overgrown symptoms, catch them before they flee!

                The following Pokémon will appear in the wild to be caught for a week!
                - Overgrown Mawile
                - Blossom Cherrim
                - Overgrown Carnivine

                Ends at {discord.utils.format_dt(ends_at)}. Happy catching! 🌿
                """
            ),
            color=0xB1D99C,
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Event(bot))
