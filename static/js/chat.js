// chat.js - Handles real-time messaging logic
let socket;
let currentConversationId = null;

function initChat(userId) {
    // Initialize Socket.io
    socket = io();

    socket.on('connect', () => {
        console.log('Connected to Chat Server');
    });

    socket.on('new_message', (data) => {
        if (data.conversation_id === currentConversationId) {
            appendMessage(data);
            scrollChatToBottom();
            
            // If it was disabled before (e.g., first message for seeker), enable it
            const input = document.getElementById('chat-input');
            const sendBtn = document.getElementById('send-btn');
            const userRole = document.getElementById('current-user-role').value;
            
            if (input && input.disabled && userRole === 'job_seeker' && data.sender_id !== document.getElementById('current-user-id').value) {
                input.disabled = false;
                sendBtn.disabled = false;
                input.placeholder = "Type a message...";
                input.focus();
            }
        }
        // Always refresh list to update last message preview and order
        refreshConversationList();
    });

    // Refresh conversation list on load
    refreshConversationList();
}

async function refreshConversationList() {
    const individualList = document.getElementById('individual-list');
    const groupList = document.getElementById('group-list');
    const individualSection = document.getElementById('individual-section');
    const groupSection = document.getElementById('group-section');
    
    const loadingEl = document.getElementById('loading-convs');
    const emptyEl = document.getElementById('empty-convs');
    
    if (!individualList || !groupList) return;
    
    try {
        const res = await fetch('/api/chat/conversations');
        const convs = await res.json();
        
        if (loadingEl) loadingEl.style.display = 'none';
        
        if (convs.length === 0) {
            if (emptyEl) emptyEl.style.display = 'block';
            individualSection.style.display = 'none';
            groupSection.style.display = 'none';
            return;
        }
        
        if (emptyEl) emptyEl.style.display = 'none';
        
        // Clear lists
        individualList.innerHTML = '';
        groupList.innerHTML = '';
        
        let hasIndividual = false;
        let hasGroup = false;

        convs.forEach(conv => {
            const item = document.createElement('div');
            item.className = `conv-item ${conv.id === currentConversationId ? 'active' : ''}`;
            item.onclick = () => loadConversation(conv.id);
            
            let name = "";
            if (conv.type === 'group') {
                name = `👥 ${conv.group_name}`;
                hasGroup = true;
            } else {
                // Focus on candidate name as requested
                name = conv.other_user_name || "New Candidate";
                if (conv.job_title) {
                    name += ` <small style="color: #64748b; font-weight: normal; font-size: 0.7rem;">(${conv.job_title})</small>`;
                }
                hasIndividual = true;
            }
            
            item.innerHTML = `
                <div class="conv-name">${name}</div>
                <div class="conv-last-msg">${conv.last_message || "No messages yet"}</div>
            `;
            
            if (conv.type === 'group') {
                groupList.appendChild(item);
            } else {
                individualList.appendChild(item);
            }
        });

        individualSection.style.display = hasIndividual ? 'block' : 'none';
        groupSection.style.display = hasGroup ? 'block' : 'none';

    } catch (err) {
        console.error('Failed to load conversations:', err);
        if (loadingEl) loadingEl.innerHTML = '<small class="text-danger">Error loading chats</small>';
    }
}

async function loadConversation(convId) {
    console.log('Loading conversation:', convId);
    currentConversationId = convId;
    const chatWindow = document.getElementById('chat-window');
    chatWindow.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Fetching history...</p></div>';
    
    // Highlight active conversation
    document.querySelectorAll('.conv-item').forEach(el => {
        el.classList.remove('active');
        // We use a custom attribute or similar to find the right one since onclick comparisons are brittle
    });

    try {
        const res = await fetch(`/api/chat/history/${convId}`);
        if (!res.ok) throw new Error('Failed to fetch history');
        const history = await res.json();
        
        chatWindow.innerHTML = ''; // Clear loading
        if (history.length === 0) {
            chatWindow.innerHTML = `
                <div class="welcome-center" style="opacity: 0.6;">
                    <div class="illustration-bubble">👋</div>
                    <h3>Start the Conversation</h3>
                    <p>Send your first message to begin the collaboration.</p>
                </div>
            `;
        } else {
            history.forEach(msg => appendMessage(msg));
            scrollChatToBottom();
        }
        
        // Join the Socket.io room
        socket.emit('join', { conversation_id: convId });
        
        // Role-based Access Control for Input
        const inputArea = document.getElementById('chat-input-area');
        const input = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        const userRole = document.getElementById('current-user-role').value;
        
        inputArea.style.display = 'block';
        
        if (userRole === 'job_seeker' && history.length === 0) {
            input.disabled = true;
            sendBtn.disabled = true;
            input.placeholder = "Waiting for recruiter to initiate the conversation...";
        } else {
            input.disabled = false;
            sendBtn.disabled = false;
            input.placeholder = "Write something amazing...";
            input.focus();
        }
        
    } catch (err) {
        console.error('Chat load error:', err);
        chatWindow.innerHTML = '<div class="error">Failed to load history</div>';
    }

    // Refresh list to show active state properly
    refreshConversationList();
}

function appendMessage(msg) {
    const window = document.getElementById('chat-window');
    const welcome = window.querySelector('.welcome-center');
    if (welcome) welcome.remove();

    const msgEl = document.createElement('div');
    const currentUserId = document.getElementById('current-user-id').value;
    const isMe = String(msg.sender_id) === String(currentUserId);
    
    msgEl.className = `message-bubble ${isMe ? 'message-me' : 'message-them'}`;
    msgEl.innerHTML = `
        <div class="sender-name">${isMe ? 'You' : msg.sender_name}</div>
        <div class="msg-content">${msg.content}</div>
        <div class="msg-time">${new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
    `;
    window.appendChild(msgEl);
    scrollChatToBottom();
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    const content = input.value.trim();
    
    if (!content || !currentConversationId) return;
    
    socket.emit('send_message', {
        conversation_id: currentConversationId,
        content: content
    });
    
    input.value = '';
}

function scrollChatToBottom() {
    const window = document.getElementById('chat-window');
    window.scrollTop = window.scrollHeight;
}

// Global triggering chat initialization
async function startChatWith(candidateId) {
    try {
        const res = await fetch('/api/chat/start_or_get_individual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ candidate_id: candidateId })
        });
        const data = await res.json();
        if (data.conversation_id) {
            window.location.href = '/dashboard/messages?conv=' + data.conversation_id;
        }
    } catch (err) {
        alert('Failed to start chat');
    }
}
