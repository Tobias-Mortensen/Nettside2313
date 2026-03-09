require('dotenv').config();
const express = require('express');
const path = require('path');
const fs = require('fs');
const bcrypt = require('bcrypt');
const session = require('express-session');

const app = express();
const USERS_FILE = path.join(__dirname, 'users.json');
const CHAT_FILE = path.join(__dirname, 'chat.json');

if (!fs.existsSync(USERS_FILE)) fs.writeFileSync(USERS_FILE, JSON.stringify([]));
if (!fs.existsSync(CHAT_FILE)) fs.writeFileSync(CHAT_FILE, JSON.stringify([]));

app.use(session({
    secret: process.env.SESSION_SECRET || 'fallback-secret-key', 
    resave: false,
    saveUninitialized: false,
    cookie: { secure: false } 
}));

app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(express.static(__dirname));

const requireAuth = (req, res, next) => {
    if (req.session.user) {
        next();
    } else {
        res.redirect('/login');
    }
};

// --- Page Routes ---
app.get('/', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));
app.get('/login', (req, res) => res.sendFile(path.join(__dirname, 'login.html')));
app.get('/signup', (req, res) => res.sendFile(path.join(__dirname, 'signup.html')));
app.get('/site', requireAuth, (req, res) => res.sendFile(path.join(__dirname, 'site.html')));
app.get('/faq', (req, res) => res.sendFile(path.join(__dirname, 'faq.html')));

// --- New: User Status Route ---
app.get('/api/user-status', (req, res) => {
    if (req.session.user) {
        res.json({ 
            loggedIn: true, 
            permission: req.session.user.permission 
        });
    } else {
        res.json({ loggedIn: false });
    }
});

// --- Auth Logic ---
app.post('/auth/signup', async (req, res) => {
    try {
        const { username, password } = req.body;
        const users = JSON.parse(fs.readFileSync(USERS_FILE));
        if (users.find(u => u.username === username)) return res.send("User already exists.");
        const hashedPassword = await bcrypt.hash(password, 10);
        const newUser = { username, password: hashedPassword, permission: 1 };
        users.push(newUser);
        fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 4));
        req.session.user = { username: newUser.username, permission: newUser.permission };
        req.session.save(() => res.redirect('/site'));
    } catch (err) {
        res.status(500).send("Error signing up.");
    }
});

app.post('/auth/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        const users = JSON.parse(fs.readFileSync(USERS_FILE));
        const user = users.find(u => u.username === username);
        if (user && await bcrypt.compare(password, user.password)) {
            req.session.user = { username: user.username, permission: user.permission };
            return res.redirect('/site');
        }
        res.send("Invalid username or password.");
    } catch (err) {
        res.status(500).send("Server error.");
    }
});

app.get('/logout', (req, res) => {
    req.session.destroy();
    res.redirect('/login');
});

// --- Chat Logic ---
const cooldowns = new Set();

app.get('/api/chats', requireAuth, (req, res) => {
    const chatData = JSON.parse(fs.readFileSync(CHAT_FILE, 'utf8') || "[]");
    res.json(chatData.slice(-50));
});

app.post('/send-chat', requireAuth, (req, res) => {
    const username = req.session.user.username;
    const { message } = req.body;
    if (!message || message.length > 128) return res.status(400).json({ error: "Invalid message" });
    if (cooldowns.has(username)) return res.status(429).json({ error: "Wait 1 second." });

    cooldowns.add(username);
    setTimeout(() => cooldowns.delete(username), 1000);

    const chatData = JSON.parse(fs.readFileSync(CHAT_FILE, 'utf8') || "[]");
    const newMessage = { username, text: message, time: Date.now() };
    chatData.push(newMessage);
    fs.writeFileSync(CHAT_FILE, JSON.stringify(chatData, null, 2));
    res.json({ success: true, newMessage });
});

app.delete('/api/chats/:timestamp', requireAuth, (req, res) => {
    if (req.session.user.permission < 2) return res.status(403).send("Admin only.");
    const timestamp = parseInt(req.params.timestamp);
    let chats = JSON.parse(fs.readFileSync(CHAT_FILE));
    const updatedChats = chats.filter(m => m.time !== timestamp);
    fs.writeFileSync(CHAT_FILE, JSON.stringify(updatedChats, null, 2));
    res.send("Deleted.");
});

app.listen(3000, () => console.log('Server running on port 3000'));