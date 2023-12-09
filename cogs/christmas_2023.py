from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from cogs import mongo
from cogs.mongo import Member, Pokemon
from data.models import Species
from helpers import checks, pagination
from helpers.context import PoketwoContext
from helpers.converters import ItemAndQuantityConverter
from helpers.utils import FlavorString

if TYPE_CHECKING:
    from bot import ClusterBot

CHRISTMAS_PREFIX = "christmas_2023_"
PASS_REWARDS = {
    1: {"reward": "event_pokemon", "id": 928},
    2: {"reward": "pokecoins", "amount": 2000},
    3: {"reward": "iv_pokemon", "amount": 80},
    4: {"reward": "pokecoins", "amount": 2000},
    5: {"reward": "shards", "amount": 125},
    6: {"reward": "pokecoins", "amount": 2000},
    7: {"reward": "pokecoins", "amount": 2000},
    8: {"reward": "rarity_pokemon", "rarity": "mythical", "amount": 5},
    9: {"reward": "pokecoins", "amount": 2000},
    10: {"reward": "event_pokemon", "id": 965},
    11: {"reward": "pokecoins", "amount": 2500},
    12: {"reward": "pokecoins", "amount": 2500},
    13: {"reward": "iv_pokemon", "amount": 80},
    14: {"reward": "pokecoins", "amount": 2500},
    15: {"reward": "shards", "amount": 125},
    16: {"reward": "pokecoins", "amount": 2500},
    17: {"reward": "pokecoins", "amount": 2500},
    18: {"reward": "rarity_pokemon", "rarity": "mythical", "amount": 5},
    19: {"reward": "pokecoins", "amount": 2500},
    20: {"reward": "event_pokemon", "id": 149},
    21: {"reward": "pokecoins", "amount": 3500},
    22: {"reward": "pokecoins", "amount": 3500},
    23: {"reward": "iv_pokemon", "amount": 80},
    24: {"reward": "pokecoins", "amount": 3500},
    25: {"reward": "rarity_pokemon", "rarity": "ub", "amount": 3},
    26: {"reward": "pokecoins", "amount": 3500},
    27: {"reward": "pokecoins", "amount": 3500},
    28: {"reward": "rarity_pokemon", "rarity": "legendary", "amount": 3},
    29: {"reward": "pokecoins", "amount": 3500},
    30: {"reward": "event_pokemon", "id": 929},
    31: {"reward": "pokecoins", "amount": 4000},
    32: {"reward": "pokecoins", "amount": 4000},
    33: {"reward": "iv_pokemon", "amount": 80},
    34: {"reward": "pokecoins", "amount": 4000},
    35: {"reward": "shards", "amount": 125},
    36: {"reward": "pokecoins", "amount": 4000},
    37: {"reward": "pokecoins", "amount": 4000},
    38: {"reward": "rarity_pokemon", "rarity": "ub", "amount": 1},
    39: {"reward": "pokecoins", "amount": 4000},
    40: {"reward": "event_pokemon", "id": 311},
    41: {"reward": "pokecoins", "amount": 5000},
    42: {"reward": "pokecoins", "amount": 5000},
    43: {"reward": "iv_pokemon", "amount": 80},
    44: {"reward": "pokecoins", "amount": 5000},
    45: {"reward": "shards", "amount": 125},
    46: {"reward": "pokecoins", "amount": 5000},
    47: {"reward": "pokecoins", "amount": 5000},
    48: {"reward": "rarity_pokemon", "rarity": "legendary", "amount": 5},
    49: {"reward": "pokecoins", "amount": 5000},
    50: {"reward": "event_pokemon", "id": 930, "badge": True},
}

XP_REQUIREMENT = 1000
BADGE_NAME = "christmas_2023"


class FlavorStrings:
    """Holds various flavor strings"""

    pokecoins = FlavorString("Pokécoins", "⚾")
    event_pokemon = FlavorString("Event Pokémon", "⚾")
    shards = FlavorString("Shards", "⚾")
    iv_pokemon = FlavorString("IV Pokémon", "⚾")
    mythical = FlavorString("Mythical Pokémon", "⚾")
    ub = FlavorString("Ultra Beast", "⚾")
    legendary = FlavorString("Legendary Pokémon", "⚾")
    presents = FlavorString("Christmas Present", "⚾")


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

    async def give_badge(self, ctx: PoketwoContext):
        user = ctx.author
        member = await self.bot.mongo.fetch_member_info(user)
        if member.badges.get(BADGE_NAME):
            return
        await self.bot.mongo.update_member(user, {"$set": {f"badges.{BADGE_NAME}": True}})

    async def give_reward(self, ctx: PoketwoContext, level):
        member = await self.bot.mongo.fetch_member_info(ctx.author)
        reward = PASS_REWARDS[level] if level <= len(PASS_REWARDS) else {"reward": "presents", "amount": 1}
        match reward["reward"]:
            case "pokecoins":
                await self.bot.mongo.update_member(ctx.author, {"$inc": {"balance": reward["amount"]}})
                return await self.make_reward_text(reward=reward)
            case "shards":
                await self.bot.mongo.update_member(ctx.author, {"$inc": {"premium_balance": reward["amount"]}})
                return await self.make_reward_text(reward=reward)
            case "event_pokemon":
                text = ""
                pokemon = await self.make_pokemon(
                    ctx.author, member, species=self.bot.data.species_by_number(reward["id"])
                )

                await self.bot.mongo.db.pokemon.insert_many([pokemon])
                pokemon_obj = self.bot.mongo.Pokemon.build_from_mongo(pokemon)

                text += f"- {pokemon_obj:liP}"

                if level == 50:
                    await self.give_badge(ctx)
                    text += "\n- Christmas 2023 badge"
                return text

            case "iv_pokemon":
                # TODO: MAKE IV POKEMON FUNCITONALITIES
                return
            case "rarity_pokemon":
                # TODO: MAKE RARITY POKEMON FUNCITONALITIES
                return
            case "presents":
                await self.bot.mongo.update_member(ctx.author, {"$inc": {f"{CHRISTMAS_PREFIX}presents": 1}})
                return await self.make_reward_text(reward=reward)

    async def give_xp(self, ctx: PoketwoContext, amount):
        await self.bot.mongo.update_member(ctx.author, {"$inc": {f"{CHRISTMAS_PREFIX}xp": amount}})
        member = await self.bot.mongo.fetch_member_info(ctx.author)

        # Handling level up
        if member[f"{CHRISTMAS_PREFIX}xp"] >= XP_REQUIREMENT:
            await self.level_up(ctx)

    async def level_up(self, ctx: PoketwoContext):
        await self.bot.mongo.update_member(ctx.author, {"$inc": {f"{CHRISTMAS_PREFIX}level": 1}})
        await self.bot.mongo.update_member(ctx.author, {"$set": {f"{CHRISTMAS_PREFIX}xp": 0}})
        member = await self.bot.mongo.fetch_member_info(ctx.author)
        user_level = member[f"{CHRISTMAS_PREFIX}level"]
        embed = self.bot.Embed(
            title=f"Congratulations, You are now level {user_level}!",
            description=f"",
        )

        embed.add_field(name="Your rewards:", value=await self.give_reward(ctx, member[f"{CHRISTMAS_PREFIX}level"]))

        await ctx.send(embed=embed)

    async def make_reward_text(self, reward, number=None):
        level_text = ""

        if reward["reward"] == "iv_pokemon":
            iv = reward["amount"]
            flavor = FlavorStrings.iv_pokemon
            reward_text = f"{flavor.emoji} {iv}+ {flavor:!e}"

        elif reward["reward"] == "rarity_pokemon":
            reward_text = getattr(FlavorStrings, reward["rarity"])

        elif reward["reward"] == "event_pokemon":
            species = self.bot.data.species_by_number(reward["id"])
            reward_text = f"{self.bot.sprites.get(species.dex_number)} {species}"
        else:
            flavor = getattr(FlavorStrings, reward["reward"])
            reward_text = f"{flavor.emoji} {reward['amount']} {flavor:!e}"

        if number != None:
            if number < 10:
                level_text = f"` {number}:`"
            else:
                level_text = f"`{number}:`"

        return f"{level_text}　{reward_text}"

    @checks.has_started()
    @commands.group(aliases=("event", "ev"), invoke_without_command=True, case_insensitive=True)
    async def christmas(self, ctx: PoketwoContext):
        """View christmas event main menu."""

        embed = self.bot.Embed(title=f"Christmas 2023 - The Poké Express", description="")

        ## POKÉPASS VALUES
        member = await self.bot.mongo.fetch_member_info(ctx.author)

        embed.add_field(name="Your Level:", value=f"{member[f'{CHRISTMAS_PREFIX}level']}")
        embed.add_field(name="Your Xp:", value=f"{member[f'{CHRISTMAS_PREFIX}xp']} / {XP_REQUIREMENT}")

        next_level = member[f"{CHRISTMAS_PREFIX}level"] + 1
        if next_level > len(PASS_REWARDS):
            next_reward = "Christmas Presents"
        else:
            next_reward = await self.make_reward_text(reward=PASS_REWARDS[next_level])

        embed.add_field(
            name=f"Next Reward",
            value=f"{next_reward}",
            inline=False,
        )
        await ctx.send(embed=embed)

    @checks.has_started()
    @christmas.command(
        aliases=("reward", "r"),
        invoke_without_command=True,
        case_insensitive=True,
    )
    async def rewards(self, ctx: PoketwoContext):
        """View all the rewards from the pass menu."""

        async def get_page(source, menu, pidx):
            pgstart = pidx * 10
            pgend = min(pgstart + 10, len(PASS_REWARDS))

            # Send embed
            description = ""
            for reward in list(PASS_REWARDS.items())[pgstart:pgend]:
                description += await self.make_reward_text(reward=reward[1], number=reward[0]) + "\n"

            embed = self.bot.Embed(title=f"Poképass Rewards", description=description)
            embed.set_footer(text=f"Showing {pgstart + 1}–{pgend} out of {len(PASS_REWARDS)}.")
            return embed

        pages = pagination.ContinuablePages(pagination.FunctionPageSource(5, get_page))
        self.bot.menus[ctx.author.id] = pages
        await pages.start(ctx)

    # DEBUGGING COMMAND
    @commands.is_owner()
    @christmas.command(aliases=("debug", "d"), usage="<type> [qty=1]")
    async def debugging(self, ctx: PoketwoContext, type, qty: int):
        if type == "xp":
            await self.give_xp(ctx, amount=qty)
            await ctx.send(f"Gave {ctx.author.name} {qty} XP!")
        if type in ["lvl", "level"]:
            await self.bot.mongo.update_member(ctx.author, {"$set": {f"{CHRISTMAS_PREFIX}level": qty}})
            await ctx.send(f"Set {ctx.author.name}'s level to {qty}!")


async def setup(bot: commands.Bot):
    await bot.add_cog(Christmas(bot))
