require('dotenv').config();
const { Client, GatewayIntentBits, PermissionFlagsBits, EmbedBuilder, ChannelType, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');
const express = require('express');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// ── Config ──────────────────────────────────────────────
const BOT_TOKEN = process.env.BOT_TOKEN;
const GUILD_ID = process.env.GUILD_ID;
const CUSTOMER_ROLE_ID = process.env.CUSTOMER_ROLE_ID;
const ADMIN_ROLE_ID = process.env.ADMIN_ROLE_ID;
const API_PORT = parseInt(process.env.API_PORT || '3001');
const API_SECRET = process.env.API_SECRET; // shared secret with website
const LICENSES_FILE = path.join(__dirname, 'licenses.json');
const TRANSCRIPTS_DIR = path.join(__dirname, 'transcripts');

// Ensure transcripts directory exists
if (!fs.existsSync(TRANSCRIPTS_DIR)) fs.mkdirSync(TRANSCRIPTS_DIR);

// ── Category cache (auto-created on first ticket) ──────
const categoryCache = { support: null, purchase: null };

// ── License Store ───────────────────────────────────────
function loadLicenses() {
  try {
    return JSON.parse(fs.readFileSync(LICENSES_FILE, 'utf8'));
  } catch {
    return {};
  }
}

function saveLicenses(data) {
  fs.writeFileSync(LICENSES_FILE, JSON.stringify(data, null, 2));
}

function generateKey() {
  // Format: LARP-XXXX-XXXX-XXXX-XXXX
  const seg = () => crypto.randomBytes(2).toString('hex').toUpperCase();
  return `LARP-${seg()}-${seg()}-${seg()}-${seg()}`;
}

// ── Discord Bot ─────────────────────────────────────────
const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers],
});

client.once('ready', () => {
  console.log(`Bot online as ${client.user.tag}`);
});

// ── Ticket Helpers ─────────────────────────────────────
async function findOrCreateCategory(guild, type) {
  const names = { support: 'Support Tickets', purchase: 'Purchase Tickets' };
  const name = names[type];

  // Check cache first
  if (categoryCache[type]) {
    const cached = guild.channels.cache.get(categoryCache[type]);
    if (cached) return cached;
  }

  // Look for existing category
  let category = guild.channels.cache.find(
    c => c.type === ChannelType.GuildCategory && c.name === name
  );

  if (!category) {
    category = await guild.channels.create({
      name,
      type: ChannelType.GuildCategory,
      permissionOverwrites: [
        { id: guild.id, deny: [PermissionFlagsBits.ViewChannel] },
        { id: ADMIN_ROLE_ID, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages] },
      ],
    });
  }

  categoryCache[type] = category.id;
  return category;
}

async function fetchAllMessages(channel) {
  const messages = [];
  let lastId;

  while (true) {
    const batch = await channel.messages.fetch({ limit: 100, ...(lastId && { before: lastId }) });
    if (batch.size === 0) break;
    messages.push(...batch.values());
    lastId = batch.last().id;
  }

  return messages.sort((a, b) => a.createdTimestamp - b.createdTimestamp);
}

async function saveTranscript(channel, ticketType, creatorId) {
  const messages = await fetchAllMessages(channel);

  const lines = messages.map(m => {
    const time = m.createdAt.toISOString();
    const author = m.author?.tag || 'Unknown';
    const content = m.content || (m.embeds.length ? '[embed]' : '[attachment]');
    return `[${time}] ${author}: ${content}`;
  });

  const text = lines.join('\n') || '(no messages)';
  const filename = `${ticketType}-${channel.name}-${Date.now()}.txt`;
  const filepath = path.join(TRANSCRIPTS_DIR, filename);

  fs.writeFileSync(filepath, text, 'utf8');

  // DM transcript to the ticket creator
  try {
    const creator = await channel.client.users.fetch(creatorId);
    await creator.send({
      content: `Your ${ticketType} ticket has been closed. Here is your transcript:`,
      files: [{ attachment: filepath, name: filename }],
    });
  } catch (err) {
    console.error('Failed to DM transcript:', err.message);
  }

  return filepath;
}

// ── Interaction Handler ────────────────────────────────
client.on('interactionCreate', async (interaction) => {
  // ── Button interactions ──
  if (interaction.isButton()) {
    const id = interaction.customId;

    // Create ticket buttons
    if (id === 'create_support_ticket' || id === 'create_purchase_ticket') {
      const type = id === 'create_support_ticket' ? 'support' : 'purchase';
      const guild = interaction.guild;
      const user = interaction.user;

      // Check for existing open ticket
      const prefix = `${type}-${user.username.toLowerCase().replace(/[^a-z0-9]/g, '')}`;
      const existing = guild.channels.cache.find(
        c => c.type === ChannelType.GuildText && c.name === prefix
      );
      if (existing) {
        return interaction.reply({ content: `You already have an open ${type} ticket: ${existing}`, flags: 64 });
      }

      await interaction.deferReply({ flags: 64 });

      const category = await findOrCreateCategory(guild, type);

      const ticketChannel = await guild.channels.create({
        name: prefix,
        type: ChannelType.GuildText,
        parent: category.id,
        permissionOverwrites: [
          { id: guild.id, deny: [PermissionFlagsBits.ViewChannel] },
          { id: user.id, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages] },
          { id: ADMIN_ROLE_ID, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages] },
        ],
      });

      // Welcome embed with close button
      const welcomeEmbed = new EmbedBuilder()
        .setColor(type === 'support' ? 0x5865f2 : 0x57f287)
        .setTitle(type === 'support' ? 'Support Ticket' : 'Purchase Ticket')
        .setDescription(
          type === 'support'
            ? `Hey ${user}, welcome to your support ticket!\nPlease describe your issue and a staff member will assist you.`
            : `Hey ${user}, welcome to your purchase ticket!\nPlease let us know what you'd like to purchase and a staff member will assist you.`
        )
        .setFooter({ text: 'Click the button below to close this ticket.' })
        .setTimestamp();

      const closeRow = new ActionRowBuilder().addComponents(
        new ButtonBuilder()
          .setCustomId(`close_ticket_${user.id}`)
          .setLabel('Close Ticket')
          .setStyle(ButtonStyle.Danger)
      );

      await ticketChannel.send({ embeds: [welcomeEmbed], components: [closeRow] });

      return interaction.editReply({ content: `Your ticket has been created: ${ticketChannel}` });
    }

    // Close ticket button
    if (id.startsWith('close_ticket_')) {
      const confirmRow = new ActionRowBuilder().addComponents(
        new ButtonBuilder()
          .setCustomId(`confirm_close_${id.replace('close_ticket_', '')}`)
          .setLabel('Confirm Close')
          .setStyle(ButtonStyle.Danger),
        new ButtonBuilder()
          .setCustomId('cancel_close')
          .setLabel('Cancel')
          .setStyle(ButtonStyle.Secondary)
      );

      return interaction.reply({
        content: 'Are you sure you want to close this ticket? A transcript will be saved.',
        components: [confirmRow],
      });
    }

    // Confirm close
    if (id.startsWith('confirm_close_')) {
      const creatorId = id.replace('confirm_close_', '');
      const channel = interaction.channel;

      await interaction.reply({ content: 'Saving transcript and closing ticket...' });

      // Determine ticket type from category name
      const parent = channel.parent;
      const ticketType = parent?.name?.toLowerCase().includes('support') ? 'support' : 'purchase';

      await saveTranscript(channel, ticketType, creatorId);

      // Small delay so the user sees the message
      setTimeout(() => channel.delete().catch(console.error), 3000);
      return;
    }

    // Cancel close
    if (id === 'cancel_close') {
      return interaction.update({ content: 'Ticket close cancelled.', components: [] });
    }

    return;
  }

  if (!interaction.isChatInputCommand()) return;

  const { commandName } = interaction;

  // ── /grant ──
  if (commandName === 'grant') {
    // Admin only
    if (!interaction.member.roles.cache.has(ADMIN_ROLE_ID) &&
        !interaction.member.permissions.has(PermissionFlagsBits.Administrator)) {
      return interaction.reply({ content: '❌ You don\'t have permission to do this.', flags: 64 });
    }

    const target = interaction.options.getUser('user');
    const licenses = loadLicenses();

    if (licenses[target.id]) {
      return interaction.reply({ content: `⚠️ **${target.username}** already has a license: \`${licenses[target.id].key}\``, flags: 64 });
    }

    const key = generateKey();
    licenses[target.id] = {
      key,
      username: target.username,
      grantedBy: interaction.user.id,
      grantedAt: new Date().toISOString(),
    };
    saveLicenses(licenses);

    // Give customer role
    try {
      const guild = interaction.guild;
      const member = await guild.members.fetch(target.id);
      await member.roles.add(CUSTOMER_ROLE_ID);
    } catch (err) {
      console.error('Failed to add role:', err.message);
    }

    // DM the user their license key
    try {
      const embed = new EmbedBuilder()
        .setColor(0x00d4ff)
        .setTitle('🔑 Larp Client — License Key')
        .setDescription('Thank you for your purchase! Here is your license key.')
        .addFields(
          { name: 'License Key', value: `\`\`\`${key}\`\`\`` },
          { name: 'How to Use', value: 'Enter this key in the Larp Client to activate. You can also view it on your profile at the website.' }
        )
        .setFooter({ text: 'Keep this key private — do not share it.' })
        .setTimestamp();

      await target.send({ embeds: [embed] });
    } catch (err) {
      console.error('Failed to DM user:', err.message);
    }

    const confirmEmbed = new EmbedBuilder()
      .setColor(0x00ff88)
      .setTitle('✅ License Granted')
      .addFields(
        { name: 'User', value: `<@${target.id}>`, inline: true },
        { name: 'Key', value: `\`${key}\``, inline: true }
      )
      .setTimestamp();

    return interaction.reply({ embeds: [confirmEmbed], flags: 64 });
  }

  // ── /revoke ──
  if (commandName === 'revoke') {
    if (!interaction.member.roles.cache.has(ADMIN_ROLE_ID) &&
        !interaction.member.permissions.has(PermissionFlagsBits.Administrator)) {
      return interaction.reply({ content: '❌ You don\'t have permission to do this.', flags: 64 });
    }

    const target = interaction.options.getUser('user');
    const licenses = loadLicenses();

    if (!licenses[target.id]) {
      return interaction.reply({ content: `⚠️ **${target.username}** doesn't have a license.`, flags: 64 });
    }

    delete licenses[target.id];
    saveLicenses(licenses);

    // Remove customer role
    try {
      const guild = interaction.guild;
      const member = await guild.members.fetch(target.id);
      await member.roles.remove(CUSTOMER_ROLE_ID);
    } catch (err) {
      console.error('Failed to remove role:', err.message);
    }

    return interaction.reply({ content: `✅ License revoked for **${target.username}**.`, flags: 64 });
  }

  // ── /license ──
  if (commandName === 'license') {
    const licenses = loadLicenses();
    const entry = licenses[interaction.user.id];

    if (!entry) {
      return interaction.reply({ content: '❌ You don\'t have a license. Purchase one to get started!', flags: 64 });
    }

    const embed = new EmbedBuilder()
      .setColor(0x00d4ff)
      .setTitle('🔑 Your License Key')
      .addFields({ name: 'Key', value: `\`\`\`${entry.key}\`\`\`` })
      .setFooter({ text: 'Keep this key private.' })
      .setTimestamp();

    return interaction.reply({ embeds: [embed], flags: 64 });
  }

  // ── /support ──
  if (commandName === 'support') {
    if (!interaction.member.roles.cache.has(ADMIN_ROLE_ID) &&
        !interaction.member.permissions.has(PermissionFlagsBits.Administrator)) {
      return interaction.reply({ content: '❌ You don\'t have permission to do this.', flags: 64 });
    }

    const embed = new EmbedBuilder()
      .setColor(0x5865f2)
      .setTitle('Larp Client — Support')
      .setDescription('Need help? Click the button below to create a support ticket.\nA staff member will assist you as soon as possible.')
      .setFooter({ text: 'Larp Client Support' })
      .setTimestamp();

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setCustomId('create_support_ticket')
        .setLabel('Create Support Ticket')
        .setStyle(ButtonStyle.Primary)
    );

    await interaction.channel.send({ embeds: [embed], components: [row] });
    return interaction.reply({ content: '✅ Support panel posted.', flags: 64 });
  }

  // ── /purch ──
  if (commandName === 'purch') {
    if (!interaction.member.roles.cache.has(ADMIN_ROLE_ID) &&
        !interaction.member.permissions.has(PermissionFlagsBits.Administrator)) {
      return interaction.reply({ content: '❌ You don\'t have permission to do this.', flags: 64 });
    }

    const embed = new EmbedBuilder()
      .setColor(0x57f287)
      .setTitle('Larp Client — Purchase')
      .setDescription('Interested in purchasing? Click the button below to open a purchase ticket.\nA staff member will help you complete your order.')
      .setFooter({ text: 'Larp Client Purchases' })
      .setTimestamp();

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setCustomId('create_purchase_ticket')
        .setLabel('Create Purchase Ticket')
        .setStyle(ButtonStyle.Success)
    );

    await interaction.channel.send({ embeds: [embed], components: [row] });
    return interaction.reply({ content: '✅ Purchase panel posted.', flags: 64 });
  }
});

client.login(BOT_TOKEN);

// ── HTTP API (for website to query licenses) ────────────
const app = express();

// Auth middleware — website must send the shared secret
app.use('/api', (req, res, next) => {
  const auth = req.headers['authorization'];
  if (!API_SECRET || auth !== `Bearer ${API_SECRET}`) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
});

// GET /api/license/:discordId
app.get('/api/license/:discordId', (req, res) => {
  const licenses = loadLicenses();
  const entry = licenses[req.params.discordId];

  if (!entry) {
    return res.json({ licensed: false });
  }

  res.json({
    licensed: true,
    key: entry.key,
    grantedAt: entry.grantedAt,
  });
});

app.listen(API_PORT, () => {
  console.log(`License API running on port ${API_PORT}`);
});
