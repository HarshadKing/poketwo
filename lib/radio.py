import discord


class RadioGroup:
    """A group of buttons that can be selected, with one selected at a time.
    Parameters
    ----------
    default_style : discord.ButtonStyle
        The style of the buttons when not selected.
    selected_style : discord.ButtonStyle
        The style of the buttons when selected.
    allow_deselect : bool
        Whether buttons can be deselected by clicking them again.
    """

    class Button(discord.ui.Button):
        def __init__(self, *, group: "RadioGroup", label: str, value: str):
            super().__init__(label=label, style=group.default_style)
            self.value = value
            self.group = group

        async def callback(self, interaction: discord.Interaction):
            await self.group.callback(interaction, self)

    def __init__(
        self,
        default_style: discord.ButtonStyle = discord.ButtonStyle.gray,
        selected_style: discord.ButtonStyle = discord.ButtonStyle.blurple,
        allow_deselect: bool = False,
    ):
        self.default_style = default_style
        self.selected_style = selected_style
        self.allow_deselect = allow_deselect
        self._selected = None
        self._buttons = []

    @property
    def selected(self):
        if self._selected is None:
            return None
        return self._selected.value

    def select(self, button: Button):
        if self._selected is not None:
            self._selected.style = self.default_style
        if button is not None:
            button.style = self.selected_style
        self._selected = button

    def add_option(self, label: str, value: str, *, is_selected: bool = False, emoji: str = None) -> Button:
        button = self.Button(label=label, group=self, value=value)
        if emoji:
            button.emoji = emoji
        self._buttons.append(button)
        if is_selected:
            self.select(button)
        return button

    def add_to_view(self, view: discord.ui.View):
        for button in self._buttons:
            view.add_item(button)

    def callback(self, interaction: discord.Interaction, button: Button):
        if button is self._selected and self.allow_deselect:
            self.select(None)
        else:
            self.select(button)
