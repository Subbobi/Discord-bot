import {
  Client, GatewayIntentBits, REST, Routes,
  SlashCommandBuilder, EmbedBuilder, Events, GuildMember, ChannelType,
} from "discord.js";

const TOKEN = process.env.DISCORD_BOT_TOKEN;
if (!TOKEN) { console.error("[Bot] DISCORD_BOT_TOKEN is not set."); process.exit(1); }

const STAFF_ROLE_NAMES = ["tester","admin","yetkili","moderatör","moderator","staff","test-yetkili","founder","owner"];

const resultsCommand = new SlashCommandBuilder()
  .setName("results").setDescription("Test sonucunu belirli bir kanala gönder")
  .addChannelOption(o => o.setName("kanal").setDescription("Sonucun gönderileceği kanal").addChannelTypes(ChannelType.GuildText).setRequired(true))
  .addUserOption(o => o.setName("oyuncu").setDescription("Test olan Discord üyesi").setRequired(true))
  .addStringOption(o => o.setName("minecraft_nick").setDescription("Minecraft kullanıcı adı").setRequired(true))
  .addStringOption(o => o.setName("kit").setDescription("Test kiti (Beast, Axe, Nethpot...)").setRequired(true))
  .addStringOption(o => o.setName("eski_tier").setDescription("Eski tier (A2, B1, Unranked...)").setRequired(true))
  .addStringOption(o => o.setName("yeni_tier").setDescription("Yeni tier (A1, S3, A2...)").setRequired(true))
  .addStringOption(o => o.setName("durum").setDescription("Maç sonucu").setRequired(true).addChoices(
    {name:"✅ Kazandı",value:"kazandı"},{name:"❌ Kaybetti",value:"kaybetti"},{name:"🤝 Berabere",value:"berabere"}))
  .addStringOption(o => o.setName("skor").setDescription("Skor (3-1, 2-0...)").setRequired(true))
  .addStringOption(o => o.setName("sunucu").setDescription("Sunucu adı").setRequired(true));

async function handleResults(interaction) {
  await interaction.deferReply({ ephemeral: true });
  const guild = interaction.guild;
  if (!guild) { await interaction.editReply("❌ Sadece sunucuda kullanılabilir."); return; }
  const member = interaction.member;
  let isAdmin = false, isStaff = false;
  if (member instanceof GuildMember) {
    isAdmin = member.permissions.has("Administrator");
    isStaff = member.roles.cache.some(r => STAFF_ROLE_NAMES.some(n => r.name.toLowerCase().includes(n)));
  } else { const p = BigInt(member?.permissions ?? "0"); isAdmin = (p & 8n) !== 0n; isStaff = isAdmin; }
  if (!isStaff && !isAdmin) { await interaction.editReply(`❌ Yetkin yok.`); return; }

  const kanal = interaction.options.getChannel("kanal", true);
  const oyuncu = interaction.options.getUser("oyuncu", true);
  const mcNick = interaction.options.getString("minecraft_nick", true);
  const kit = interaction.options.getString("kit", true);
  const eskiTier = interaction.options.getString("eski_tier", true);
  const yeniTier = interaction.options.getString("yeni_tier", true);
  const durum = interaction.options.getString("durum", true);
  const skor = interaction.options.getString("skor", true);
  const sunucu = interaction.options.getString("sunucu", true);

  const durumText = durum==="kazandı"?"✅ Kazandı":durum==="kaybetti"?"❌ Kaybetti":"🤝 Berabere";
  const tierText = eskiTier.toLowerCase()!==yeniTier.toLowerCase()?`~~${eskiTier}~~ → **${yeniTier}**`:`**${yeniTier}** *(değişmedi)*`;

  const embed = new EmbedBuilder()
    .setTitle("🏆 PvpTierlist's Test Results").setColor(0xffa500)
    .setThumbnail(`https://mc-heads.net/avatar/${encodeURIComponent(mcNick)}/64`)
    .addFields(
      {name:"🎯 Tester",value:`<@${interaction.user.id}>`,inline:true},
      {name:"👤 Oyuncu",value:`<@${oyuncu.id}>`,inline:true},
      {name:"\u200B",value:"\u200B",inline:true},
      {name:"🎮 Minecraft Nick",value:`\`${mcNick}\``,inline:true},
      {name:"⚔️ Kit",value:`\`${kit}\``,inline:true},
      {name:"🌐 Sunucu",value:`\`${sunucu}\``,inline:true},
      {name:"📊 Tier",value:tierText,inline:true},
      {name:"🏅 Sonuç",value:durumText,inline:true},
      {name:"🎲 Skor",value:`\`${skor}\``,inline:true})
    .setFooter({text:`Bot Tier System | ${new Date().toLocaleDateString("tr-TR",{day:"2-digit",month:"2-digit",year:"numeric"})}`})
    .setTimestamp();

  try {
    await kanal.send({embeds:[embed]});
    await interaction.editReply(`✅ Sonuç <#${kanal.id}> kanalına gönderildi!`);
  } catch(err) {
    await interaction.editReply(`❌ <#${kanal.id}> kanalına gönderilemedi.`);
  }
}

const client = new Client({intents:[GatewayIntentBits.Guilds]});
client.once(Events.ClientReady, async c => {
  console.log(`[Bot] Logged in as ${c.user.tag}`);
  const rest = new REST().setToken(TOKEN);
  await rest.put(Routes.applicationCommands(c.user.id), {body:[resultsCommand.toJSON()]});
  console.log("[Bot] /results registered ✅");
});
client.on(Events.InteractionCreate, async interaction => {
  if (!interaction.isChatInputCommand() || interaction.commandName !== "results") return;
  try { await handleResults(interaction); } catch(err) {
    try {
      const msg = "❌ Beklenmeyen hata.";
      if (interaction.deferred || interaction.replied) await interaction.editReply(msg);
      else await interaction.reply({content:msg,ephemeral:true});
    } catch {}
  }
});
client.on(Events.Error, err => console.error("[Bot] Error:", err.message));
await client.login(TOKEN);
