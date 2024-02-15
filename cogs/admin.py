import random
import typing
from datetime import datetime

from discord.ext import commands

from helpers.converters import FetchUserConverter, TimeDelta, strfdelta

from . import mongo


class Administration(commands.Cog):
    """Commands for bot administration."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.is_owner()
    @commands.group(aliases=("am",), invoke_without_command=True, case_insensitive=True)
    async def admin(self, ctx):
        pass

    @commands.is_owner()
    @admin.command(aliases=("sp",))
    async def suspend(self, ctx, users: commands.Greedy[FetchUserConverter], *, reason: str = None):
        """Suspend one or more users."""

        await self.bot.mongo.db.member.update_many(
            {"_id": {"$in": [x.id for x in users]}},
            {"$set": {"suspended": True, "suspension_reason": reason}, "$unset": {"suspended_until": 1}},
        )
        await self.bot.redis.hdel("db:member", *[int(x.id) for x in users])
        users_msg = ", ".join(f"**{x}**" for x in users)
        await ctx.send(f"Suspended {users_msg}.")

    @commands.is_owner()
    @admin.command(aliases=("tsp",))
    async def tempsuspend(
        self,
        ctx,
        duration: TimeDelta,
        users: commands.Greedy[FetchUserConverter],
        *,
        reason: str = None,
    ):
        """Temporarily suspend one or more users."""

        await self.bot.mongo.db.member.update_many(
            {"_id": {"$in": [x.id for x in users]}},
            {
                "$set": {"suspended_until": datetime.utcnow() + duration, "suspension_reason": reason},
                "$unset": {"suspended": 1},
            },
        )
        await self.bot.redis.hdel("db:member", *[int(x.id) for x in users])
        users_msg = ", ".join(f"**{x}**" for x in users)
        await ctx.send(f"Suspended {users_msg} for {strfdelta(duration)}.")

    @commands.is_owner()
    @admin.command(aliases=("usp",))
    async def unsuspend(self, ctx, users: commands.Greedy[FetchUserConverter]):
        """Unuspend one or more users."""

        await self.bot.mongo.db.member.update_many(
            {"_id": {"$in": [x.id for x in users]}},
            {"$unset": {"suspended": 1, "suspended_until": 1, "suspension_reason": 1}},
        )
        await self.bot.redis.hdel("db:member", *[int(x.id) for x in users])
        users_msg = ", ".join(f"**{x}**" for x in users)
        await ctx.send(f"Unsuspended {users_msg}.")

    @commands.is_owner()
    @admin.command(aliases=("spawn",))
    async def randomspawn(self, ctx):
        await self.bot.get_cog("Spawning").spawn_pokemon(ctx.channel)

    @commands.is_owner()
    @admin.command(aliases=("giveredeem", "ar", "gr"))
    async def addredeem(self, ctx, user: FetchUserConverter, num: int = 1):
        """Give a redeem."""

        await self.bot.mongo.update_member(user, {"$inc": {"redeems": num}})
        await ctx.send(f"Gave **{user}** {num} redeems.")

    @commands.is_owner()
    @admin.command(aliases=("givecoins", "ac", "gc"))
    async def addcoins(self, ctx, user: FetchUserConverter, amt: int):
        """Add to a user's balance."""

        await self.bot.mongo.update_member(user, {"$inc": {"balance": amt}})
        await ctx.send(f"Gave **{user}** {amt} Pokécoins.")

    @commands.is_owner()
    @admin.command(aliases=("giveshard", "as", "gs"))
    async def addshard(self, ctx, user: FetchUserConverter, amt: int):
        """Add to a user's shard balance."""

        await self.bot.mongo.update_member(user, {"$inc": {"premium_balance": amt}})
        await ctx.send(f"Gave **{user}** {amt} shards.")

    @commands.is_owner()
    @admin.command(aliases=("givevote", "av", "gv"))
    async def addvote(self, ctx, user: FetchUserConverter, amt: int = 1):
        """Add to a user's vote streak."""

        await self.bot.mongo.update_member(
            user,
            {
                "$set": {"last_voted": datetime.utcnow()},
                "$inc": {"vote_total": amt, "vote_streak": amt},
            },
        )

        await ctx.send(f"Increased vote streak by {amt} for **{user}**.")

    @commands.is_owner()
    @admin.command(aliases=("givebox", "ab", "gb"))
    async def addbox(self, ctx, user: FetchUserConverter, box_type, amt: int = 1):
        """Give a user boxes."""

        if box_type not in ("normal", "great", "ultra", "master"):
            return await ctx.send("That's not a valid box type!")

        await self.bot.mongo.update_member(
            user,
            {
                "$set": {"last_voted": datetime.utcnow()},
                "$inc": {f"gifts_{box_type}": amt},
            },
        )

        if amt == 1:
            await ctx.send(f"Gave **{user}** 1 {box_type} box.")
        else:
            await ctx.send(f"Gave **{user}** {amt} {box_type} boxes.")

    @commands.is_owner()
    @admin.command(aliases=("g",))
    async def give(self, ctx, user: FetchUserConverter, *, arg: str):
        """Give a pokémon."""

        shiny = False

        if arg.lower().startswith("shiny"):
            shiny = True
            arg = arg.lower().replace("shiny", "").strip()

        species = self.bot.data.species_by_name(arg)

        if species is None:
            return await ctx.send(f"Could not find a pokemon matching `{arg}`.")

        await self.bot.mongo.db.pokemon.insert_one(
            await self.bot.mongo.make_pokemon(user, species, shiny=shiny)
        )

        await ctx.send(f"Gave **{user}** a {species}.")

    @commands.is_owner()
    @admin.command()
    async def setup(self, ctx, user: FetchUserConverter, num: int = 100):
        """Test setup pokémon."""

        # This is for development purposes.

        pokemon = []
        idx = await self.bot.mongo.fetch_next_idx(user, reserve=num)

        for i in range(num):
            species = self.bot.data.species_by_number(random.randint(1, 905))
            pokemon.append(
                await self.bot.mongo.make_pokemon(user, species, idx=idx+i)
            )

        await self.bot.mongo.db.pokemon.insert_many(pokemon)
        await ctx.send(f"Gave **{user}** {num} pokémon.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Administration(bot))
