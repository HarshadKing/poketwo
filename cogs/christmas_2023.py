from __future__ import annotations
from functools import cached_property
import math

import random
from typing import TYPE_CHECKING, Dict, List, Optional

import discord
from discord.ext import commands

from cogs import mongo
from cogs.mongo import Member
from data.models import Species
from helpers import checks, pagination
from helpers.context import PoketwoContext
from helpers.converters import FetchUserConverter
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

XP_REQUIREMENT = {"base": 1000, "extra": 500}
BADGE_NAME = "christmas_2023"


CHRISTMAS_PREFIX = "christmas_2023_"

# TODO: FINALIZE CHANCES
PRESENTS_ID = f"{CHRISTMAS_PREFIX}presents"
PRESENT_CHANCES = {"pc": 0.25, "shards": 0.1, "event": 0.48, "rare": 0.12, "80iv-pokemon": 0.05}
PRESENT_REWARD_AMOUNTS = {
    "pc": range(2000, 4000),
    "shards": range(10, 40),
    "event": [1],
    "rare": [1],
    "80iv-pokemon": [1],
}

EVENT_CHANCES = {
    # These have been separated for ease of use
    965: 0.11 / PRESENT_CHANCES["event"],  # TODO: Train Varoom ID
    928: 0.096 / PRESENT_CHANCES["event"],  # TODO: Christmas Tree Smolliv ID
    149: 0.096 / PRESENT_CHANCES["event"],  # TODO: Conductor Dragonite ID
    929: 0.072 / PRESENT_CHANCES["event"],  # TODO: Christmas Tree Dolliv ID
    311: 0.068 / PRESENT_CHANCES["event"],  # TODO: Pyjama Plusle & Minun ID
    930: 0.038 / PRESENT_CHANCES["event"],  # TODO: Christmas Tree Arboliva ID
    789: 0.01 / PRESENT_CHANCES["event"],  # TODO: Fireworks Cosmog ID
}
EVENT_REWARDS = [*EVENT_CHANCES.keys()]
EVENT_WEIGHTS = [*EVENT_CHANCES.values()]

PRESENT_REWARDS = [*PRESENT_CHANCES.keys()]
PRESENT_WEIGHTS = [*PRESENT_CHANCES.values()]


class FlavorStrings:
    """Holds various flavor strings"""

    pokepass = FlavorString("Poképass")
    pokecoins = FlavorString("Pokécoins", "<:pokecoins:1185296751012356126>")
    event_pokemon = FlavorString("Event Pokémon")
    shards = FlavorString("Shards", "<:shards:1185296789918728263>")
    iv_pokemon = FlavorString("IV Pokémon", "<:present_green:1185312793948332062> ")
    mythical = FlavorString("Mythical Pokémon", "<:present_red:1185312798343962794> ")
    ub = FlavorString("Ultra Beast", "<:present_yellow:1185312800596308048>")
    legendary = FlavorString("Legendary Pokémon", "<:present_purple:1185312796854980719>")
    present = FlavorString("Christmas Present", ":gift:")
    badge = FlavorString("Christmas 2023 Badge", "<:badge_christmas_2023:1185512567716708435>")


# Command strings
CMD_CHRISTMAS = "`{0} christmas`"
CMD_OPEN = "`{0} christmas open [qty=1]`"


class Christmas(commands.Cog):
    """Christmas event commands."""

    def __init__(self, bot):
        self.bot: ClusterBot = bot

    @cached_property
    def pools(self) -> Dict[str, List[Species]]:
        p = {
            "event": EVENT_REWARDS,
            "rare": self.bot.data.list_mythical + self.bot.data.list_legendary + self.bot.data.list_ub,
            "non-event": self.bot.data.pokemon.keys(),
        }
        return {k: [self.bot.data.species_by_number(i) for i in v] for k, v in p.items()}

    async def make_pokemon(
        self,
        owner: discord.User | discord.Member,
        member: Member,
        *,
        species: Species,
        shiny_boost: Optional[int] = 1,
        minimum_iv_percent: Optional[int] = 0,  # Minimum IV percentage 0-100
    ):
        ivs = [mongo.random_iv() for _ in range(6)]
        if minimum_iv_percent:
            min_iv = math.ceil(minimum_iv_percent / 100 * 186)
            while sum(ivs) < min_iv:  # TODO: Use a better method to do this
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

    async def give_badge(self, member: Member):
        if member.badges.get(BADGE_NAME):
            return
        await self.bot.mongo.update_member(member, {"$set": {f"badges.{BADGE_NAME}": True}})

    async def give_reward(self, user: discord.User | discord.Member, member: Member, level):
        reward = PASS_REWARDS[level + 1] if level < len(PASS_REWARDS) else {"reward": "presents", "amount": 1}
        match reward["reward"]:
            case "pokecoins":
                await self.bot.mongo.update_member(member, {"$inc": {"balance": reward["amount"]}})
                return await self.make_reward_text(reward=reward)
            case "shards":
                await self.bot.mongo.update_member(member, {"$inc": {"premium_balance": reward["amount"]}})
                return await self.make_reward_text(reward=reward)
            case "event_pokemon":
                text = ""
                pokemon = await self.make_pokemon(user, member, species=self.bot.data.species_by_number(reward["id"]))

                await self.bot.mongo.db.pokemon.insert_many([pokemon])
                pokemon_obj = self.bot.mongo.Pokemon.build_from_mongo(pokemon)

                text += f"- {pokemon_obj:liP}"

                if level == 50:
                    await self.give_badge(member)
                    text += "\n- Christmas 2023 badge"
                return text

            case "iv_pokemon":
                # TODO: MAKE IV POKEMON FUNCITONALITIES
                return
            case "rarity_pokemon":
                # TODO: MAKE RARITY POKEMON FUNCITONALITIES
                return
            case "presents":
                await self.bot.mongo.update_member(member, {"$inc": {f"{CHRISTMAS_PREFIX}presents": 1}})
                return await self.make_reward_text(reward=reward)

    async def give_xp(self, user: discord.User, amount):
        await self.bot.mongo.update_member(user, {"$inc": {f"{CHRISTMAS_PREFIX}xp": amount}})
        member = await self.bot.mongo.fetch_member_info(user)

        requirement = (
            XP_REQUIREMENT["base"]
            if member[f"{CHRISTMAS_PREFIX}level"] < len(PASS_REWARDS)
            else XP_REQUIREMENT["extra"]
        )
        # Handling level up
        if member[f"{CHRISTMAS_PREFIX}xp"] >= requirement:
            await self.level_up(user, member)

            # If the user gets more than the required xp to level up, give the rest of the xp as awell
            if amount > requirement:
                await self.give_xp(user, amount=amount - requirement)

    async def level_up(self, user: discord.User | discord.Member, member: Member):
        await self.bot.mongo.update_member(
            member, {"$inc": {f"{CHRISTMAS_PREFIX}level": 1}, "$set": {f"{CHRISTMAS_PREFIX}xp": 0}}
        )
        user_level = member[f"{CHRISTMAS_PREFIX}level"] + 1
        embed = self.bot.Embed(
            title=f"Congratulations, You are now level {user_level}!",
            description=f"",
        )

        embed.add_field(
            name="Your rewards:", value=await self.give_reward(user, member, member[f"{CHRISTMAS_PREFIX}level"])
        )

        # await ctx.send(embed=embed)

        await self.bot.send_dm(member, embed=embed)

    async def make_reward_text(self, reward, number=None):
        level_text = ""

        if reward["reward"] == "iv_pokemon":
            iv = reward["amount"]
            flavor = FlavorStrings.iv_pokemon
            reward_text = f"{flavor.emoji} {iv}+ {flavor:!e}"

        elif reward["reward"] == "rarity_pokemon":
            amount = reward["amount"]
            flavor = getattr(FlavorStrings, reward["rarity"])
            reward_text = f"{flavor.emoji} {amount} {flavor:!e}"

        elif reward["reward"] == "event_pokemon":
            species = self.bot.data.species_by_number(reward["id"])
            reward_text = f"{self.bot.sprites.get(species.dex_number)} {species}"
            if "badge" in reward:
                reward_text += f" & {getattr(FlavorStrings, 'badge')}"
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

        requirement = (
            XP_REQUIREMENT["base"]
            if member[f"{CHRISTMAS_PREFIX}level"] < len(PASS_REWARDS)
            else XP_REQUIREMENT["extra"]
        )

        embed.add_field(name="Your Level:", value=f"{member[f'{CHRISTMAS_PREFIX}level']}")
        embed.add_field(name="Your Xp:", value=f"{member[f'{CHRISTMAS_PREFIX}xp']} / {requirement} ")

        next_level = member[f"{CHRISTMAS_PREFIX}level"] + 1
        if next_level > len(PASS_REWARDS):
            next_reward = f"{FlavorStrings.present.emoji} 1 Present"
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
            await self.give_xp(ctx.author, amount=qty)
            await ctx.send(f"Gave {ctx.author.name} {qty} XP!")
        if type in ["lvl", "level"]:
            await self.bot.mongo.update_member(ctx.author, {"$set": {f"{CHRISTMAS_PREFIX}level": qty}})
            await ctx.send(f"Set {ctx.author.name}'s level to {qty}!")

    @checks.has_started()
    @christmas.command(aliases=("inv", "presents", "present"))
    async def inventory(self, ctx: PoketwoContext):
        embed = self.bot.Embed(title=f"Christmas 2023 Presents Inventory")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)

        member = await self.bot.mongo.fetch_member_info(ctx.author)

        prefix = ctx.clean_prefix.strip()
        embed.add_field(
            name=f"{FlavorStrings.present:s} — {member[PRESENTS_ID]:,}",
            value=(
                f"> {CMD_OPEN.format(prefix)}\n"
                f"You will earn a present for every {FlavorStrings.pokepass} level you complete after completing the {FlavorStrings.pokepass}!"
                f" These presents hold the various rewards that were available in the main levels of the {FlavorStrings.pokepass}."
            ),
            inline=False,
        )

        await ctx.send(embed=embed)

    @commands.is_owner()
    @christmas.command(aliases=("givepresent", "gp"))
    async def addpresent(
        self,
        ctx: PoketwoContext,
        user: FetchUserConverter,
        qty: Optional[int] = 1,
    ):
        """Give presents to a user."""

        await self.bot.mongo.update_member(user, {"$inc": {PRESENTS_ID: qty}})
        await ctx.send(f"Gave **{user}** {qty}x {FlavorStrings.present:b}.")

    @checks.has_started()
    @christmas.command()
    async def open(self, ctx: PoketwoContext, qty: Optional[int] = 1):

        if qty <= 0:
            return await ctx.send(f"Nice try...")
        elif qty > 15:
            return await ctx.send(f"You can only open up to 15 {FlavorStrings.present:s!e} at once!")

        member = await self.bot.mongo.fetch_member_info(ctx.author)

        presents = member[PRESENTS_ID]

        if presents < qty:
            return await ctx.send(
                f"You don't have enough {FlavorStrings.present:sb}! {FlavorStrings.present:sb!e} are earned by completing {FlavorStrings.pokepass} levels after completing the {FlavorStrings.pokepass}."
            )

        # GO
        await self.bot.mongo.update_member(ctx.author, {"$inc": {PRESENTS_ID: -qty}})

        embed = self.bot.Embed(
            title=f"You open {qty} {FlavorStrings.present:{'s' if qty > 1 else ''}}...",
            description=None,
        )
        embed.set_author(icon_url=ctx.author.display_avatar.url, name=str(ctx.author))

        update = {"$inc": {"balance": 0, "premium_balance": 0}}
        inserts = []
        text = []

        for reward in random.choices(PRESENT_REWARDS, weights=PRESENT_WEIGHTS, k=qty):
            count = random.choice(PRESENT_REWARD_AMOUNTS[reward])

            match reward:
                case "pc":
                    text.append(f"- {count} {FlavorStrings.pokecoins:!e}")
                    update["$inc"]["balance"] += count
                case "shards":
                    text.append(f"- {count} {FlavorStrings.shards:!e}")
                    update["$inc"]["premium_balance"] += count
                case "event" | "rare" | "80iv-pokemon":
                    shiny_boost = 1
                    minimum_iv_percent = 0
                    match reward:
                        case "event":
                            population = self.pools["event"]
                            weights = EVENT_CHANCES
                            shiny_boost = 20
                        case "rare":
                            pool = [x for x in self.pools["rare"] if x.catchable]
                            population = pool
                            weights = [x.abundance for x in pool]
                        case "80iv-pokemon":
                            pool = [x for x in self.pools["non-event"] if x.catchable]
                            population = pool
                            weights = [x.abundance for x in pool]
                            minimum_iv_percent = 80

                    species = random.choices(population, weights, k=1)[0]
                    # TODO: Finalize shiny boost
                    # TODO: Implement min_iv
                    pokemon = await self.make_pokemon(
                        ctx.author,
                        member,
                        species=species,
                        shiny_boost=shiny_boost,
                        minimum_iv_percent=minimum_iv_percent,
                    )
                    pokemon_obj = self.bot.mongo.Pokemon.build_from_mongo(pokemon)

                    text.append(f"- {pokemon_obj:liP} **({reward.upper()})**")  # TODO: Remove suffix
                    inserts.append(pokemon)

        await self.bot.mongo.update_member(ctx.author, update)
        if len(inserts) > 0:
            await self.bot.mongo.db.pokemon.insert_many(inserts)

        embed.description = "\n".join(text)
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(Christmas(bot))
