from textwrap import dedent

from discord.ext import commands

from helpers import checks


# For future events, add this cog to cogs/__init__.py and just change these

TITLE = "Spring Overgrown 🌱"
DESCRIPTION = dedent(
    f"""
    Spring came earlier than expected, which seems to be affecting many Pokémon. Three Pokémon in particular show these overgrown symptoms, catch them before they flee!

    The following Pokémon will appear in the wild to be caught for a week!
    - Overgrown Mawile
    - Blossom Cherrim
    - Overgrown Carnivine

    Happy catching! 🌿
    """
)
COLOR = 0xB1D99C


class Event(commands.Cog):
    """Cog for simple events that don't have special mechanics and don't need a dedicated cog"""

    def __init__(self, bot):
        self.bot = bot

    @checks.has_started()
    @commands.command(aliases=("ev",))
    async def event(self, ctx):
        """Command to show any currently running event, if any."""

        embed = self.bot.Embed(
            title=TITLE,
            description=DESCRIPTION,
            color=COLOR,
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Event(bot))
