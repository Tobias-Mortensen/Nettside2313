const express = require('express');
const path = require('path');
const fs = require('fs');
const bcrypt = require('bcrypt');
const session = require('express-session');
const app = express();

const USERS_FILE = path.join(__dirname, 'users.json');

// 1. Session Middleware setup
require('dotenv').config();

app.use(session({
    secret: process.env.SESSION_SECRET, // Pulls from the .env file
    resave: false,
    saveUninitialized: false,
    cookie: { secure: false } 
}));

app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(express.static(__dirname));

if (!fs.existsSync(USERS_FILE)) {
    fs.writeFileSync(USERS_FILE, JSON.stringify([]));
}

// 2. Protected Route Middleware
const requireAuth = (req, res, next) => {
    if (req.session.user) {
        next();
    } else {
        res.redirect('/login');
    }
};

// Routes
app.get('/', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));
app.get('/login', (req, res) => res.sendFile(path.join(__dirname, 'login.html')));
app.get('/signup', (req, res) => res.sendFile(path.join(__dirname, 'signup.html')));
app.get('/site', requireAuth, (req, res) => res.sendFile(path.join(__dirname, 'site.html')));
app.get('/faq', (req, res) => {res.sendFile(path.join(__dirname, 'faq.html'));});


// Sign Up Logic: Encrypt, Save, and Auto-Login
app.post('/auth/signup', async (req, res) => {
    try {
        const { username, password } = req.body;
        const users = JSON.parse(fs.readFileSync(USERS_FILE));

        if (users.find(u => u.username === username)) {
            return res.send("User already exists.");
        }

        const hashedPassword = await bcrypt.hash(password, 10);
        const newUser = {
            username,
            password: hashedPassword,
            permission: 1
        };

        users.push(newUser);
        fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 4));

        // --- THE FIX ---
        req.session.user = { 
            username: newUser.username, 
            permission: newUser.permission 
        };

        // Force save the session before redirecting
        req.session.save((err) => {
            if (err) {
                console.error("Session save error:", err);
                return res.redirect('/login');
            }
            res.redirect('/site');
        });

    } catch (err) {
        console.error(err);
        res.status(500).send("Error signing up.");
    }
});

// Login Logic with Session
app.post('/auth/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        const users = JSON.parse(fs.readFileSync(USERS_FILE));
        
        const user = users.find(u => u.username === username);

        if (user) {
            const isMatch = await bcrypt.compare(password, user.password);
            
            if (isMatch) {
                // Save user info to the session
                req.session.user = { username: user.username, permission: user.permission };
                
                // CRITICAL: This must be res.redirect for the URL to change
                return res.redirect('/site'); 
            }
        }
        res.send("Invalid username or password.");
    } catch (err) {
        res.status(500).send("Server error during login.");
    }
});

// Logout Route
app.get('/logout', (req, res) => {
    req.session.destroy();
    res.redirect('/login');
});

app.listen(3000, () => console.log('Server running on port 3000'));