function sendMessage() {
    const userInput = document.getElementById('userInput').value;
    if (userInput.trim() === '') return;  // Prevent empty messages

    const chatDiv = document.getElementById('chat');
    chatDiv.innerHTML += `<p>You: ${userInput}</p>`;
    
    // Call your backend to get the chatbot's response
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: userInput })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        chatDiv.innerHTML += `<p>Bot: ${data.reply}</p>`;
    })
    .catch(error => console.error('Error:', error));

    // Clear input after sending
    document.getElementById('userInput').value = '';
}

function register(event) {
    event.preventDefault();
    const username = document.getElementById('registerUsername').value;
    const password = document.getElementById('registerPassword').value;

    fetch('/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => { throw new Error(data.message); });
        }
        return response.json(); // Return JSON if the response is ok
    })
    .then(data => {
        alert(data.message);
        document.getElementById('registerForm').reset(); // Reset the form after successful registration
    })
    .catch(error => alert("Error: " + error.message));
}

function login(event) {
    event.preventDefault();
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;

    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
    })
    .then(response => {
        if (response.ok) {
            alert("Login successful!");
            document.getElementById('loginForm').reset(); // Reset the login form
            document.getElementById('chat-container').style.display = 'block';  // Show chatbot
            document.getElementById('registration').style.display = 'none';     // Hide registration
            document.getElementById('login').style.display = 'none';           // Hide login
        } else {
            return response.json().then(data => { throw new Error(data.message); });
        }
    })
    .catch(error => alert("Error: " + error.message));
}
