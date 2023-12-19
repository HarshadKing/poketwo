from __future__ import annotations
import asyncio
from functools import cached_property
import math
import contextlib

from datetime import datetime, timedelta
import itertools
import random
import textwrap
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union
import uuid

import discord
from discord.ext import commands, tasks
import humanfriendly

from cogs import mongo
from cogs.mongo import Member, PokemonBase
from data.models import Species
from helpers import checks, pagination
from helpers.context import PoketwoContext
from helpers.converters import FetchUserConverter
from helpers.utils import FlavorString
from lib.probability import random_iv_composition

if TYPE_CHECKING:
    from bot import ClusterBot

# GENERAL

CHRISTMAS_PREFIX = "christmas_2023_"
BADGE_NAME = "christmas_2023"
IV_REWARD = 75
EMBED_COLOR = 0x418DD0


class FlavorStrings:
    """Holds various flavor strings."""

    pokeexpress = FlavorString("The Poké Express")
    pokepass = FlavorString("Poképass")

    pokecoins = FlavorString("Pokécoins", "<:pokecoins:1185296751012356126>")
    event_pokemon = FlavorString("Event Pokémon")
    shards = FlavorString("Shards", "<:shards:1185296789918728263>")
    redeem = FlavorString("Redeem")
    iv_pokemon = FlavorString("IV Pokémon", "<:present_green:1185312793948332062> ")
    mythical = FlavorString("Mythical Pokémon", "<:present_red:1185312798343962794> ")
    ub = FlavorString("Ultra Beast", "<:present_yellow:1185312800596308048>")
    legendary = FlavorString("Legendary Pokémon", "<:present_purple:1185312796854980719>")
    present = FlavorString("Christmas Present", "<:present_blue:1186054091617619968>")
    badge = FlavorString("Christmas 2023 Badge", "<:badge_christmas_2023:1185512567716708435>")


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
REGIONS = ("kanto", "johto", "hoenn", "sinnoh", "unova", "kalos", "alola", "galar", "paldea", "hisui")
RARITIES = ("mythical", "legendary", "ub")
FORMS = ("alolan", "galarian", "hisuian")


## COMMAND STRINGS
CMD_CHRISTMAS = "`{0} christmas`"
CMD_REWARDS = "`{0} christmas rewards`"
CMD_MINIGAMES = "`{0} christmas minigames`"
CMD_TOGGLE_NOTIFICATIONS = "`{0} christmas minigames toggle`"
CMD_OPEN = "`{0} christmas open [qty=1]`"


## EVENT POKEMON IDS
EVENT_SMOLLIV = 50152
EVENT_VAROOM = 50151
EVENT_DRAGONITE = 50148
EVENT_DOLLIV = 50153
EVENT_PLUSLE_MINUN = 50149
EVENT_ARBOLIVA = 50154
EVENT_COSMOG = 50150


# POKEPASS

XP_ID = f"{CHRISTMAS_PREFIX}xp"
LEVEL_ID = f"{CHRISTMAS_PREFIX}level"

PASS_REWARDS = {
    1: {"reward": "event_pokemon", "id": EVENT_SMOLLIV},
    2: {"reward": "pokecoins", "amount": 2000},
    3: {"reward": "iv_pokemon"},
    4: {"reward": "pokecoins", "amount": 2000},
    5: {"reward": "shards", "amount": 125},
    6: {"reward": "pokecoins", "amount": 2000},
    7: {"reward": "pokecoins", "amount": 2000},
    8: {"reward": "rarity_pokemon", "rarity": "mythical", "amount": 5},
    9: {"reward": "pokecoins", "amount": 2000},
    10: {"reward": "event_pokemon", "id": EVENT_VAROOM},
    11: {"reward": "pokecoins", "amount": 2500},
    12: {"reward": "pokecoins", "amount": 2500},
    13: {"reward": "iv_pokemon"},
    14: {"reward": "pokecoins", "amount": 2500},
    15: {"reward": "shards", "amount": 125},
    16: {"reward": "pokecoins", "amount": 2500},
    17: {"reward": "pokecoins", "amount": 2500},
    18: {"reward": "rarity_pokemon", "rarity": "mythical", "amount": 5},
    19: {"reward": "pokecoins", "amount": 2500},
    20: {"reward": "event_pokemon", "id": EVENT_DRAGONITE},
    21: {"reward": "pokecoins", "amount": 3500},
    22: {"reward": "pokecoins", "amount": 3500},
    23: {"reward": "iv_pokemon"},
    24: {"reward": "pokecoins", "amount": 3500},
    25: {"reward": "rarity_pokemon", "rarity": "ub", "amount": 3},
    26: {"reward": "pokecoins", "amount": 3500},
    27: {"reward": "pokecoins", "amount": 3500},
    28: {"reward": "rarity_pokemon", "rarity": "legendary", "amount": 3},
    29: {"reward": "pokecoins", "amount": 3500},
    30: {"reward": "event_pokemon", "id": EVENT_DOLLIV},
    31: {"reward": "pokecoins", "amount": 4000},
    32: {"reward": "pokecoins", "amount": 4000},
    33: {"reward": "iv_pokemon"},
    34: {"reward": "pokecoins", "amount": 4000},
    35: {"reward": "shards", "amount": 125},
    36: {"reward": "pokecoins", "amount": 4000},
    37: {"reward": "pokecoins", "amount": 4000},
    38: {"reward": "rarity_pokemon", "rarity": "ub", "amount": 5},
    39: {"reward": "pokecoins", "amount": 4000},
    40: {"reward": "event_pokemon", "id": EVENT_PLUSLE_MINUN},
    41: {"reward": "pokecoins", "amount": 5000},
    42: {"reward": "pokecoins", "amount": 5000},
    43: {"reward": "iv_pokemon"},
    44: {"reward": "pokecoins", "amount": 5000},
    45: {"reward": "shards", "amount": 125},
    46: {"reward": "pokecoins", "amount": 5000},
    47: {"reward": "pokecoins", "amount": 5000},
    48: {"reward": "rarity_pokemon", "rarity": "legendary", "amount": 5},
    49: {"reward": "pokecoins", "amount": 5000},
    50: {"reward": "event_pokemon", "id": EVENT_ARBOLIVA, "badge": True},
}

XP_REQUIREMENT = {"base": 1000, "extra": 500}


# PRESENTS

PRESENTS_ID = f"{CHRISTMAS_PREFIX}presents"

# TODO: FINALIZE CHANCES
PRESENT_CHANCES = {
    "pokecoins": 0.25,
    "shards": 0.095,
    "redeems": 0.005,
    "event_pokemon": 0.48,
    "rarity_pokemon": 0.085,
    "iv_pokemon": 0.085,
}
PRESENT_REWARD_AMOUNTS = {
    "pokecoins": range(2000, 4000),
    "shards": range(10, 40),
    "redeems": [1],
    "event_pokemon": [1],
    "rarity_pokemon": [1],
    "iv_pokemon": [1],
}

EVENT_CHANCES = {
    # These have been separated for ease of use
    EVENT_VAROOM: 0.11 / PRESENT_CHANCES["event_pokemon"],
    EVENT_SMOLLIV: 0.096 / PRESENT_CHANCES["event_pokemon"],
    EVENT_DRAGONITE: 0.096 / PRESENT_CHANCES["event_pokemon"],
    EVENT_DOLLIV: 0.072 / PRESENT_CHANCES["event_pokemon"],
    EVENT_PLUSLE_MINUN: 0.068 / PRESENT_CHANCES["event_pokemon"],
    EVENT_ARBOLIVA: 0.038 / PRESENT_CHANCES["event_pokemon"],
    EVENT_COSMOG: 0.01 / PRESENT_CHANCES["event_pokemon"],
}
EVENT_REWARDS = [*EVENT_CHANCES.keys()]
EVENT_WEIGHTS = [*EVENT_CHANCES.values()]

PRESENT_REWARDS = [*PRESENT_CHANCES.keys()]
PRESENT_WEIGHTS = [*PRESENT_CHANCES.values()]


# QUESTS

QUESTS_ID = f"{CHRISTMAS_PREFIX}quests"
QUESTS_NOTIFY_ID = f"{CHRISTMAS_PREFIX}quests_notify"

QUEST_REWARDS = {"daily": 1100, "weekly": 2800, "catch": 1}


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
            description = f"Spend {count} {FlavorStrings.pokecoins:!e} on the market"

        case "market_sell":
            description = f"Earn {count} {FlavorStrings.pokecoins:!e} from the market"

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
    """Function to make a quest with any event, range of count and conditions."""

    return lambda: {
        "event": event,
        "count": random.choice(count_range),
        "condition": {k: v() if callable(v) else v for k, v in condition.items()},
    }


DAILY_QUESTS = {
    make_quest("catch", range(20, 31)): 15,  # Any catch quest
    make_quest("catch", range(10, 21), type=lambda: random.choice(TYPES)): 15,  # Type pokemon quests
    make_quest(
        "catch", range(10, 21), region=lambda: random.choice(REGIONS[:-1])
    ): 9,  # Region pokemon quests except hisui
    make_quest("catch", range(1, 3), region="hisui"): 1,  # Hisui region pokemon quest
    make_quest("catch", range(5, 11), rarity="event"): 10,  # Event pokemon quests
    make_quest("catch", range(10, 21), rarity="paradox"): 5,  # Paradox pokemon quests
    make_quest("market_buy", [500, 1000]): 5,  # Market Purchase quest
    make_quest("market_sell", [500, 1000]): 10,  # Market Sale quest
    make_quest("open_box", range(1, 2)): 10,  # Voting box quest
    make_quest("trade", range(3, 6)): 5,  # Trading quest
    make_quest("battle_start", range(1, 4), type=lambda: random.choice(TYPES)): 10,  # Battling with certain types quest
    make_quest("release", range(5, 11)): 5,  # Releasing quest
}

WEEKLY_QUESTS = {
    make_quest("catch", range(60, 71)): 15,  # Any catch quest
    make_quest("catch", range(40, 61), type=lambda: random.choice(TYPES)): 10,  # Type pokemon quests
    make_quest("catch", range(50, 61), region="paldea"): 0.5,  # Paldea region pokemon quest
    make_quest(
        "catch", range(40, 51), region=lambda: random.choice(("kanto", "johto", "hoenn", "unova"))
    ): 2,  # Group 1 region pokemon quests
    make_quest(
        "catch", range(30, 41), region=lambda: random.choice(("sinnoh", "alola", "kalos", "galar"))
    ): 2,  # Group 2 region pokemon quests
    make_quest("catch", range(5, 11), region="hisui"): 0.5,  # Hisui region pokemon quest
    make_quest("catch", range(1, 4), rarity=lambda: random.choice(RARITIES)): 15,  # Rare pokemon quests
    make_quest("catch", range(1, 4), form=lambda: random.choice(FORMS)): 10,  # Regional form pokemon quests
    make_quest("catch", range(15, 26), rarity="event"): 5,  # Event pokemon quests
    make_quest("market_buy", [4000, 5000, 5500]): 10,  # Market Purchase quest
    make_quest("market_sell", [4000, 5000, 5500]): 10,  # Market Sale quest
    make_quest("open_box", range(4, 7)): 15,  # Voting box quest
    make_quest(
        "battle_start", range(6, 11), type=lambda: random.choice(TYPES)
    ): 10,  # Battling with certain types quest
}


# MAIN

## Main Menu View for quick access to commands


class ChristmasView(discord.ui.View):
    def __init__(self, ctx: PoketwoContext):
        self.ctx = ctx
        self.cog: Christmas = self.ctx.bot.get_cog("Christmas")
        super().__init__(timeout=120)

    @discord.ui.button(label="Minigames", style=discord.ButtonStyle.blurple)
    async def inventory(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer()
        await self.ctx.invoke(self.cog.minigames)

    @discord.ui.button(label="All Rewards", style=discord.ButtonStyle.green)
    async def milestones(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.response.defer()
        await self.ctx.invoke(self.cog.rewards)

    async def interaction_check(self, interaction):
        if interaction.user.id not in {
            self.ctx.bot.owner_id,
            self.ctx.author.id,
            *self.ctx.bot.owner_ids,
        }:
            await interaction.response.send_message("You can't use this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            await self.message.edit(view=self)


## Main Cog


class Christmas(commands.Cog):
    """Christmas event commands."""

    def __init__(self, bot):
        self.bot: ClusterBot = bot
        if self.bot.cluster_idx == 0:
            self.notify_quests.start()

    # GENERAL

    async def cog_load(self):
        self.bot.Embed.CUSTOM_COLOR = EMBED_COLOR  # Set custom embed color for this event

    async def cog_unload(self):
        self.bot.Embed.CUSTOM_COLOR = None  # Unset custom embed color
        if self.bot.cluster_idx == 0:
            self.notify_quests.cancel()

    @cached_property
    def pools(self) -> Dict[str, List[Species]]:
        p = {
            "event_pokemon": EVENT_REWARDS,
            "rarity_pokemon": self.bot.data.list_mythical + self.bot.data.list_legendary + self.bot.data.list_ub,
            "ub": self.bot.data.list_ub,
            "legendary": self.bot.data.list_legendary,
            "mythical": self.bot.data.list_mythical,
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
        """Function to build a pokémon."""

        ivs = [mongo.random_iv() for _ in range(6)]
        if minimum_iv_percent:
            ivs = random_iv_composition(sum_lower_bound=math.ceil(minimum_iv_percent / 100 * 186))

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

    async def make_reward_pokemon(
        self,
        reward: str,
        user: discord.User | discord.Member,
        member: Member,
    ) -> PokemonBase:
        """Function to build specific kinds of pokémon."""

        shiny_boost = 1
        minimum_iv_percent = 0
        match reward:
            case "event_pokemon":
                population = self.pools["event_pokemon"]
                weights = EVENT_CHANCES
                shiny_boost = 10
            case "rarity_pokemon" | "ub" | "legendary" | "mythical":
                pool = [x for x in self.pools[reward] if x.catchable]
                population = pool
                weights = [x.abundance for x in pool]
            case "iv_pokemon":
                pool = [x for x in self.pools["non-event"] if x.catchable]
                population = pool
                weights = [x.abundance for x in pool]
                minimum_iv_percent = IV_REWARD

        species = random.choices(population, weights, k=1)[0]
        return await self.make_pokemon(
            user,
            member,
            species=species,
            shiny_boost=shiny_boost,
            minimum_iv_percent=minimum_iv_percent,
        )

    # POKEPASS

    ## Commands

    @checks.has_started()
    @commands.group(aliases=("event", "ev"), invoke_without_command=True, case_insensitive=True)
    async def christmas(self, ctx: PoketwoContext):
        """Christmas event main menu. Contains Poképass details and presents inventory."""

        prefix = ctx.clean_prefix.strip()
        embed = self.bot.Embed(
            title=f"All Aboard {FlavorStrings.pokeexpress}!",
            description=textwrap.dedent(
                f"""
                All aboard {FlavorStrings.pokeexpress}, where adventure awaits and joyous cheer fills the air! As the frosty winds whistle through the forests and hills, cosy up inside {FlavorStrings.pokeexpress} with different Pokémon for the most magical journey of all—to the North Pole to see Santa!
                **Progress the journey by playing various minigames and completing {FlavorStrings.pokepass} levels, collecting gifts and rewards along the way!**
                """
            ),
        )

        ## POKÉPASS VALUES
        member = await self.bot.mongo.fetch_member_info(ctx.author)

        requirement = self.get_xp_requirement(member[LEVEL_ID])

        embed.add_field(name=f"Your {FlavorStrings.pokepass} Level:", value=f"{member[LEVEL_ID]}", inline=False)
        embed.add_field(
            name=f"Your {FlavorStrings.pokepass} XP:", value=f"{member[XP_ID]} / {requirement}", inline=False
        )

        next_level = member[LEVEL_ID] + 1
        if next_level > len(PASS_REWARDS):
            next_reward = f"{FlavorStrings.present.emoji} 1 {FlavorStrings.present:!e}"
        else:
            next_reward = await self.make_reward_text(reward=PASS_REWARDS[next_level])

        embed.add_field(
            name=f"Next {FlavorStrings.pokepass} Reward",
            value=f"{next_reward}",
            inline=False,
        )

        embed.add_field(
            name=f"{FlavorStrings.present:s} — {member[PRESENTS_ID]:,}",
            value=(
                f"Once you've completed the {FlavorStrings.pokepass}, you will receive a present from Santa for every new level you complete! "
                f"These presents can contain any of the different rewards you've received throughout the main levels of the {FlavorStrings.pokepass}.\n"
                f"Use {CMD_OPEN.format(prefix)} to open them!"
                # f"You will earn a present for every {FlavorStrings.pokepass} level you complete after completing the {FlavorStrings.pokepass}!"
                # f" These presents hold the various rewards that were available in the main levels of the {FlavorStrings.pokepass}."
            ),
            inline=False,
        )

        view = ChristmasView(ctx)
        view.message = await ctx.reply(embed=embed, view=view)

    @checks.has_started()
    @christmas.command(
        aliases=("reward", "r"),
        invoke_without_command=True,
        case_insensitive=True,
    )
    async def rewards(self, ctx: PoketwoContext):
        """View all the rewards obtainable from the Poképass."""

        member = await self.bot.mongo.fetch_member_info(ctx.author)
        level = member[LEVEL_ID]

        async def get_page(source, menu, pidx):
            pgstart = pidx * 10
            pgend = min(pgstart + 10, len(PASS_REWARDS))

            # Send embed
            description = ""
            for reward in list(PASS_REWARDS.items())[pgstart:pgend]:
                text = await self.make_reward_text(reward=reward[1], number=reward[0])
                description += (text if reward[0] <= level else f"**{text}**") + "\n"

            embed = self.bot.Embed(title=f"Poképass Rewards", description=description)
            embed.set_footer(text=f"Showing {pgstart + 1}–{pgend} out of {len(PASS_REWARDS)}.")
            embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
            return embed

        pages = pagination.ContinuablePages(pagination.FunctionPageSource(5, get_page))
        self.bot.menus[ctx.author.id] = pages
        await pages.start(ctx)

    @commands.is_owner()
    @christmas.command(aliases=("debug", "d"), usage="<type> [qty=1]")
    async def debugging(self, ctx: PoketwoContext, type, qty: int):
        """Admin-only debugging command to grant XP and Levels."""

        if type == "xp":
            await self.give_xp(ctx.author, amount=qty)
            await ctx.send(f"Gave {ctx.author.name} {qty} XP!")
        if type in ["lvl", "level"]:
            await self.bot.mongo.update_member(ctx.author, {"$set": {LEVEL_ID: qty}})
            await ctx.send(f"Set {ctx.author.name}'s level to {qty}!")

    ## Utils

    async def make_reward_text(self, reward, number=None):
        """Function to build the text for a Poképass reward."""

        level_text = ""
        amount = reward.get("amount", 1)
        if reward["reward"] == "iv_pokemon":
            flavor = FlavorStrings.iv_pokemon
            reward_text = f"{flavor.emoji} {amount} {IV_REWARD}+ {flavor:!e}"

        elif reward["reward"] == "rarity_pokemon":
            flavor = getattr(FlavorStrings, reward["rarity"])
            reward_text = f"{flavor.emoji} {amount} {flavor:!e}"

        elif reward["reward"] == "event_pokemon":
            species = self.bot.data.species_by_number(reward["id"])
            reward_text = f"{self.bot.sprites.get(species.dex_number)} {amount} {species}"
            if "badge" in reward:
                reward_text += f" & {FlavorStrings.badge}"
        else:
            flavor = getattr(FlavorStrings, reward["reward"])
            reward_text = f"{flavor.emoji} {amount} {flavor:!e}"

        if number != None:
            if number < 10:
                level_text = f"` {number}:`"
            else:
                level_text = f"`{number}:`"

        return f"{level_text}　{reward_text}"

    async def give_badge(self, member: Member):
        """Function to give a user the christmas badge."""

        if member.badges.get(BADGE_NAME):
            return
        await self.bot.mongo.update_member(member, {"$set": {f"badges.{BADGE_NAME}": True}})

    async def give_reward(self, user: discord.User | discord.Member, member: Member, level):
        """Function to give a user rewards from the Poképass according to their level"""

        reward = PASS_REWARDS[level] if level <= len(PASS_REWARDS) else {"reward": "present", "amount": 1}
        match reward["reward"]:
            case "pokecoins":
                await self.bot.mongo.update_member(member, {"$inc": {"balance": reward["amount"]}})
                return await self.make_reward_text(reward=reward)
            case "shards":
                await self.bot.mongo.update_member(member, {"$inc": {"premium_balance": reward["amount"]}})
                return await self.make_reward_text(reward=reward)
            case "event_pokemon" | "rarity_pokemon" | "iv_pokemon":
                text = [await self.make_reward_text(reward)]
                if reward.get("id"):
                    pokemon = await self.make_pokemon(
                        user, member, species=self.bot.data.species_by_number(reward["id"])
                    )
                    await self.bot.mongo.db.pokemon.insert_one(pokemon)
                    pokemon_obj = self.bot.mongo.Pokemon.build_from_mongo(pokemon)
                    text.append(f"- {pokemon_obj:liP}")
                else:
                    count = reward.get("amount", 1)
                    # Pass in the rarity if the reward is a rare pokemon, otherwise just the reward
                    inserts = [
                        await self.make_reward_pokemon(reward.get("rarity", reward["reward"]), user, member)
                        for i in range(count)
                    ]

                    await self.bot.mongo.db.pokemon.insert_many(inserts)
                    for pokemon in inserts:
                        pokemon_obj = self.bot.mongo.Pokemon.build_from_mongo(pokemon)
                        text.append(f"- {pokemon_obj:liP}")

                if reward.get("badge"):
                    await self.give_badge(member)
                    text.append(f"- {FlavorStrings.badge}")

                return "\n".join(text)
            case "present":
                await self.bot.mongo.update_member(member, {"$inc": {PRESENTS_ID: 1}})
                return await self.make_reward_text(reward=reward)

    async def reward_level_up(self, user: discord.User | discord.Member, member: Member, level: int):
        """Function to level a user up and DM the message along with rewards earned."""

        embed = self.bot.Embed(
            title=f"Congratulations, you leveled up to {FlavorStrings.pokepass} level {level}!",
            description=f"",
        )

        embed.add_field(name="Your rewards:", value=await self.give_reward(user, member, level))

        await self.bot.send_dm(user, embed=embed)

    def get_xp_requirement(self, level: int):
        return XP_REQUIREMENT["base"] if level < len(PASS_REWARDS) else XP_REQUIREMENT["extra"]

    async def give_xp(self, user: discord.User, amount):
        """Function to give xp to a user and level up if requirements met."""

        member = await self.bot.mongo.fetch_member_info(user)
        member_xp = member[XP_ID]
        member_level = member[LEVEL_ID]

        new_xp = member_xp + amount
        new_level = member_level

        requirement = self.get_xp_requirement(new_level)
        while new_xp >= requirement:
            # While xp is larger than requirement, level up and lower xp
            # and at the same time update the requirement in case it changes
            # based on the new level.
            new_level += 1
            new_xp -= requirement
            requirement = self.get_xp_requirement(new_level)

        update = {"$inc": {XP_ID: new_xp - member_xp}}
        if new_level > member_level:
            update["$inc"][LEVEL_ID] = new_level - member_level

        await self.bot.mongo.db.member.find_one_and_update({"_id": member.id}, update)
        await self.bot.redis.hdel(f"db:member", int(member.id))

        # Send the DMs after updating
        if new_level > member_level:
            for l in range(member_level + 1, new_level + 1):
                await self.reward_level_up(user, member, l)

    ## Event handlers

    @commands.Cog.listener("on_catch")
    async def xp_per_catch(self, ctx, species, id):
        # Giving XP this way may lead to race conditions?
        await self.give_xp(ctx.author, QUEST_REWARDS["catch"])

    # PRESENTS

    ## Commands

    @checks.has_started()
    @christmas.command(aliases=("o",))
    async def open(self, ctx: PoketwoContext, qty: Optional[int] = 1):
        """Command to open presents. Max qty at a time is 15."""

        if qty <= 0:
            return await ctx.send(f"Nice try...")
        elif qty > 15:
            return await ctx.send(f"You can only open up to 15 {FlavorStrings.present:s!e} at once!")

        member = await self.bot.mongo.fetch_member_info(ctx.author)

        presents = member[PRESENTS_ID]

        if presents < qty:
            return await ctx.send(
                f"You don't have enough {FlavorStrings.present:sb}! {FlavorStrings.present:sb!e} are earned for every new level after compeleting the {FlavorStrings.pokepass}."
            )

        # GO
        await self.bot.mongo.update_member(ctx.author, {"$inc": {PRESENTS_ID: -qty}})

        embed = self.bot.Embed(
            title=f"You open {qty} {FlavorStrings.present:{'s' if qty > 1 else ''}}...",
            description=None,
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)

        update = {"$inc": {"balance": 0, "premium_balance": 0, "redeems": 0}}
        inserts = []
        text = []

        for reward in random.choices(PRESENT_REWARDS, weights=PRESENT_WEIGHTS, k=qty):
            count = random.choice(PRESENT_REWARD_AMOUNTS[reward])

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
                case "event_pokemon" | "rarity_pokemon" | "iv_pokemon":
                    pokemon = await self.make_reward_pokemon(reward, ctx.author, member)
                    pokemon_obj = self.bot.mongo.Pokemon.build_from_mongo(pokemon)
                    text.append(f"- {pokemon_obj:liP}")
                    inserts.append(pokemon)

        await self.bot.mongo.update_member(ctx.author, update)
        if len(inserts) > 0:
            await self.bot.mongo.db.pokemon.insert_many(inserts)

        embed.description = "\n".join(text)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.is_owner()
    @christmas.command(aliases=("givepresent", "gp"))
    async def addpresent(
        self,
        ctx: PoketwoContext,
        user: FetchUserConverter,
        qty: Optional[int] = 1,
    ):
        """Admin-only command to give presents to a user."""

        await self.bot.mongo.update_member(user, {"$inc": {PRESENTS_ID: qty}})
        await ctx.send(f"Gave **{user}** {qty}x {FlavorStrings.present:b}.")

    # QUESTS

    ## Commands

    @checks.has_started()
    @christmas.group(aliases=["mg", "games", "q", "quests"], invoke_without_command=True)
    async def minigames(self, ctx: commands.Context):
        """View Poképass minigames/quests."""

        embed = self.bot.Embed(
            title=f"{FlavorStrings.pokepass} Minigames",
            description=(
                f"Play a diverse selection of minigames and earn XP to level up your {FlavorStrings.pokepass}! "
                f"Traverse {FlavorStrings.pokeexpress}, play a variety of minigames, and collect various rewards along the way!\n\n"
                f"Additionally, you'll earn **{QUEST_REWARDS['catch']}XP** for every pokémon you catch!"
            ),
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)

        all_quests = await self.fetch_quests(ctx.author)

        key = lambda q: q["type"]
        groups = itertools.groupby(sorted(all_quests, key=key), key)  # Group by daily/weekly

        for group, quests in groups:
            expires = None
            value = []
            for q in quests:
                description = get_quest_description(q)

                # Underline the description to represent a progress bar
                dl = list(f"\u200b{description}")
                dl.insert(0, "__")
                dl.insert(max(round(q["progress"] / q["count"] * len(dl)), 2), "__")

                value.append(f"{'`☑`' if q.get('completed') else '`☐`'} {''.join(dl)} `{q['progress']}/{q['count']}`")
                expires = q["expires"]

            timespan = expires - datetime.now()
            ts = f"<t:{int(expires.timestamp())}:{{0}}>"
            embed.add_field(
                name=f"{q['type'].capitalize()} Minigames — {QUEST_REWARDS[q['type']]}XP each",
                value="\n".join(
                    [f"Resets in **{humanfriendly.format_timespan(round(timespan.total_seconds()))}**", *value]
                ),
                inline=False,
            )

        await ctx.reply(embed=embed, mention_author=False)

    @checks.has_started()
    @minigames.command(name="togglenotification", aliases=("toggle",))
    async def toggle_notification(self, ctx: PoketwoContext):
        """Toggle the minigames reset notifications."""

        member = await self.bot.mongo.fetch_member_info(ctx.author)
        notify = member.christmas_2023_quests_notify

        await self.bot.mongo.update_member(ctx.author, {"$set": {QUESTS_NOTIFY_ID: not notify}})
        await ctx.reply(
            f"Turned {'off' if notify else 'on'} notifications for when {FlavorStrings.pokepass} minigames reset!"
        )

    @commands.is_owner()
    @minigames.command()
    async def setprogress(self, ctx: PoketwoContext, index: int, progress: int):
        """Admin-only debugging command to set progress of a quest."""

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

    ## Loop to notify when quests reset

    @tasks.loop(seconds=20)
    async def notify_quests(self):
        quests = self.bot.mongo.Member.find({QUESTS_ID: {"$elemMatch": {"expires": {"$lt": datetime.now()}}}})

        async for member in quests:
            await asyncio.create_task(self.renew_quests(member))
            if member.christmas_2023_quests_notify is not False:
                await asyncio.create_task(
                    self.bot.send_dm(
                        discord.Object(member.id),
                        f"You have new {FlavorStrings.pokepass} minigames available! Use {CMD_MINIGAMES.format('@Pokétwo')} to view them! You can disable this notification using {CMD_TOGGLE_NOTIFICATIONS.format('@Pokétwo')}.",
                    )
                )

    @notify_quests.before_loop
    async def before_notify_loop(self):
        await self.bot.wait_until_ready()

    ## Utils

    async def renew_quests(self, member: Member):
        quests = [q for q in member[QUESTS_ID] if datetime.now() < q["expires"]]

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

    async def fetch_quests(self, user: Union[discord.User, discord.Member]) -> List[Dict[str, Any]]:
        member = await self.bot.mongo.fetch_member_info(user)

        return await self.renew_quests(member)

    async def check_quests(self, user: Union[discord.User, discord.Member]):
        """Function to check for quest completions."""

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
                    await user.send(
                        f"You completed the {FlavorStrings.pokepass} minigame **{get_quest_description(q)}**! You received **{inc_xp}XP**!"
                    )
                    await self.give_xp(user, inc_xp)

    def verify_condition(self, condition: dict, species: Species):
        """Function to verify conditions of a pokemon's species with quest requirements."""

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
        """Function that is called on every event that is received. This checks for valid quests and progresses accordingly."""

        quests = await self.fetch_quests(user)
        if not quests:
            return

        for q in quests:
            if q["event"] != event:
                continue

            if (
                len(to_verify) == 0 or any(self.verify_condition(q.get("condition"), x) for x in to_verify)
            ) and not q.get("completed"):
                await self.bot.mongo.db.member.update_one(
                    {"_id": user.id, f"{QUESTS_ID}._id": q["_id"]},
                    {"$inc": {f"{QUESTS_ID}.$.progress": min(count, q["count"] - q["progress"])}},
                )

        await self.bot.redis.hdel("db:member", user.id)
        await self.check_quests(user)

    ## Event listeners

    @commands.Cog.listener("on_catch")
    async def progress_catch_quests(self, ctx, species, id):
        await self.on_quest_event(ctx.author, "catch", [species])

    @commands.Cog.listener()
    async def on_market_buy(self, user, pokemon):
        await self.on_quest_event(user, "market_buy", [], count=pokemon["market_data"]["price"])
        await self.on_quest_event(
            await self.bot.fetch_user(pokemon["owner_id"]), "market_sell", [], count=pokemon["market_data"]["price"]
        )

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
