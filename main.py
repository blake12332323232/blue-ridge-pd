import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from datetime import datetime
from flask import Flask
from threading import Thread
import os
TOKEN = os.getenv("TOKEN")

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Online"

def run():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

TOKEN = "MTQ3NDEwOTE4NzkxODM5NzU5NA.GIeneZ.oIuBY88synn7VJxUCI73-PXPro2-qaLka4xVIg"

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Database Setup
conn = sqlite3.connect("management.db")
cursor = conn.cursor()
   
cursor.execute("""
CREATE TABLE IF NOT EXISTS strikes (
    user_id INTEGER,
    moderator TEXT,
    reason TEXT,
    date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS promotions (
    user_id INTEGER,
    promoted_by TEXT,
    old_rank TEXT,
    new_rank TEXT,
    date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS leave_requests (
    user_id INTEGER,
    reason TEXT,
    status TEXT,
    date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS trainings (
    host TEXT,
    attendee TEXT,
    result TEXT,
    date TEXT
)
""")

conn.commit()

# ---------------- READY ---------------- #

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(e)

    bot.add_view(FTOPanel())

    print(f"{bot.user} is online.")

# ---------------- PROMOTE ---------------- #

@bot.tree.command(name="promote", description="Promote a department member")
@app_commands.describe(
    member="Member to promote",
    old_rank="Old rank",
    new_rank="New rank"
)
async def promote(interaction: discord.Interaction,
                  member: discord.Member,
                  old_rank: str,
                  new_rank: str):

    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "You do not have permission.",
            ephemeral=True
        )
        return

    cursor.execute("""
    INSERT INTO promotions VALUES (?, ?, ?, ?, ?)
    """, (
        member.id,
        str(interaction.user),
        old_rank,
        new_rank,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()

    embed = discord.Embed(
        title="Promotion Logged",
        color=discord.Color.green()
    )

    embed.add_field(name="Member", value=member.mention, inline=False)
    embed.add_field(name="Old Rank", value=old_rank, inline=True)
    embed.add_field(name="New Rank", value=new_rank, inline=True)
    embed.add_field(name="Promoted By", value=interaction.user.mention, inline=False)

    await interaction.response.send_message(embed=embed)

# ---------------- STRIKE ---------------- #

@bot.tree.command(name="strike", description="Issue a strike")
@app_commands.describe(
    member="Member receiving strike",
    reason="Reason for strike"
)
async def strike(interaction: discord.Interaction,
                 member: discord.Member,
                 reason: str):

    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "You do not have permission.",
            ephemeral=True
        )
        return

    cursor.execute("""
    INSERT INTO strikes VALUES (?, ?, ?, ?)
    """, (
        member.id,
        str(interaction.user),
        reason,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()

    embed = discord.Embed(
        title="Strike Issued",
        color=discord.Color.red()
    )

    embed.add_field(name="Member", value=member.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)

    await interaction.response.send_message(embed=embed)

# ---------------- LEAVE REQUEST ---------------- #

@bot.tree.command(name="leave", description="Submit a leave request")
@app_commands.describe(reason="Reason for leave")
async def leave(interaction: discord.Interaction, reason: str):

    cursor.execute("""
    INSERT INTO leave_requests VALUES (?, ?, ?, ?)
    """, (
        interaction.user.id,
        reason,
        "Pending",
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()

    embed = discord.Embed(
        title="Leave Request Submitted",
        color=discord.Color.orange()
    )

    embed.add_field(name="Member", value=interaction.user.mention)
    embed.add_field(name="Reason", value=reason)
    embed.add_field(name="Status", value="Pending")

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------------- TRAINING ---------------- #

@bot.tree.command(name="training", description="Log training results")
@app_commands.describe(
    attendee="Training attendee",
    result="Pass or Fail"
)
async def training(interaction: discord.Interaction,
                   attendee: discord.Member,
                   result: str):

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "You do not have permission.",
            ephemeral=True
        )
        return

    cursor.execute("""
    INSERT INTO trainings VALUES (?, ?, ?, ?)
    """, (
        str(interaction.user),
        str(attendee),
        result,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()

    embed = discord.Embed(
        title="Training Logged",
        color=discord.Color.blue()
    )

    embed.add_field(name="Attendee", value=attendee.mention)
    embed.add_field(name="Result", value=result)
    embed.add_field(name="Host", value=interaction.user.mention)

    await interaction.response.send_message(embed=embed)

# ---------------- ACTIVITY CHECK ---------------- #

@bot.tree.command(name="activity", description="Check member activity")
@app_commands.describe(member="Member to check")
async def activity(interaction: discord.Interaction,
                   member: discord.Member):

    strike_count = cursor.execute("""
    SELECT COUNT(*) FROM strikes WHERE user_id = ?
    """, (member.id,)).fetchone()[0]

    promotion_count = cursor.execute("""
    SELECT COUNT(*) FROM promotions WHERE user_id = ?
    """, (member.id,)).fetchone()[0]

    leave_count = cursor.execute("""
    SELECT COUNT(*) FROM leave_requests WHERE user_id = ?
    """, (member.id,)).fetchone()[0]

    embed = discord.Embed(
        title="Department Activity",
        color=discord.Color.gold()
    )

    embed.add_field(name="Member", value=member.mention, inline=False)
    embed.add_field(name="Promotions", value=str(promotion_count))
    embed.add_field(name="Strikes", value=str(strike_count))
    embed.add_field(name="Leave Requests", value=str(leave_count))

    await interaction.response.send_message(embed=embed)

# ADD THIS SECTION UNDER TOKEN

GUILD_ID = 1509015055583281222

# ---------- ROLE IDS ---------- #
# Replace with your actual role IDs

ROLES = {
    "Cadet": 1509015055604121670,
    "Officer": 1509015055616839692,
    "Senior Officer": 1509015055616839693,
    "Corporal": 1509015055616839695,
    "Sergeant": 1509015055616839697,
    "Lieutenant": 1509015055616839699,
    "Captain": 1509015055621165259,
    "Major": 1509015055621165261,
    "Assistant Chief": 1509015055621165262,
    "Deputy Chief": 1509015055621165263,
    "Chief": 1509022921211908279,

    "Trooper Cadet": 1509015055616839691,
    "Trooper": 1509015055616839692,
    "Senior Trooper": 1509015055616839693,

    "FTO": 1509023578073337926,
    "Supervisor": 1509024323677978655,
}

# ---------- TRAINING CHANNEL ---------- #

TRAINING_CHANNEL_ID = 1509015062193508410

# ---------- FTO PANEL ---------- #

class FTOPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Pass Cadet",
        style=discord.ButtonStyle.green,
        custom_id="pass_cadet"
    )
    async def pass_cadet(self, interaction: discord.Interaction, button: discord.ui.Button):

        if ROLES["FTO"] not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message(
                "You are not an FTO.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "Mention the cadet to promote.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Fail Cadet",
        style=discord.ButtonStyle.red,
        custom_id="fail_cadet"
    )
    async def fail_cadet(self, interaction: discord.Interaction, button: discord.ui.Button):

        if ROLES["FTO"] not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message(
                "You are not an FTO.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Cadet Failed Training",
            description=f"Handled by {interaction.user.mention}",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed)

# ---------- TRAINING PANEL COMMAND ---------- #
@bot.tree.command(name="fto-panel", description="Send FTO training panel")
async def fto_panel(interaction: discord.Interaction):

    if ROLES["FTO"] not in [r.id for r in interaction.user.roles]:
        await interaction.response.send_message(
            "You are not an FTO.",
            ephemeral=True
        )
        return

    await interaction.response.defer()  # ✅ prevents 10062

    embed = discord.Embed(
        title="FTO Training Panel",
        description="Use the buttons below to manage cadet training.",
        color=discord.Color.blue()
    )

    await interaction.followup.send(
        embed=embed,
        view=FTOPanel()
    )

# ---------- ROLE PROMOTION SYSTEM ---------- #

@bot.tree.command(name="promote-role", description="Promote a member")
@app_commands.describe(
    member="Member to promote",
    new_rank="New department rank"
)
async def promote_role(
    interaction: discord.Interaction,
    member: discord.Member,
    new_rank: str
):

    allowed = [
        ROLES["Supervisor"],
        ROLES["Lieutenant"],
        ROLES["Captain"],
        ROLES["Major"],
        ROLES["Assistant Chief"],
        ROLES["Deputy Chief"],
        ROLES["Chief"]
    ]

    if not any(role.id in allowed for role in interaction.user.roles):
        await interaction.response.send_message(
            "You cannot use this command.",
            ephemeral=True
        )
        return

    if new_rank not in ROLES:
        await interaction.response.send_message(
            "Invalid rank.",
            ephemeral=True
        )
        return

    # Remove old department roles
    for rank_name, role_id in ROLES.items():
        role = interaction.guild.get_role(role_id)
        if role in member.roles:
            await member.remove_roles(role)

    # Add new role
    new_role = interaction.guild.get_role(ROLES[new_rank])

    await member.add_roles(new_role)

    cursor.execute("""
    INSERT INTO promotions VALUES (?, ?, ?, ?, ?)
    """, (
        member.id,
        str(interaction.user),
        "Previous Rank",
        new_rank,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()

    embed = discord.Embed(
        title="Member Promoted",
        color=discord.Color.green()
    )

    embed.add_field(name="Member", value=member.mention, inline=False)
    embed.add_field(name="New Rank", value=new_rank, inline=False)
    embed.add_field(name="Promoted By", value=interaction.user.mention, inline=False)

    await interaction.response.send_message(embed=embed)

# ---------- DEMOTION SYSTEM ---------- #

@bot.tree.command(name="demote", description="Demote a member")
@app_commands.describe(
    member="Member to demote",
    new_rank="New lower rank"
)
async def demote(
    interaction: discord.Interaction,
    member: discord.Member,
    new_rank: str
):

    if ROLES["Supervisor"] not in [r.id for r in interaction.user.roles]:
        await interaction.response.send_message(
            "No permission.",
            ephemeral=True
        )
        return

    for rank_name, role_id in ROLES.items():
        role = interaction.guild.get_role(role_id)

        if role in member.roles:
            await member.remove_roles(role)

    role = interaction.guild.get_role(ROLES[new_rank])

    await member.add_roles(role)

    embed = discord.Embed(
        title="Member Demoted",
        color=discord.Color.orange()
    )

    embed.add_field(name="Member", value=member.mention)
    embed.add_field(name="New Rank", value=new_rank)
    embed.add_field(name="Handled By", value=interaction.user.mention)

    await interaction.response.send_message(embed=embed)

# ---------- TRAINING CONFIG ---------- #

TRAINING_CATEGORY_ID = 1509015062193508409

active_trainings = {}

# ---------- FTO TRAINING PANEL ---------- #

class TrainingSetupModal(discord.ui.Modal):

    def __init__(self, voice_channel):
        super().__init__(title="Start Training")
        self.voice_channel = voice_channel

        self.duration = discord.ui.TextInput(
            label="Training Duration",
            placeholder="Example: 1 Hour",
            required=True
        )

        self.add_item(self.duration)

    async def on_submit(self, interaction: discord.Interaction):

        training_id = str(interaction.user.id)

        active_trainings[training_id] = {
            "host": interaction.user.id,
            "voice_channel": self.voice_channel.id,
            "duration": self.duration.value,  # ✅ FIXED
            "attendance_locked": False,
            "attendees": []
        }

        embed = discord.Embed(
            title="Training Started",
            color=discord.Color.blue()
        )

        embed.add_field(name="Host", value=interaction.user.mention, inline=False)
        embed.add_field(name="Voice Channel", value=self.voice_channel.mention, inline=False)
        embed.add_field(name="Duration", value=self.duration.value, inline=False)
        embed.add_field(name="Attendance", value="OPEN", inline=False)

        await interaction.response.send_message(
            embed=embed,
            view=TrainingManagementView(training_id)
        )

# ---------- TRAINING MANAGEMENT VIEW ---------- #

# ---------- TRAINING MANAGEMENT VIEW ---------- #

# ---------- TRAINING MANAGEMENT VIEW ---------- #

class TrainingManagementView(discord.ui.View):
    def __init__(self, training_id):
        super().__init__(timeout=None)
        self.training_id = training_id

    # ---------------- JOIN ATTENDANCE ---------------- #
    @discord.ui.button(
        label="Join Attendance",
        style=discord.ButtonStyle.green,
        custom_id="join_attendance"
    )
    async def join_attendance(self, interaction: discord.Interaction, button: discord.ui.Button):

        training = active_trainings.get(self.training_id)

        if not training:
            return await interaction.response.send_message(
                "❌ This training session expired.",
                ephemeral=True
            )

        if training["attendance_locked"]:
            return await interaction.response.send_message(
                "❌ Attendance is locked.",
                ephemeral=True
            )

        vc = interaction.guild.get_channel(training["voice_channel"])

        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(
                "❌ You must be in the training VC.",
                ephemeral=True
            )

        if interaction.user.voice.channel.id != vc.id:
            return await interaction.response.send_message(
                "❌ You are not in the correct training VC.",
                ephemeral=True
            )

        if interaction.user.id not in training["attendees"]:
            training["attendees"].append(interaction.user.id)

        await interaction.response.send_message(
            "✅ Attendance recorded.",
            ephemeral=True
        )

    # ---------------- LOCK ATTENDANCE ---------------- #
    @discord.ui.button(
        label="Lock Attendance",
        style=discord.ButtonStyle.red,
        custom_id="lock_attendance"
    )
    async def lock_attendance(self, interaction: discord.Interaction, button: discord.ui.Button):

        training = active_trainings.get(self.training_id)

        if not training:
            return await interaction.response.send_message(
                "❌ Training session expired.",
                ephemeral=True
            )

        # ONLY HOST CAN LOCK
        if interaction.user.id != training["host"]:
            return await interaction.response.send_message(
                "❌ Only the host can lock attendance.",
                ephemeral=True
            )

        training["attendance_locked"] = True

        vc = interaction.guild.get_channel(training["voice_channel"])

        attendees = []
        for uid in training["attendees"]:
            member = interaction.guild.get_member(uid)
            if member:
                attendees.append(member.mention)

        embed = discord.Embed(
            title="📌 Attendance Locked",
            color=discord.Color.red()
        )

        embed.add_field(name="Host", value=interaction.user.mention, inline=False)
        embed.add_field(name="VC", value=vc.mention if vc else "Unknown", inline=False)
        embed.add_field(name="Duration", value=training["duration"], inline=False)
        embed.add_field(
            name="Attendees",
            value="\n".join(attendees) if attendees else "None",
            inline=False
        )

        # disable old buttons
        for item in self.children:
            item.disabled = True

        # add complete button
        self.add_item(TrainingCompleteButton(self.training_id))

        await interaction.response.edit_message(embed=embed, view=self)
# ---------- TRAINING COMPLETE BUTTON ---------- #

class TrainingCompleteButton(discord.ui.Button):
    def __init__(self, training_id):
        super().__init__(
            label="Training Complete",
            style=discord.ButtonStyle.green,
            custom_id=f"training_complete_{training_id}"
        )
        self.training_id = training_id

    async def callback(self, interaction: discord.Interaction):

        training = active_trainings.get(self.training_id)

        if not training:
            return await interaction.response.send_message(
                "❌ Training expired.",
                ephemeral=True
            )

        if interaction.user.id != training["host"]:
            return await interaction.response.send_message(
                "❌ Only the host can complete this training.",
                ephemeral=True
            )

        attendees = []
        for uid in training["attendees"]:
            member = interaction.guild.get_member(uid)
            if member:
                attendees.append(member.mention)
                try:
                    await member.send(f"You attended training hosted by {interaction.user}.")
                except:
                    pass

        vc = interaction.guild.get_channel(training["voice_channel"])

        embed = discord.Embed(
            title="✅ Training Completed",
            color=discord.Color.green()
        )

        embed.add_field(name="Host", value=interaction.user.mention, inline=False)
        embed.add_field(name="VC", value=vc.mention if vc else "Unknown", inline=False)
        embed.add_field(name="Duration", value=training["duration"], inline=False)
        embed.add_field(
            name="Attendees",
            value="\n".join(attendees) if attendees else "None",
            inline=False
        )

        del active_trainings[self.training_id]

        await interaction.response.edit_message(embed=embed, view=discord.ui.View())
# ---------- VOICE CHANNEL SELECT ---------- #

class TrainingVCSelect(discord.ui.Select):

    def __init__(self, guild):

        options = [
            discord.SelectOption(
                label=vc.name[:100],
                value=str(vc.id)
            )
            for vc in guild.voice_channels
            if vc.category and vc.category.id == TRAINING_CATEGORY_ID
        ]

        options = options[:25]

        if len(options) == 0:
            options = [
                discord.SelectOption(
                    label="No training VC found",
                    value="none"
                )
            ]

        super().__init__(
            placeholder="Select a Training Voice Channel",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        if self.values[0] == "none":
            await interaction.response.send_message(
                "No valid training channels found.",
                ephemeral=True
            )
            return

        vc_id = int(self.values[0])

        voice_channel = interaction.guild.get_channel(vc_id)

        if voice_channel is None:
            await interaction.response.send_message(
                "Invalid voice channel selected.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            TrainingSetupModal(voice_channel)
        )

# ---------- TRAINING START VIEW ---------- #

class TrainingStartView(discord.ui.View):

    def __init__(self, guild):
        super().__init__(timeout=None)

        self.add_item(TrainingVCSelect(guild))

# ---------- START TRAINING COMMAND ---------- #

@bot.tree.command(
    name="start-training",
    description="Start an FTO training session"
)
async def start_training(interaction: discord.Interaction):

    if ROLES["FTO"] not in [r.id for r in interaction.user.roles]:

        await interaction.response.send_message(
            "You are not an FTO.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="FTO Training Setup",
        description="Select the voice channel for the training.",
        color=discord.Color.blue()
    )

    await interaction.response.send_message(
        embed=embed,
        view=TrainingStartView(interaction.guild),
        ephemeral=True
    )

# ---------- GLOBAL APP COMMAND ERROR HANDLER ---------- #

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    print(error)

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                "❌ An error occurred while running the command.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ An error occurred while running the command.",
                ephemeral=True
            )
    except:
        pass
# ---------------- RUN BOT ---------------- #
# /join command
@bot.tree.command(name="join", description="Make the bot join your VC")
async def join(interaction: discord.Interaction):

    # Check if user is in VC
    if not interaction.user.voice:
        await interaction.response.send_message(
            "❌ You must be in a voice channel.",
            ephemeral=True
        )
        return

    channel = interaction.user.voice.channel

    # Move if already connected
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
    else:
        await channel.connect()

    await interaction.response.send_message(
        f"✅ Joined **{channel.name}**"
    )

# /leave command
@bot.tree.command(name="bot-leave", description="Disconnect the bot from VC")
async def leave(interaction: discord.Interaction):

    vc = interaction.guild.voice_client

    if vc:
        await vc.disconnect()
        await interaction.response.send_message("👋 Left the voice channel.")
    else:
        await interaction.response.send_message(
            "❌ I'm not in a voice channel.",
            ephemeral=True
        )
keep_alive()
bot.run(TOKEN)
