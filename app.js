const express = require("express");
const path = require("path");
const app = express();

// This line tells Express to serve all your files (css, js, images) 
// located in the current folder.
app.use(express.static(__dirname));

// Route for the Home Page
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

// Route for the Login Page (so epsteinisland.no/login works)
app.get("/login", (req, res) => {
  res.sendFile(path.join(__dirname, "login.html"));
});

app.listen(3000, "0.0.0.0", () => {
  console.log("Server running on port 3000. Access via epsteinisland.no");
});