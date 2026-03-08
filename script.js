const express = require('express');
const path = require('path');
const fs = require('fs');
const bcrypt = require('bcrypt'); // New dependency
const app = express();

const USERS_FILE = path.join(__dirname, 'users.json');

app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.use(express.static(__dirname));

// Route for the secret page
app.get('/penis', (req, res) => {
    res.send("<h1>Access Granted: Welcome to the inner circle.</h1>");
});

// SIGN UP: Encrypt password before saving
app.post('/auth/signup', async (req, res) => {
    const { username, password } = req.body;
    const users = JSON.parse(fs.readFileSync(USERS_FILE));

    if (users.find(u => u.username === username)) {
        return res.status(400).send("User already exists.");
    }

    try {
        // Hash the password with a salt round of 10
        const hashedPassword = await bcrypt.hash(password, 10);
        
        const newUser = {
            username,
            password: hashedPassword,
            permission: 1
        };

        users.push(newUser);
        fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 4));
        res.redirect('/login');
    } catch {
        res.status(500).send("Error creating user.");
    }
});

// LOGIN: Compare hashed password and redirect
app.post('/auth/login', async (req, res) => {
    const { username, password } = req.body;
    const users = JSON.parse(fs.readFileSync(USERS_FILE));
    
    const user = users.find(u => u.username === username);

    if (user) {
        // Check if the entered password matches the hashed password
        const match = await bcrypt.compare(password, user.password);
        
        if (match) {
            // SUCCESS: Redirect to your specific path
            res.redirect('/penis');
        } else {
            res.status(401).send("Invalid password.");
        }
    } else {
        res.status(404).send("User not found.");
    }
});

app.listen(3000, () => console.log('Server running on port 3000'));