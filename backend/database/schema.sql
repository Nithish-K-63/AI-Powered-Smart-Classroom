-- SQLite Database Schema for AI-Powered Smart Classroom AV Troubleshooting Assistant
-- Enforce Foreign Keys
PRAGMA foreign_keys = ON;

-- 1. Users Table (Role-based access: admin, teacher, technician)
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'technician')),
    department TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- 2. Campus Blocks Table
CREATE TABLE IF NOT EXISTS blocks (
    id TEXT PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- 3. Classrooms Table
CREATE TABLE IF NOT EXISTS classrooms (
    id TEXT PRIMARY KEY,
    block_id TEXT NOT NULL,
    room_number TEXT NOT NULL,
    name TEXT NOT NULL,
    floor INTEGER DEFAULT 1,
    qr_code_token TEXT UNIQUE NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (block_id) REFERENCES blocks(id) ON DELETE RESTRICT,
    UNIQUE(block_id, room_number)
);

-- 4. Technicians Table
CREATE TABLE IF NOT EXISTS technicians (
    id TEXT PRIMARY KEY,
    user_id TEXT UNIQUE,
    full_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    specialty TEXT DEFAULT 'General AV',
    is_available INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 5. Technician Assignments (by block, classroom, or equipment category)
CREATE TABLE IF NOT EXISTS technician_assignments (
    id TEXT PRIMARY KEY,
    technician_id TEXT NOT NULL,
    block_id TEXT,
    classroom_id TEXT,
    equipment_category TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (technician_id) REFERENCES technicians(id) ON DELETE CASCADE,
    FOREIGN KEY (block_id) REFERENCES blocks(id) ON DELETE CASCADE,
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE
);

-- 6. Complaints Table
CREATE TABLE IF NOT EXISTS complaints (
    id TEXT PRIMARY KEY,
    complaint_code TEXT UNIQUE NOT NULL,
    classroom_id TEXT NOT NULL,
    reporter_user_id TEXT,
    device_type TEXT NOT NULL,
    device_model TEXT,
    problem_description TEXT NOT NULL,
    parsed_symptoms TEXT,
    urgency TEXT NOT NULL DEFAULT 'Medium' CHECK(urgency IN ('Low', 'Normal', 'Medium', 'High', 'Urgent')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'resolved', 'escalated', 'closed')),
    assigned_technician_id TEXT,
    resolution_notes TEXT,
    resolved_at TEXT,
    resolved_by_user_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE RESTRICT,
    FOREIGN KEY (reporter_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_technician_id) REFERENCES technicians(id) ON DELETE SET NULL,
    FOREIGN KEY (resolved_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 7. Chat Messages Table (AI-Assisted Troubleshooting Session History)
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    complaint_id TEXT NOT NULL,
    sender_role TEXT NOT NULL CHECK(sender_role IN ('user', 'assistant', 'system')),
    message_text TEXT NOT NULL,
    retrieved_sources_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
);

-- 8. Troubleshooting Steps Table (Step-by-step guidance & teacher feedback)
CREATE TABLE IF NOT EXISTS troubleshooting_steps (
    id TEXT PRIMARY KEY,
    complaint_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    instruction_text TEXT NOT NULL,
    source_doc TEXT,
    source_page INTEGER,
    user_feedback TEXT DEFAULT 'pending' CHECK(user_feedback IN ('pending', 'worked', 'failed', 'skipped')),
    feedback_timestamp TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
    UNIQUE(complaint_id, step_number)
);

-- 9. Complaint Events (Append-only Audit Log)
CREATE TABLE IF NOT EXISTS complaint_events (
    id TEXT PRIMARY KEY,
    complaint_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_name TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
);

-- 10. Technician Notifications (In-App and Twilio Call Logs)
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    complaint_id TEXT NOT NULL,
    technician_id TEXT NOT NULL,
    channel TEXT NOT NULL CHECK(channel IN ('in_app', 'twilio_call', 'sms', 'email')),
    recipient_contact TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'sent', 'failed')),
    error_message TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
    FOREIGN KEY (technician_id) REFERENCES technicians(id) ON DELETE CASCADE
);

-- 11. Knowledge Documents Table (Uploaded Manuals & Guides)
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    total_chunks INTEGER NOT NULL DEFAULT 0,
    doc_metadata_json TEXT,
    uploaded_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Create Indexes for fast querying
CREATE INDEX IF NOT EXISTS idx_classrooms_block ON classrooms(block_id);
CREATE INDEX IF NOT EXISTS idx_complaints_classroom ON complaints(classroom_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_device ON complaints(device_type);
CREATE INDEX IF NOT EXISTS idx_complaints_technician ON complaints(assigned_technician_id);
CREATE INDEX IF NOT EXISTS idx_complaints_created ON complaints(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_complaint ON chat_messages(complaint_id);
CREATE INDEX IF NOT EXISTS idx_steps_complaint ON troubleshooting_steps(complaint_id);
CREATE INDEX IF NOT EXISTS idx_events_complaint ON complaint_events(complaint_id);
CREATE INDEX IF NOT EXISTS idx_notifs_complaint ON notifications(complaint_id);

