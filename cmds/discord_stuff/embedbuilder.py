# Still a WIP command as well, can be used, but has some issues, such as drop-downs or buttons being added

import discord
from discord.ext import commands
import json
import os
import re


DATA_FILE = "embed_data_store.json"
ALLOWED_ROLE_IDS = {} # Allowed role ID that can use this command 
ALERT_CHANNEL_ID = # Not totally sure why this is still here (should be fine empty) 
ALERT_ROLE_ID = # Not totally sure why this is still here (should be fine empty)

def load_embed_data_store():
    if os.path.isfile(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_embed_data_store(store):
    with open(DATA_FILE, "w") as f:
        json.dump(store, f, indent=4)


class EmbedData:
    def __init__(self, data=None):
        data = data or {}
        self.title = data.get("title", "Title")
        self.description = data.get("description", "Description")
        self.color = data.get("color", 0x2ECC71)
        self.thumbnail = data.get("thumbnail")
        self.fields = data.get("fields", [])
        self.buttons = data.get("buttons", [])
        self.dropdowns = data.get("dropdowns", [])

    def to_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "color": self.color,
            "thumbnail": self.thumbnail,
            "fields": self.fields,
            "buttons": self.buttons,
            "dropdowns": self.dropdowns,
        }



class EmbedEditorView(discord.ui.View):
    def __init__(self, embed_data, bot, channel_id=None, message_id=None):
        super().__init__(timeout=None)
        self.embed_data = embed_data
        self.bot = bot
        self.channel_id = channel_id
        self.message_id = message_id

        for bdata in self.embed_data.buttons:
            self.add_item(EmbedButton(bdata['label'], bdata['custom_id'], self))
        for ddata in self.embed_data.dropdowns:
            self.add_item(EmbedDropdown(ddata, self))

        self.add_item(EditTitleButton(self))
        self.add_item(EditDescriptionButton(self))
        self.add_item(EditColorButton(self))
        self.add_item(EditThumbnailButton(self))
        self.add_item(AddFieldButton(self))
        self.add_item(SendEmbedButton(self))
        self.add_item(EditComponentsButton(self))

    async def update_embed(self, interaction: discord.Interaction):
        store = load_embed_data_store()
        store[str(self.message_id)] = {
            "channel_id": self.channel_id,
            "message_id": self.message_id,
            **self.embed_data.to_dict()
        }
        save_embed_data_store(store)

        color_value = self.embed_data.color
        if isinstance(color_value, str):
            try:
                color_value = int(color_value.strip("#"), 16)
            except:
                color_value = 0x2ECC71

        embed = discord.Embed(
            title=self.embed_data.title,
            description=self.embed_data.description,
            color=color_value,
        )
        if self.embed_data.thumbnail:
            embed.set_thumbnail(url=self.embed_data.thumbnail)
        for f in self.embed_data.fields:
            if f.get("name") and f.get("value"):
                embed.add_field(
                    name=f["name"], value=f["value"], inline=f.get("inline", False)
                )
        embed.set_footer(text="Brought to you by Future Crew™")

        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.NotFound:
            alert_channel = self.bot.get_channel(ALERT_CHANNEL_ID)
            if alert_channel:
                await alert_channel.send(
                    f"<@&{ALERT_ROLE_ID}> ❌ Could not update embed in thread "
                    f"(message `{self.message_id}` in channel `{self.channel_id}`). "
                    f"Please re-open the forum post."
                )


class EditTitleButton(discord.ui.Button):
    def __init__(self, parent): super().__init__(label="Edit Title", style=discord.ButtonStyle.primary); self.parent = parent
    async def callback(self, interaction): await interaction.response.send_modal(TextInputModal("Edit Title", "Title", "title", self.parent))

class EditDescriptionButton(discord.ui.Button):
    def __init__(self, parent): super().__init__(label="Edit Description", style=discord.ButtonStyle.primary); self.parent = parent
    async def callback(self, interaction): await interaction.response.send_modal(TextInputModal("Edit Description", "Description", "description", self.parent))

class EditColorButton(discord.ui.Button):
    def __init__(self, parent): super().__init__(label="Edit Color", style=discord.ButtonStyle.primary); self.parent = parent
    async def callback(self, interaction): await interaction.response.send_modal(TextInputModal("Edit Color", "Hex Color (e.g. #ff0000)", "color", self.parent))

class EditThumbnailButton(discord.ui.Button):
    def __init__(self, parent): super().__init__(label="Edit Thumbnail", style=discord.ButtonStyle.primary); self.parent = parent
    async def callback(self, interaction): await interaction.response.send_modal(TextInputModal("Edit Thumbnail", "Thumbnail URL", "thumbnail", self.parent))

class AddFieldButton(discord.ui.Button):
    def __init__(self, parent): super().__init__(label="Add Field", style=discord.ButtonStyle.secondary); self.parent = parent
    async def callback(self, interaction):
        index = len(self.parent.embed_data.fields)
        await interaction.response.send_modal(FieldEditModal(self.parent, index))

class SendEmbedButton(discord.ui.Button):
    def __init__(self, parent): super().__init__(label="Send Embed", style=discord.ButtonStyle.success); self.parent = parent
    async def callback(self, interaction): await interaction.response.send_modal(ChannelInputModal(self.parent))

class EditComponentsButton(discord.ui.Button):
    def __init__(self, parent): super().__init__(label="Edit Buttons/Dropdowns", style=discord.ButtonStyle.secondary); self.parent = parent
    async def callback(self, interaction): await interaction.response.send_modal(ComponentEditorModal(self.parent))


class TextInputModal(discord.ui.Modal):
    def __init__(self, title, label, attribute, parent):
        super().__init__(title=title)
        self.attribute = attribute
        self.parent = parent
        default_val = getattr(parent.embed_data, attribute, "")
        if attribute == "color" and isinstance(default_val, int):
            default_val = f"#{default_val:06x}"
        self.add_item(discord.ui.TextInput(label=label, style=discord.TextStyle.paragraph, default=default_val))
    async def on_submit(self, interaction):
        val = self.children[0].value
        if self.attribute == "color":
            try: val = int(val.strip("#"), 16)
            except: val = 0x2ECC71
        setattr(self.parent.embed_data, self.attribute, val)
        await self.parent.update_embed(interaction)


class FieldEditModal(discord.ui.Modal):
    def __init__(self, parent, index):
        super().__init__(title=f"Edit Field #{index+1}")
        self.parent, self.index = parent, index
        if index >= len(parent.embed_data.fields):
            parent.embed_data.fields.append({"name": "", "value": "", "inline": False})
        field = parent.embed_data.fields[index]
        self.name_input = discord.ui.TextInput(label="Field Name", max_length=256, default=field.get("name", ""))
        self.value_input = discord.ui.TextInput(label="Field Value", style=discord.TextStyle.paragraph, max_length=1024, default=field.get("value", ""))
        self.inline_input = discord.ui.TextInput(label="Inline? (true/false)", max_length=5, default=str(field.get("inline", False)).lower())
        self.add_item(self.name_input); self.add_item(self.value_input); self.add_item(self.inline_input)
    async def on_submit(self, interaction):
        inline = self.inline_input.value.lower() == "true"
        self.parent.embed_data.fields[self.index] = {"name": self.name_input.value, "value": self.value_input.value, "inline": inline}
        await self.parent.update_embed(interaction)


class ChannelInputModal(discord.ui.Modal):
    def __init__(self, parent):
        super().__init__(title="Send Embed to Channel")
        self.parent = parent
        self.add_item(discord.ui.TextInput(
            label="Channel ID, mention, or invite link",
            placeholder="Paste channel ID, mention, or link",
            max_length=200,
            required=True
        ))
    async def on_submit(self, interaction):
        channel_str = self.children[0].value.strip()
        channel = None
        try:
            if channel_str.startswith("<#") and channel_str.endswith(">"):
                channel_id = int(channel_str[2:-1])
            elif "discord.com/channels/" in channel_str:
                match = re.search(r"https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/channels/\d+/(\d+)", channel_str)
                if match: channel_id = int(match.group(1))
                else: raise ValueError()
            else:
                channel_id = int(channel_str)
            channel = self.parent.bot.get_channel(channel_id) or await self.parent.bot.fetch_channel(channel_id)
        except:
            channel = None
        if not channel:
            await interaction.response.send_message("❌ Could not find channel.", ephemeral=True)
            return

        color_val = self.parent.embed_data.color
        if isinstance(color_val, str):
            try: color_val = int(color_val.strip("#"), 16)
            except: color_val = 0x2ECC71
        embed = discord.Embed(title=self.parent.embed_data.title, description=self.parent.embed_data.description, color=color_val)
        if self.parent.embed_data.thumbnail:
            embed.set_thumbnail(url=self.parent.embed_data.thumbnail)
        for f in self.parent.embed_data.fields:
            embed.add_field(name=f.get("name", ""), value=f.get("value", ""), inline=f.get("inline", False))
        embed.set_footer(text="Brought to you by Future Crew™")

        try:
            msg = await channel.send(embed=embed)
            store = load_embed_data_store()
            store[str(msg.id)] = {
                "channel_id": channel.id,
                "message_id": msg.id,
                **self.parent.embed_data.to_dict()
            }
            save_embed_data_store(store)
            await interaction.response.send_message(f"✅ Embed sent to {channel.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to send embed: {e}", ephemeral=True)


class EmbedButton(discord.ui.Button):
    def __init__(self, label, custom_id, parent):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=custom_id)
        self.parent = parent
    async def callback(self, interaction):
        await interaction.response.send_message(f"Button `{self.label}` clicked.", ephemeral=True)


class EmbedDropdown(discord.ui.Select):
    def __init__(self, dropdown_data, parent):
        options = [discord.SelectOption(label=o.get("label",""), description=o.get("description",""), value=o.get("value","")) for o in dropdown_data.get("options", [])]
        super().__init__(placeholder=dropdown_data.get("placeholder","Select an option"), options=options, custom_id=dropdown_data.get("custom_id"))
        self.parent, self.dropdown_data = parent, dropdown_data
    async def callback(self, interaction):
        selection = self.values[0] if self.values else None
        linked_field_text = None
        for option in self.dropdown_data.get("options", []):
            if option.get("value") == selection:
                field_index = option.get("field_index")
                if field_index is not None:
                    try:
                        field_index = int(field_index)
                        field = self.parent.embed_data.fields[field_index]
                        linked_field_text = f"**Linked Field:** {field.get('name', '')} - {field.get('value', '')}"
                    except (IndexError, ValueError):
                        linked_field_text = "Invalid linked field index."
                break
        reply = f"Dropdown `{self.placeholder}` selected: {self.values}"
        if linked_field_text: reply += f"\n{linked_field_text}"
        await interaction.response.send_message(reply, ephemeral=True)


class ComponentEditorModal(discord.ui.Modal):
    def __init__(self, parent):
        super().__init__(title="Edit Components")
        self.parent = parent
        self.add_item(discord.ui.TextInput(
            label="New Button JSON or empty",
            placeholder='{"label": "Test", "custom_id": "test"}',
            required=False, style=discord.TextStyle.paragraph, max_length=1000
        ))
        self.add_item(discord.ui.TextInput(
            label="New Dropdown JSON or empty",
            placeholder='{"custom_id": "dd1", "placeholder": "Pick one", "options": [{"label": "One", "value": "1", "field_index": 0}]}',
            required=False, style=discord.TextStyle.paragraph, max_length=2000
        ))
    async def on_submit(self, interaction):
        btn_json_str, dd_json_str = self.children[0].value.strip(), self.children[1].value.strip()
        changed = False
        if btn_json_str:
            try:
                btn_data = json.loads(btn_json_str)
                if "label" in btn_data and "custom_id" in btn_data:
                    self.parent.embed_data.buttons.append(btn_data)
                    self.parent.add_item(EmbedButton(btn_data["label"], btn_data["custom_id"], self.parent))
                    changed = True
            except Exception as e:
                await interaction.response.send_message(f"Invalid button JSON: {e}", ephemeral=True); return
        if dd_json_str:
            try:
                dd_data = json.loads(dd_json_str)
                if "custom_id" in dd_data and "options" in dd_data:
                    valid = True
                    for opt in dd_data["options"]:
                        if not isinstance(opt, dict) or "label" not in opt or "value" not in opt:
                            valid = False; break
                        if "field_index" in opt:
                            try: int(opt["field_index"])
                            except: valid = False; break
                    if valid:
                        self.parent.embed_data.dropdowns.append(dd_data)
                        self.parent.add_item(EmbedDropdown(dd_data, self.parent))
                        changed = True
                    else:
                        await interaction.response.send_message("Invalid dropdown options.", ephemeral=True); return
            except Exception as e:
                await interaction.response.send_message(f"Invalid dropdown JSON: {e}", ephemeral=True); return
        if changed:
            await self.parent.update_embed(interaction)
            await interaction.response.send_message("Components updated!", ephemeral=True)
        else:
            await interaction.response.send_message("No valid component data provided.", ephemeral=True)


class EmbedEditor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.embed_data_store = load_embed_data_store()

    @commands.hybrid_command(name="editembed")
    @commands.has_any_role(*ALLOWED_ROLE_IDS)
    async def editembed(self, ctx):
        """Create a new editable embed in the current thread/forum post"""
        embed_data = EmbedData()
        view = EmbedEditorView(embed_data, self.bot)
        message = await ctx.send(embed=discord.Embed(title=embed_data.title, description=embed_data.description, color=embed_data.color), view=view)

        view.channel_id, view.message_id = ctx.channel.id, message.id
        self.embed_data_store[str(message.id)] = {
            "channel_id": ctx.channel.id,
            "message_id": message.id,
            **embed_data.to_dict()
        }
        save_embed_data_store(self.embed_data_store)

    @commands.Cog.listener()
    async def on_ready(self):
        """Restore all embeds and re-register views"""
        for msg_id_str, data in self.embed_data_store.items():
            try:
                channel = self.bot.get_channel(data["channel_id"])
                if not channel: continue
                msg = await channel.fetch_message(data["message_id"])
                embed_data = EmbedData(data)
                view = EmbedEditorView(embed_data, self.bot, channel_id=data["channel_id"], message_id=data["message_id"])
                self.bot.add_view(view, message_id=data["message_id"])
                await msg.edit(embed=discord.Embed(
                    title=embed_data.title,
                    description=embed_data.description,
                    color=embed_data.color,
                ), view=view)
            except Exception as e:
                alert_channel = self.bot.get_channel(ALERT_CHANNEL_ID)
                if alert_channel:
                    await alert_channel.send(
                        f"<@&{ALERT_ROLE_ID}> ❌ Could not restore embed `{msg_id_str}` "
                        f"in channel `{data.get('channel_id')}`. Error: {e}"
                    )
                continue


async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedEditor(bot))

