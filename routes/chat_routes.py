from flask import Blueprint, render_template, request, session, jsonify, url_for, redirect
from flask_socketio import emit, join_room, leave_room
from config.database import db_config
from datetime import datetime
import traceback

chat_bp = Blueprint('chat', __name__)
socketio = None # Will be initialized in app.py

def init_chat_socketio(sio):
    global socketio
    socketio = sio
    
    @socketio.on('join')
    def on_join(data):
        room = f"conv_{data['conversation_id']}"
        join_room(room)
        print(f"User {session.get('user_id')} joined room {room}")

    @socketio.on('send_message')
    def on_send_message(data):
        conv_id = data['conversation_id']
        content = data['content']
        sender_id = session.get('user_id')
        
        if not sender_id:
            return

        conn = db_config.get_connection()
        try:
            cursor = conn.cursor()
            
            # CHECK: If sender is a job seeker, they can only send if there is already at least one message
            if session.get('role') == 'job_seeker':
                cursor.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = %s", (conv_id,))
                msg_count = cursor.fetchone()[0]
                if msg_count == 0:
                    print(f"Blocked message from seeker {sender_id} to empty conversation {conv_id}")
                    return
            
            # Save to database
            cursor.execute(
                "INSERT INTO messages (conversation_id, sender_id, content) VALUES (%s, %s, %s) RETURNING id, timestamp",
                (conv_id, sender_id, content)
            )
            new_msg = cursor.fetchone()
            conn.commit()
            
            # Broadcast to room
            room = f"conv_{conv_id}"
            emit('new_message', {
                'id': new_msg[0],
                'conversation_id': conv_id,
                'sender_id': sender_id,
                'sender_name': session.get('fullname'),
                'content': content,
                'timestamp': new_msg[1].isoformat() if hasattr(new_msg[1], 'isoformat') else str(new_msg[1])
            }, room=room)
        except Exception as e:
            print(f"Error sending message: {e}")
            traceback.print_exc()
        finally:
            conn.close()

@chat_bp.route('/dashboard/messages')
def chat_hub():
    """Main chat interface showing all conversations"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('dashboard/chat_hub.html')

@chat_bp.route('/api/chat/conversations')
def get_conversations():
    """Fetch all conversations for the current user"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        # Complex query to get conversations with participant names and last message
        # Added subquery to find the OTHER participant's name for individual chats
        query = """
            SELECT 
                c.id, 
                c.type, 
                c.group_name, 
                c.job_id,
                j.title as job_title,
                (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY timestamp DESC LIMIT 1) as last_message,
                (SELECT timestamp FROM messages WHERE conversation_id = c.id ORDER BY timestamp DESC LIMIT 1) as last_msg_time,
                (SELECT u.fullname FROM participants p2 
                 JOIN users u ON p2.user_id = u.id 
                 WHERE p2.conversation_id = c.id AND p2.user_id != %s LIMIT 1) as other_user_name
            FROM conversations c
            JOIN participants p ON c.id = p.conversation_id
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE p.user_id = %s
            ORDER BY last_msg_time DESC NULLS LAST
        """
        cursor.execute(query, (user_id, user_id))
        rows = cursor.fetchall()
        
        conversations = []
        for r in rows:
            conversations.append({
                "id": r[0],
                "type": r[1],
                "group_name": r[2],
                "job_id": r[3],
                "job_title": r[4],
                "last_message": r[5] or "No messages yet",
                "last_msg_time": r[6].isoformat() if r[6] else None,
                "other_user_name": r[7]
            })
        return jsonify(conversations)
    except Exception as e:
        print(f"Error fetching conversations: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@chat_bp.route('/api/chat/history/<int:conv_id>')
def get_chat_history(conv_id):
    """Fetch all messages for a specific conversation"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
        
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        # Verify user is a participant
        cursor.execute("SELECT 1 FROM participants WHERE conversation_id = %s AND user_id = %s", (conv_id, user_id))
        if not cursor.fetchone():
            return jsonify({"error": "Forbidden"}), 403
            
        # Get messages with sender names
        query = """
            SELECT m.id, m.sender_id, u.fullname, m.content, m.timestamp
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.conversation_id = %s
            ORDER BY m.timestamp ASC
        """
        cursor.execute(query, (conv_id,))
        rows = cursor.fetchall()
        
        messages = []
        for r in rows:
            messages.append({
                "id": r[0],
                "sender_id": r[1],
                "sender_name": r[2],
                "content": r[3],
                "timestamp": r[4].isoformat()
            })
        return jsonify(messages)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@chat_bp.route('/api/chat/start_or_get_individual', methods=['POST'])
def start_individual_chat():
    """Start or get an existing 1:1 chat with a candidate"""
    if session.get('role') != 'recruiter':
        return jsonify({"error": "Only recruiters can initiate chats"}), 403
        
    data = request.json
    candidate_id = data.get('candidate_id')
    recruiter_id = session.get('user_id')
    
    if not candidate_id:
        return jsonify({"error": "Candidate ID required"}), 400
        
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        # 1. Check if 1:1 conversation already exists between these two
        query = """
            SELECT c.id 
            FROM conversations c
            JOIN participants p1 ON c.id = p1.conversation_id
            JOIN participants p2 ON c.id = p2.conversation_id
            WHERE c.type = 'individual' 
            AND p1.user_id = %s 
            AND p2.user_id = %s
        """
        cursor.execute(query, (recruiter_id, candidate_id))
        existing = cursor.fetchone()
        
        if existing:
            return jsonify({"conversation_id": existing[0]})
            
        # 2. Create new individual conversation
        cursor.execute("INSERT INTO conversations (type) VALUES ('individual') RETURNING id")
        conv_id = cursor.fetchone()[0]
        
        # 3. Add both participants
        cursor.execute("INSERT INTO participants (conversation_id, user_id) VALUES (%s, %s)", (conv_id, recruiter_id))
        cursor.execute("INSERT INTO participants (conversation_id, user_id) VALUES (%s, %s)", (conv_id, candidate_id))
        
        conn.commit()
        return jsonify({"conversation_id": conv_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@chat_bp.route('/api/chat/create_group', methods=['POST'])
def create_group_chat():
    """Create a group chat for shortlisted candidates"""
    if session.get('role') != 'recruiter':
        return jsonify({"error": "Only recruiters can create groups"}), 403
        
    data = request.json
    group_name = data.get('group_name')
    candidate_ids = data.get('candidate_ids', []) # List of user IDs
    job_id = data.get('job_id')
    recruiter_id = session.get('user_id')
    
    if not group_name or not candidate_ids:
        return jsonify({"error": "Group name and candidates required"}), 400
        
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        # 1. Create group conversation
        cursor.execute(
            "INSERT INTO conversations (type, group_name, job_id) VALUES ('group', %s, %s) RETURNING id",
            (group_name, job_id)
        )
        conv_id = cursor.fetchone()[0]
        
        # 2. Add recruiter
        cursor.execute("INSERT INTO participants (conversation_id, user_id) VALUES (%s, %s)", (conv_id, recruiter_id))
        
        # 3. Add all candidates
        for cid in candidate_ids:
            cursor.execute("INSERT INTO participants (conversation_id, user_id) VALUES (%s, %s)", (conv_id, cid))
            
        conn.commit()
        return jsonify({"conversation_id": conv_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@chat_bp.route('/api/chat/candidates')
def get_candidates():
    """Fetch all candidates who applied to recruiter's jobs"""
    if session.get('role') != 'recruiter':
        return jsonify([])
        
    user_id = session.get('user_id')
    conn = db_config.get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT DISTINCT u.id, u.fullname, u.email, u.profile_pic
            FROM users u
            JOIN applications a ON u.id = a.job_seeker_id
            JOIN jobs j ON a.job_id = j.id
            WHERE j.recruiter_id = %s
        """
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        candidates = []
        for r in rows:
            candidates.append({
                "id": r[0],
                "fullname": r[1],
                "email": r[2],
                "profile_pic": r[3]
            })
        return jsonify(candidates)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
