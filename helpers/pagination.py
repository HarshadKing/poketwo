from typing import Optional
import discord
import math
from helpers import constants

from discord.ext import menus
from discord.ext.menus.views import ViewMenuPages
from lib import radio

REMOVE_BUTTONS = [
    "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
    "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\ufe0f",
    "\N{BLACK SQUARE FOR STOP}\ufe0f",
]


class FunctionPageSource(menus.PageSource):
    def __init__(self, num_pages, format_page):
        self.num_pages = num_pages
        self.format_page = format_page.__get__(self)

    def is_paginating(self):
        return self.num_pages > 1

    async def get_page(self, page_number):
        return page_number

    def get_max_pages(self):
        return self.num_pages


class AsyncListPageSource(menus.AsyncIteratorPageSource):
    def __init__(
        self,
        data,
        title=None,
        show_index=False,
        prepare_page=lambda self, items: None,
        format_item=str,
        per_page=20,
        count=None,
    ):
        super().__init__(data, per_page=per_page)
        self.title = title
        self.show_index = show_index
        self.prepare_page = prepare_page.__get__(self)
        self.format_item = format_item.__get__(self)
        self.count = count

    def get_max_pages(self):
        if self.count is None:
            return None
        else:
            return math.ceil(self.count / self.per_page)

    async def format_page(self, menu, entries):
        self.prepare_page(entries)
        lines = [
            f"{i+1}. {self.format_item(x)}" if self.show_index else self.format_item(x)
            for i, x in enumerate(entries, start=menu.current_page * self.per_page)
        ]
        start = menu.current_page * self.per_page
        footer = f"Showing entries {start + 1}–{start + len(lines)}"
        if self.count is not None:
            footer += f" out of {self.count}."
        else:
            footer += "."

        embed = menu.ctx.bot.Embed(
            title=self.title,
            description=f"\n".join(lines)[:4096],
        )
        embed.set_footer(text=footer)
        return embed


class ContinuablePages(ViewMenuPages):
    def __init__(self, source, allow_last=True, allow_go=True, **kwargs):
        super().__init__(source, **kwargs, timeout=120)
        self.allow_last = allow_last
        self.allow_go = allow_go
        for x in REMOVE_BUTTONS:
            self.remove_button(x)

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(self.current_page)
        kwargs = await self._get_kwargs_from_page(page)
        return await self.send_with_view(channel, **kwargs)

    async def show_checked_page(self, page_number):
        max_pages = self._source.get_max_pages()
        try:
            if max_pages is None:
                await self.show_page(page_number)
            elif page_number < 0 and not self.allow_last:
                await self.ctx.send(
                    "Sorry, this does not support going to last page. Try sorting in the reverse direction instead."
                )
            else:
                await self.show_page(page_number % max_pages)
        except IndexError:
            pass

    async def continue_at(self, ctx, page, *, channel=None, wait=False):
        self.stop()
        max_pages = self._source.get_max_pages()
        if max_pages is None:
            self.current_page = page
        else:
            self.current_page = page % self._source.get_max_pages()
        self.message = None
        await self.start(ctx, channel=channel, wait=wait)


class DexButtons(discord.ui.View):
    def __init__(self, ctx, embed, species, is_shiny, gender):
        super().__init__()
        self._embed = embed
        self.ctx = ctx
        self.species = species
        if species.has_gender_differences == 1:
            self.gender_select = GenderRadioGroup(self, gender)
            self.gender_select.add_to_view(self)
        else:
            self.gender_select = None
        self.shiny_select = ShinyRadioGroup(self, is_selected=is_shiny)
        self.shiny_select.add_to_view(self)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("You can't use this!", ephemeral=True)
            return False
        return True

    def get_embed(self) -> discord.Embed:
        """Update base embed based on current attributes and return it."""

        # Update title to include sparkles emoji or not
        self._embed.title = f"#{self.species.dex_number} — {self.species}"
        if self.shiny_select.selected:
            self._embed.title += " \N{SPARKLES}"

        # Update image for shiny/gender selection
        image_url = self.species.get_gender_image_url(
            self.shiny_select.selected, "male" if not self.gender_select else self.gender_select.selected
        )
        self._embed.set_image(url=image_url)

        return self._embed

    async def update_embed(self, interaction):
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class GenderRadioGroup(radio.RadioGroup):
    def __init__(self, view: DexButtons, gender):
        super().__init__()
        self.view = view
        male_selected = True if gender == "Male" else False
        self.add_option("", "male", is_selected=male_selected, emoji=constants.GENDER_EMOTES["male"])
        self.add_option("", "female", is_selected=not male_selected, emoji=constants.GENDER_EMOTES["female"])

    async def callback(self, interaction, button):
        super().callback(interaction, button)
        await self.view.update_embed(interaction)


class ShinyRadioGroup(radio.RadioGroup):
    def __init__(self, view: DexButtons, is_selected: bool = False):
        super().__init__(
            default_style=discord.ButtonStyle.red, selected_style=discord.ButtonStyle.green, allow_deselect=True
        )
        self.view = view
        self.add_option("✨", "shiny", is_selected=is_selected)

    @property
    def selected(self):
        # This isn't a normal radio group — it only has one button and
        # we just care about whether it's selected or not.
        return self._selected is not None

    async def callback(self, interaction, button):
        super().callback(interaction, button)
        await self.view.update_embed(interaction)
