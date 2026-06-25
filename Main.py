import discord
import os
from discord.ext import commands
from discord import Embed, Color, Option
from dotenv import load_dotenv

# محاولة قراءة التوكن من Environment Variables أولاً
TOKEN = os.getenv("DISCORD_TOKEN")

# إذا لم يوجد، حاول من ملف .env (للتشغيل المحلي)
if not TOKEN:
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")

# إذا لم يوجد التوكن، أظهر خطأ واضحاً
if not TOKEN:
    raise ValueError(
        "❌ التوكن غير موجود!\n"
        "ضع التوكن في:\n"
        "1. متغير البيئة DISCORD_TOKEN (على المنصة)\n"
        "2. أو ملف .env (للتشغيل المحلي)"
    )

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

# قاعدة بيانات مؤقتة
sections_db = {}  # {section_name: role_name}
message_id = None  # لتخزين ID رسالة الأزرار
channel_id = None  # لتخزين ID الشانل

class RoleButton(discord.ui.Button):
    def __init__(self, label, role_name):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.primary,
            custom_id=f"role_{role_name}"
        )
        self.role_name = role_name

    async def callback(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, name=self.role_name)
        if not role:
            await interaction.response.send_message(
                f"❌ الرتبة `{self.role_name}` غير موجودة.", 
                ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(
                f"✅ تم سحب رتبة **{self.role_name}**", 
                ephemeral=True
            )
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                f"✅ تم منحك رتبة **{self.role_name}**", 
                ephemeral=True
            )

class RoleView(discord.ui.View):
    def __init__(self, sections):
        super().__init__(timeout=None)
        for section_name, role_name in sections.items():
            self.add_item(RoleButton(section_name, role_name))

@bot.event
async def on_ready():
    print(f"✅ MASTER ONLINE | {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="الأقسام | /publish"
        )
    )

# ==================== الأوامر ====================

@bot.slash_command(name="add_section", description="إضافة قسم جديد (بدون إعلان)")
@commands.has_permissions(administrator=True)
async def add_section(
    ctx: discord.ApplicationContext,
    section_name: Option(str, "اسم القسم", required=True),
    role_name: Option(str, "اسم الرتبة الموجودة", required=True)
):
    # التحقق من وجود الرتبة
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.respond(f"❌ الرتبة `{role_name}` غير موجودة.", ephemeral=True)
        return

    if section_name in sections_db:
        await ctx.respond(f"⚠️ القسم `{section_name}` موجود بالفعل.", ephemeral=True)
        return

    sections_db[section_name] = role_name
    await ctx.respond(
        f"✅ تم إضافة القسم **{section_name}** مرتبط بالرتبة `{role_name}`\n"
        f"📌 استخدم `/publish` للإعلان عنه.",
        ephemeral=True
    )
    print(f"[MASTER] تم إضافة: {section_name} → {role_name}")

@bot.slash_command(name="publish", description="الإعلان عن الأقسام الجديدة مع منشن @everyone")
@commands.has_permissions(administrator=True)
async def publish(
    ctx: discord.ApplicationContext,
    announcement: Option(str, "رسالة الإعلان (اختياري)", required=False, default="📢 تم إضافة أقسام جديدة!")
):
    if not sections_db:
        await ctx.respond("❌ لا يوجد أقسام للإعلان عنها. استخدم `/add_section` أولاً.", ephemeral=True)
        return

    # بناء رسالة الإعلان
    embed = Embed(
        title="🚀 **أقسام السيرفر الجديدة**",
        description=(
            f"{announcement}\n\n"
            "اختر القسم المناسب لك واضغط على الزر لتحصل على الرتبة.\n"
            "🔄 **الضغط مرة أخرى** يسحب الرتبة."
        ),
        color=Color.gold()
    )

    # عرض الأقسام
    section_list = "\n".join([
        f"• **{sec}** → رتبة `{role}`" 
        for sec, role in sections_db.items()
    ])
    embed.add_field(
        name="🎯 الأقسام المتاحة",
        value=section_list,
        inline=False
    )
    embed.set_footer(text="MASTER System | إدارة ديناميكية")

    view = RoleView(sections_db)

    # منشن @everyone
    mention = "@everyone"

    # التحقق من وجود رسالة سابقة
    global message_id, channel_id
    
    if message_id and channel_id:
        try:
            # محاولة تعديل الرسالة القديمة
            channel = bot.get_channel(channel_id)
            if channel:
                old_message = await channel.fetch_message(message_id)
                await old_message.edit(content=mention, embed=embed, view=view)
                
                await ctx.respond(
                    f"✅ تم تحديث رسالة الأقسام مع منشن {mention}",
                    ephemeral=True
                )
                return
        except:
            pass  # في حال فشل التعديل، نرسل جديدة

    # إرسال رسالة جديدة (إذا لم توجد قديمة أو فشل التعديل)
    new_message = await ctx.send(content=mention, embed=embed, view=view)
    message_id = new_message.id
    channel_id = ctx.channel.id
    
    await ctx.respond(
        f"✅ تم نشر الإعلان مع منشن {mention}",
        ephemeral=True
    )

@bot.slash_command(name="update_buttons", description="تحديث رسالة الأزرار بدون إعلان")
@commands.has_permissions(administrator=True)
async def update_buttons(ctx: discord.ApplicationContext):
    if not sections_db:
        await ctx.respond("❌ لا يوجد أقسام مسجلة.", ephemeral=True)
        return

    global message_id, channel_id
    
    if not message_id or not channel_id:
        await ctx.respond("❌ لا توجد رسالة أزرار سابقة للتحديث.", ephemeral=True)
        return

    try:
        channel = bot.get_channel(channel_id)
        if not channel:
            await ctx.respond("❌ الشانل غير موجود.", ephemeral=True)
            return

        old_message = await channel.fetch_message(message_id)
        
        # بناء الإيمبد الجديد
        embed = Embed(
            title="🚀 **أقسام السيرفر**",
            description=(
                "اختر القسم المناسب لك واضغط على الزر.\n"
                "🔄 **الضغط مرة أخرى** يسحب الرتبة."
            ),
            color=Color.gold()
        )
        
        section_list = "\n".join([
            f"• **{sec}** → رتبة `{role}`" 
            for sec, role in sections_db.items()
        ])
        embed.add_field(
            name="🎯 الأقسام المتاحة",
            value=section_list,
            inline=False
        )
        embed.set_footer(text="MASTER System | محدث")

        view = RoleView(sections_db)
        await old_message.edit(embed=embed, view=view)
        
        await ctx.respond("✅ تم تحديث رسالة الأزرار بنجاح.", ephemeral=True)
        
    except Exception as e:
        await ctx.respond(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

@bot.slash_command(name="remove_section", description="حذف قسم من النظام")
@commands.has_permissions(administrator=True)
async def remove_section(
    ctx: discord.ApplicationContext,
    section_name: Option(str, "اسم القسم المراد حذفه", required=True)
):
    if section_name not in sections_db:
        await ctx.respond(f"❌ القسم `{section_name}` غير موجود.", ephemeral=True)
        return

    del sections_db[section_name]
    await ctx.respond(f"✅ تم حذف القسم **{section_name}**", ephemeral=True)
    print(f"[MASTER] تم حذف: {section_name}")

@bot.slash_command(name="list_sections", description="عرض جميع الأقسام المسجلة")
@commands.has_permissions(administrator=True)
async def list_sections(ctx: discord.ApplicationContext):
    if not sections_db:
        await ctx.respond("📭 لا توجد أقسام مسجلة حالياً.", ephemeral=True)
        return

    embed = Embed(
        title="📋 قائمة الأقسام",
        color=Color.blue()
    )
    for sec, role in sections_db.items():
        embed.add_field(
            name=sec,
            value=f"رتبة: `{role}`",
            inline=True
        )
    
    await ctx.respond(embed=embed, ephemeral=True)

@bot.slash_command(name="sync_sections", description="مزامنة الرتب المفقودة (إنشاء تلقائي)")
@commands.has_permissions(administrator=True)
async def sync_sections(ctx: discord.ApplicationContext):
    created = []
    for section, role_name in sections_db.items():
        if not discord.utils.get(ctx.guild.roles, name=role_name):
            await ctx.guild.create_role(name=role_name, reason="تم إنشاؤها بواسطة MASTER")
            created.append(role_name)
    
    if created:
        await ctx.respond(f"✅ تم إنشاء الرتب: {', '.join(created)}", ephemeral=True)
    else:
        await ctx.respond("✅ جميع الرتب موجودة مسبقاً.", ephemeral=True)

# ==================== تشغيل البوت ====================
print("🔄 جاري تشغيل البوت...")
bot.run(TOKEN)
