import discord
from discord.ext import commands
from discord import app_commands
import json
import os

DATA_FILE = "embed_data_store.json"

def load_store():
    if os.path.isfile(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_store(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


class AddButtonModal(discord.ui.Modal, title="Add Embed Button"):
    def __init__(self, message):
        super().__init__()
        self.message = message
        self.label_input = discord.ui.TextInput(label="Button Label", max_length=80)
        self.custom_id_input = discord.ui.TextInput(label="Custom ID", max_length=100)
        self.add_item(self.label_input)
        self.add_item(self.custom_id_input)

    async def on_submit(self, interaction: discord.Interaction):
        store = load_store()
        msg_id = str(self.message.id)
        if msg_id not in store:
            await interaction.response.send_message("Not an editable embed.", ephemeral=True)
            return
        store[msg_id].setdefault("buttons", []).append({
            "label": self.label_input.value,
            "custom_id": self.custom_id_input.value
        })
        save_store(store)
        await interaction.response.send_message("✅ Button added.", ephemeral=True)


class RemoveButtonModal(discord.ui.Modal, title="Remove Embed Button"):
    def __init__(self, message):
        super().__init__()
        self.message = message
        self.custom_id_input = discord.ui.TextInput(label="Custom ID to remove")
        self.add_item(self.custom_id_input)

    async def on_submit(self, interaction: discord.Interaction):
        store = load_store()
        msg_id = str(self.message.id)
        if msg_id not in store:
            await interaction.response.send_message("Not an editable embed.", ephemeral=True)
            return
        buttons = store[msg_id].get("buttons", [])
        store[msg_id]["buttons"] = [b for b in buttons if b.get("custom_id") != self.custom_id_input.value]
        save_store(store)
        await interaction.response.send_message("✅ Button removed.", ephemeral=True)


class AddDropdownModal(discord.ui.Modal, title="Add Dropdown"):
    def __init__(self, message):
        super().__init__()
        self.message = message
        self.custom_id_input = discord.ui.TextInput(label="Custom ID")
        self.placeholder_input = discord.ui.TextInput(label="Placeholder")
        self.add_item(self.custom_id_input)
        self.add_item(self.placeholder_input)

    async def on_submit(self, interaction: discord.Interaction):
        store = load_store()
        msg_id = str(self.message.id)
        if msg_id not in store:
            await interaction.response.send_message("Not an editable embed.", ephemeral=True)
            return
        store[msg_id].setdefault("dropdowns", []).append({
            "custom_id": self.custom_id_input.value,
            "placeholder": self.placeholder_input.value,
            "options": []
        })
        save_store(store)
        await interaction.response.send_message("✅ Dropdown added.", ephemeral=True)


class EmbedContextCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        bot.tree.add_command(app_commands.ContextMenu(
            name="➕ Add Embed Button",
            callback=self.add_button
        ))
        bot.tree.add_command(app_commands.ContextMenu(
            name="❌ Remove Embed Button",
            callback=self.remove_button
        ))
        bot.tree.add_command(app_commands.ContextMenu(
            name="➕ Add Dropdown",
            callback=self.add_dropdown
        ))

    async def add_button(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.send_modal(AddButtonModal(message))

    async def remove_button(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.send_modal(RemoveButtonModal(message))

    async def add_dropdown(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.send_modal(AddDropdownModal(message))


async def setup(bot):
    await bot.add_cog(EmbedContextCommands(bot))
