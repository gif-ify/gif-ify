import discord
from discord import app_commands
import aiohttp
import logging
from io import BytesIO
from PIL import Image

DISCORD_TOKEN = ""
CATBOX_URL = "https://catbox.moe/user/api.php"




logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord_bot")

async def upload_to_catbox(file_bytes, filename):
    data = aiohttp.FormData()
    data.add_field("reqtype", "fileupload")
    data.add_field(
        "fileToUpload",
        file_bytes,
        filename=filename,
        content_type="application/octet-stream"
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(CATBOX_URL, data=data) as resp:
            text = await resp.text()

            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}: {text}")

            if not text.startswith("http"):
                raise Exception(f"Catbox error: {text}")

            return text

def convert_to_gif(file_bytes):
    with Image.open(BytesIO(file_bytes)) as im:
        im = im.convert("RGBA")
        gif_bytes = BytesIO()
        im.save(gif_bytes, format="GIF")
        gif_bytes.seek(0)
        return gif_bytes.read()

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        logger.info("Slash commands synced!")

client = MyBot()

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    print('----------------------------')


@client.tree.command(name="gif", description="Convert a image/file to gif.")
@app_commands.describe(
    file="Attach an image/file",
    spoiler="Send the resulting GIF as a spoiler",
    ephemeral="Send the output only visible to you"
)
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def gif(
    interaction: discord.Interaction,
    file: discord.Attachment | None = None,
    link: str | None = None,
    spoiler: bool = False,
    ephemeral: bool = False,
):
    await interaction.response.defer(ephemeral=ephemeral)

    try:

        if file:
            file_bytes = await file.read()
            filename = file.filename

        elif link:
            async with aiohttp.ClientSession() as session:
                async with session.get(link) as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to download link: HTTP {resp.status}")
                    file_bytes = await resp.read()
            filename = link.split("/")[-1]

        else:
            await interaction.followup.send("You must provide a file or a link.")
            return


        if not filename.lower().endswith(".gif"):
            file_bytes = convert_to_gif(file_bytes)
            filename = filename.rsplit(".", 1)[0] + ".gif"

 
        if spoiler:
            filename = "SPOILER_" + filename(".", 1)[0] + ".gif"


        url = await upload_to_catbox(file_bytes, filename)

        if spoiler:
            url = f"||{url}||"

        await interaction.followup.send(url, allowed_mentions=None)  #


    except Exception as e:
        await interaction.followup.send(f"Upload failed:\n`{e}`")

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)

