from typing import Optional
import discord
import math

from discord.ext import menus
from discord.ext.menus.views import ViewMenuPages

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
    def __init__(self, author, source, species, is_shiny):
        self.author = author
        self.source = source
        self.species = species
        self.shiny = is_shiny
        self.gender = "male"

        super().__init__()
        self.clear_items()
        self.add_correct_buttons()


    def add_correct_buttons(self):
        shiny_button = self.button_shiny
        if self.shiny:
            shiny_button.style = discord.ButtonStyle.green

        self.add_item(shiny_button)

        if self.species.has_gender_differences == 1:
            self.add_item(self.button_male)
            self.add_item(self.button_female)


    @discord.ui.button(label="♂", style=discord.ButtonStyle.blurple)
    async def button_male(self, ctx, button=discord.Button):
        if ctx.user == self.author:
            if self.shiny:
                img = self.species.shiny_image_url
            else:
                img = self.species.image_url
            self.gender = "male"
            await self.switch_dex_gender(ctx, button, discord.ButtonStyle.blurple, 2, img)

    @discord.ui.button(label="♀", style=discord.ButtonStyle.gray)
    async def button_female(self, ctx, button=discord.Button):
        if ctx.user == self.author:
            if self.shiny:
                img = self.species.shiny_image_url_female
            else:
                img = self.species.image_url_female
            self.gender = "female"
            await self.switch_dex_gender(ctx, button, discord.ButtonStyle.red, 1, img)

    @discord.ui.button(label="✨", style=discord.ButtonStyle.gray)
    async def button_shiny(self, ctx, button=discord.Button):
        if ctx.user == self.author:
            match self.shiny:
                case True:
                    if self.gender == "male":
                        img = self.species.image_url
                    else:
                        img = self.species.image_url_female
                    self.shiny = False
                    await self.switch_dex_shiny(ctx, button, discord.ButtonStyle.gray, f"{self.source.title[:-2]}",  img)
                case False:
                    if self.gender == "male":
                        img = self.species.shiny_image_url
                    else:
                        img = self.species.shiny_image_url_female
                    self.shiny = True
                    await self.switch_dex_shiny(ctx, button, discord.ButtonStyle.green, f"{self.source.title} ✨",  img)

    async def switch_dex_shiny(self, ctx: discord.Interaction, button, colour, title, image):
        button.style = colour
        self.source.set_image(url=image)
        self.source.title = title
        return await ctx.response.edit_message(embed=self.source, view=self)

    async def switch_dex_gender(self, ctx : discord.Interaction, button, colour, other_button, image):
        button.style = colour
        button.view.children[other_button].style = discord.ButtonStyle.gray
        self.source.set_image(url=image)
        return await ctx.response.edit_message(embed=self.source, view=self)

    