const { Client, GatewayIntentBits, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, ChannelType, PermissionsBitField } = require('discord.js');
const fs = require('fs');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers
    ]
});

// Queue ve ayarlar
const queues = new Map(); // guildId -> queue array
const activeTickets = new Map(); // guildId -> active ticket channel
const config = {
    tierlistCategoryId: 'TIERLIST_KATEGORI_ID', // Ticket'ların açılacağı kategori ID'si
    staffRoleId: 'STAFF_ROL_ID', // Staff rolü ID'si
    queueChannelId: 'QUEUE_KANAL_ID' // Queue komutlarının kullanılacağı kanal ID'si
};

client.once('ready', () => {
    console.log(`${client.user.tag} aktif!`);
    client.user.setActivity('Minecraft Tierlist', { type: 'PLAYING' });
});

// Queue başlatma
client.on('messageCreate', async (message) => {
    if (message.author.bot || !message.content.startsWith('!')) return;

    const args = message.content.slice(1).trim().split(/ +/);
    const command = args.shift().toLowerCase();

    if (command === 'queue') {
        const guildId = message.guild.id;
        
        if (!queues.has(guildId)) {
            queues.set(guildId, []);
        }

        const queue = queues.get(guildId);
        const embed = new EmbedBuilder()
            .setTitle('🎮 Minecraft Tierlist Queue')
            .setColor('#00ff00')
            .setDescription(queue.length > 0 ? 
                `**Sıradakiler:**\n${queue.map((user, index) => `**${index + 1}.** ${user}`).join('\n')}` : 
                'Henüz kimse yok!'
            )
            .setFooter({ text: `Sırada: ${queue.length} kişi` });

        const row = new ActionRowBuilder()
            .addComponents(
                new ButtonBuilder()
                    .setCustomId('join_queue')
                    .setLabel('Sıraya Gir')
                    .setStyle(ButtonStyle.Success),
                new ButtonBuilder()
                    .setCustomId('leave_queue')
                    .setLabel('Sıradan Çık')
                    .setStyle(ButtonStyle.Danger)
            );

        await message.reply({ embeds: [embed], components: [row] });
    }
});

// Button interactions
client.on('interactionCreate', async (interaction) => {
    if (!interaction.isButton()) return;

    const guildId = interaction.guild.id;
    
    if (!queues.has(guildId)) {
        queues.set(guildId, []);
    }
    let queue = queues.get(guildId);

    if (interaction.customId === 'join_queue') {
        const userIndex = queue.findIndex(u => u === interaction.user.id);
        
        if (userIndex !== -1) {
            return interaction.reply({ content: '❌ Zaten sıradasın!', ephemeral: true });
        }

        queue.push(interaction.user.id);
        queues.set(guildId, queue);

        await interaction.reply({ content: `✅ Sıraya girdin! (${queue.length}. sıradasın)`, ephemeral: true });
        updateQueueMessage(interaction.guild, interaction.channel);
    }

    if (interaction.customId === 'leave_queue') {
        const userIndex = queue.findIndex(u => u === interaction.user.id);
        
        if (userIndex === -1) {
            return interaction.reply({ content: '❌ Sıraya girmedin ki!', ephemeral: true });
        }

        queue.splice(userIndex, 1);
        queues.set(guildId, queue);

        await interaction.reply({ content: '✅ Sıraya çıktın!', ephemeral: true });
        updateQueueMessage(interaction.guild, interaction.channel);
    }

    if (interaction.customId === 'next_player') {
        if (!checkStaffPermission(interaction.member)) {
            return interaction.reply({ content: '❌ Bu komutu kullanma yetkin yok!', ephemeral: true });
        }

        await processNextPlayer(interaction.guild);
        await interaction.reply({ content: '✅ Sonraki oyuncu çağrıldı!', ephemeral: true });
    }

    if (interaction.customId === 'close_ticket') {
        await interaction.reply({ content: '🎫 Ticket kapatılıyor...' });
        setTimeout(() => {
            interaction.channel.delete();
        }, 2000);
    }
});

// Sonraki oyuncuyu işle
async function processNextPlayer(guild) {
    const guildId = guild.id;
    let queue = queues.get(guildId);

    if (queue.length === 0) return;

    const nextPlayerId = queue.shift();
    queues.set(guildId, queue);

    const nextPlayer = await client.users.fetch(nextPlayerId).catch(() => null);
    if (!nextPlayer) return;

    // Ticket kanalı oluştur
    const ticketChannel = await createTicketChannel(guild, nextPlayer);
    
    // Active ticket kaydet
    activeTickets.set(guildId, ticketChannel.id);

    // Queue güncelle
    updateQueueMessage(guild);
}

// Ticket kanalı oluştur
async function createTicketChannel(guild, player) {
    const category = guild.channels.cache.get(config.tierlistCategoryId);
    if (!category) {
        console.error('Tierlist category bulunamadı!');
        return null;
    }

    const ticketChannel = await guild.channels.create({
        name: `tierlist-${player.username}`,
        type: ChannelType.GuildText,
        parent: config.tierlistCategoryId,
        permissionOverwrites: [
            {
                id: guild.id,
                deny: [PermissionsBitField.Flags.ViewChannel]
            },
            {
                id: player.id,
                allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages]
            },
            {
                id: config.staffRoleId,
                allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages]
            }
        ]
    });

    // Ticket embed'i
    const embed = new EmbedBuilder()
        .setTitle(`🎮 ${player.username} - Minecraft Tierlist`)
        .setDescription(`Merhaba ${player.toString()}!\n\nTierlist yapabilirsin, staff ekibimiz yardımcı olacak!`)
        .setColor('#ffaa00')
        .setThumbnail(player.displayAvatarURL())
        .setTimestamp();

    const row = new ActionRowBuilder()
        .addComponents(
            new ButtonBuilder()
                .setCustomId('close_ticket')
                .setLabel('Ticket Kapat')
                .setStyle(ButtonStyle.Danger)
        );

    await ticketChannel.send({ content: `${player.toString()} <@&${config.staffRoleId}>`, embeds: [embed], components: [row] });

    return ticketChannel;
}

// Queue mesajını güncelle
async function updateQueueMessage(guild, channel = null) {
    const guildId = guild.id;
    const queue = queues.get(guildId);

    if (!channel) {
        channel = guild.channels.cache.get(config.queueChannelId);
    }

    if (!channel) return;

    const messages = await channel.messages.fetch({ limit: 10 });
    const queueMessage = messages.find(msg => msg.author.id === client.user.id && msg.embeds.length > 0);

    if (queueMessage) {
        const embed = new EmbedBuilder()
            .setTitle('🎮 Minecraft Tierlist Queue')
            .setColor('#00ff00')
            .setDescription(queue.length > 0 ? 
                `**Sıradakiler:**\n${queue.map((userId, index) => {
                    const user = client.users.cache.get(userId);
                    return `**${index + 1}.** ${user ? user.toString() : '<Bilinmeyen>'}`;
                }).join('\n')}` : 
                'Henüz kimse yok!'
            )
            .setFooter({ text: `Sırada: ${queue.length} kişi` });

        const row = new ActionRowBuilder()
            .addComponents(
                new ButtonBuilder()
                    .setCustomId('join_queue')
                    .setLabel('Sıraya Gir')
                    .setStyle(ButtonStyle.Success)
                    .setDisabled(queue.length >= 10), // Max 10 kişi
                new ButtonBuilder()
                    .setCustomId('leave_queue')
                    .setLabel('Sıradan Çık')
                    .setStyle(ButtonStyle.Danger)
            );

        await queueMessage.edit({ embeds: [embed], components: [row] });
    }
}

// Staff yetki kontrolü
function checkStaffPermission(member) {
    return member.roles.cache.has(config.staffRoleId);
}

client.login('BOT_TOKENINIZI_BURAYA_YAZIN'); 
