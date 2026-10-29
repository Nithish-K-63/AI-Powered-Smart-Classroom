"""Seed Campus Blocks, Classrooms, Technicians, Manuals, and Initial SOPs matching Figma Make Prototype."""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.connection import db_session, init_database
from backend.database.crud import (
    assign_technician,
    create_block,
    create_classroom,
    create_complaint,
    create_technician,
    create_user,
    list_blocks,
    list_classrooms,
    list_technicians,
    register_knowledge_document,
    update_complaint_status,
)
from backend.rag.document_processor import ManualDocumentProcessor
from backend.rag.vector_store import vector_store

MANUALS_DIR = PROJECT_ROOT / "data" / "campus_manuals"
MANUALS_DIR.mkdir(parents=True, exist_ok=True)


def seed_sample_manuals():
    """Create verified campus AV equipment SOP manuals."""
    manuals = {
        "projector_sop.txt": (
            "Epson & BenQ Classroom Projector Standard Operating Procedure",
            "projector",
            """Campus AV Department - Standard Operating Procedure: Classroom Projectors (SOP-PRJ-01)
Page 1: Power & Startup Instructions
1. Ensure the wall power switch labeled 'AV Mains' is in the ON position with an amber LED.
2. Press the blue 'POWER' button on the classroom podium control panel or the remote once.
3. Observe the Status Indicator: A solid blue LED confirms standard operation. A flashing orange LED indicates lamp cool-down or warming cycle; wait 60 seconds before pressing power again.
4. If no display is projected after 90 seconds, verify the HDMI cable connection between the podium patch panel and the projector input port.

Page 2: Signal & Input Source Selection
1. On the podium switcher, select 'HDMI 1 (Laptop)' or press 'Source Search' on the remote.
2. On Windows laptops, press [Windows Key] + [P] and select 'Duplicate' to output 1080p video.
3. If the projector shows 'No Signal Detected', inspect the HDMI cable pins for bends, disconnect and firmly reseat both ends.
4. If image remains blank, cycle the projector input to 'HDMI 2' and back to 'HDMI 1' to refresh the handshake.

Page 3: Blurry Image, Aspect Ratio & Color Distortion
1. Use the manual Focus Ring located above the projector lens to adjust text sharpness.
2. Press the 'Aspect' button on the remote and ensure it is configured to '16:9 widescreen'.
3. For keystone distortion, enter Menu -> Geometry Correction -> Auto Keystone to square the image.
4. If projector shuts off automatically after 5 minutes with a red flashing Temp LED, the intake air filter is obstructed; escalate to a technician for vacuum cleaning.""",
        ),
        "smart_board_sop.txt": (
            "SMART Board & Interactive Display Operating Procedure",
            "smart_board",
            """Campus AV Department - Interactive Smart Board Standard Operating Procedure (SOP-SB-02)
Page 1: Touch Screen & Interactive Stylus Calibration
1. Verify the USB touch cable (Type-A to Type-B) is securely plugged into both the teacher PC and the interactive board panel port labeled 'Touch Out 1'.
2. If the stylus coordinates are misaligned or offset from your finger touch, open the 'SMART Settings' app from the desktop system tray and select 'Calibrate Screen'.
3. Firmly press the center of each of the 9 target crosshairs shown sequentially on the board until a green checkmark appears.
4. Ensure no physical obstruction, stickers, or dry erase dust blocks the optical sensors along the internal bezel edges.

Page 2: Blank Screen & OPS Internal PC Troubleshooting
1. Ensure the rocker master power switch beneath the bottom-right frame is flipped to 'I' (ON).
2. Tap the power icon on the front convenience panel to wake the display from standby.
3. If using the built-in OPS slot PC, tap 'Source' on the front panel and select 'OPS' or 'PC'.
4. If the screen displays 'No Cable Connected', verify that the external HDMI 1 cable is firmly seated and toggle the input selector.

Page 3: Wireless Casting & Annotation Freeze
1. For AirPlay and Miracast wireless casting, ensure your laptop is connected to the 'Campus-Faculty-WiFi' subnet.
2. If the annotation overlay freezes, press the physical 'Home' button on the front control panel and restart the Whiteboard app.
3. Never use abrasive chemical cleaners or standard dry erase markers on interactive capacitive surfaces.""",
        ),
        "microphone_audio_sop.txt": (
            "Shure Wireless Microphone & Podium Audio Operating Guide",
            "microphone",
            """Campus AV Department - Classroom Audio & Microphone Standard Operating Procedure (SOP-MIC-03)
Page 1: Wireless Lapel & Handheld Microphone Setup
1. Slide open the transmitter battery compartment and verify two fresh AA alkaline batteries are inserted with correct polarity (+ / -).
2. Slide the transmitter power switch to 'ON'. A green LED indicates adequate battery level; red LED indicates under 30 minutes remaining.
3. Confirm that the wireless receiver channel in the podium rack matches the transmitter frequency group (Default: Group 1, Channel 4).
4. Verify the RF signal indicator LED on the podium receiver illuminates green when the mic is switched on.

Page 2: No Sound & Audio Muting Checks
1. Check the physical toggle switch on top of the transmitter pack; verify it is NOT set to 'MUTE'.
2. Check the podium master mixer console: Ensure the 'MIC 1' fader is raised to the '0 dB' unity mark.
3. Verify the master 'Mute All' button on the podium touch panel is toggled OFF (illuminated green, not red).
4. If audio is still absent, inspect the lavalier microphone mini-XLR cable connector into the bodypack and tighten the locking collar.

Page 3: Feedback Squeal, Static & Acoustic Interference
1. To stop immediate feedback howling, pull down the podium MIC fader by 6 dB and step away from the overhead speakers.
2. Keep lapel microphone clipped 6 to 8 inches below your mouth, pointing upwards toward the chin.
3. If intermittent crackling or static occurs, switch the wireless receiver channel to Channel 6 to avoid Wi-Fi band congestion.""",
        ),
        "wall_speakers_sop.txt": (
            "Classroom Wall Mounted Speakers & Mixer Amplifier SOP",
            "speaker",
            """Campus AV Department - Wall Mounted Sound System SOP (SOP-SPK-04)
Page 1: Power & Volume Levels
1. Ensure the amplifier in the podium equipment rack has its power switch ON (Blue pilot light).
2. Check the master output volume knob on the amplifier faceplate; set between 10 o'clock and 12 o'clock positions.
3. If sound is missing from PC playback, verify the computer audio output device is set to 'Crestron / Extron AV Audio (HDMI)'.
4. Ensure the PC operating system volume is set to 80% and unmuted in the Windows taskbar.

Page 2: Distorted or Buzzing Sound
1. If an audible ground hum (60Hz buzz) occurs when connecting a 3.5mm aux jack, flip the 'Ground Lift' switch on the podium DI box.
2. Replace damaged 3.5mm stereo patch cables.
3. Ensure no high-power laptop chargers or mobile phones rest directly upon the audio mixer enclosure.""",
        ),
        "display_monitor_sop.txt": (
            "Classroom Auxiliary Display & Large Screen Monitor SOP",
            "display",
            """Campus AV Department - Commercial Display Panel SOP (SOP-DSP-05)
Page 1: Screen Power & HDMI Source Detection
1. Use the commercial display remote control to power on the 75-inch wall display.
2. If the screen displays 'No Signal', confirm the HDMI switcher behind the podium is outputting to Display Port 1.
3. If the display power LED flashes continuously without showing video, disconnect the AC power cord from the wall outlet for 15 seconds to perform a power cycle.""",
        ),
    }

    processor = ManualDocumentProcessor(chunk_size=400, chunk_overlap=60)
    all_chunks = []

    for filename, (title, category, content) in manuals.items():
        file_path = MANUALS_DIR / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        doc_rec = register_knowledge_document(
            title=title,
            filename=filename,
            file_type="txt",
            file_path=str(file_path),
            total_chunks=0,
            uploaded_by="campus_av_admin",
            metadata={"equipment_category": category},
        )

        chunks = processor.process_file(
            file_path=file_path,
            doc_id=doc_rec["id"],
            title=title,
            equipment_category=category,
        )
        all_chunks.extend(chunks)

    vector_store.add_chunks(all_chunks)
    print(f"[Seed] Ingested {len(all_chunks)} verified SOP chunks into vector store.")


def seed_campus_infrastructure():
    """Seed campus blocks, classrooms, technicians, and exact demo complaints from Figma Make."""
    init_database()

    with db_session() as conn:
        conn.execute("DELETE FROM complaint_events")
        conn.execute("DELETE FROM troubleshooting_steps")
        conn.execute("DELETE FROM chat_messages")
        conn.execute("DELETE FROM notifications")
        conn.execute("DELETE FROM complaints")
        conn.execute("DELETE FROM technician_assignments")
        conn.execute("DELETE FROM classrooms")
        conn.execute("DELETE FROM blocks")
        conn.execute("DELETE FROM technicians")
        conn.execute("DELETE FROM users")

    print("[Seed] Creating Campus Users, Blocks, Classrooms, and Technicians matching Figma Make...")

    # 1. Users with hashed passwords
    admin_priya = create_user("priya_admin", "Priya Sharma", "priya@campus.edu", "admin", "IT Administration", password="Admin@123")
    prof_elena = create_user("elena_teacher", "Prof. Elena Rostova", "elena@campus.edu", "teacher", "Science Department", password="Teacher@123")
    tech_alex = create_user("alex_tech", "Alex Morgan", "alex.tech@campus.edu", "technician", "AV Engineering", password="Tech@123")

    # Additional standard demo accounts
    create_user("admin", "Campus Administrator", "admin@campus.edu", "admin", "IT Administration", password="Admin@123")
    create_user("teacher1", "Faculty Member", "teacher1@campus.edu", "teacher", "Academic Department", password="Teacher@123")
    create_user("tech1", "Lead AV Technician", "tech1@campus.edu", "technician", "AV Support", password="Tech@123")

    # 2. Campus Blocks matching Figma Make
    block_science = create_block("SCI", "Science Block", "Science and Physics Complex")
    block_eng = create_block("ENG", "Engineering Block", "Main Engineering Hall")
    block_lib = create_block("LIB", "Library Block", "Campus Central Library")

    # 3. Classrooms matching Figma Make
    cr_s204 = create_classroom(block_science["id"], "S-204", "Lecture Hall", floor=2, qr_token="QR-ROOM-S204")
    cr_e112 = create_classroom(block_eng["id"], "E-112", "Seminar Room", floor=1, qr_token="QR-ROOM-E112")
    cr_l101 = create_classroom(block_lib["id"], "L-101", "Auditorium", floor=1, qr_token="QR-ROOM-L101")

    # 4. Technician Alex Morgan
    alex = create_technician(
        full_name="Alex Morgan",
        phone_number="+1-555-019-8833",
        email="alex.tech@campus.edu",
        specialty="Campus AV Operations",
        user_id=tech_alex["id"],
    )

    # 5. Routing Assignments
    assign_technician(alex["id"], block_id=block_science["id"])
    assign_technician(alex["id"], block_id=block_eng["id"])
    assign_technician(alex["id"], block_id=block_lib["id"])

    # 6. Seed the EXACT 4 Complaints from Figma Make:
    # DEMO-AV-0180: Projector S-204 (Resolved)
    c0 = create_complaint(
        classroom_id=cr_s204["id"],
        device_type="projector",
        device_model="Epson PowerLite 119W",
        problem_description="Projector lamp timer reset completed successfully.",
        urgency="Normal",
        reporter_user_id=prof_elena["id"],
    )
    with db_session() as conn:
        conn.execute("UPDATE complaints SET complaint_code = 'DEMO-AV-0180' WHERE id = ?", (c0["id"],))
    update_complaint_status(c0["id"], "resolved", "Alex Morgan", "technician", resolution_notes="Lamp reset verified.")

    # DEMO-AV-0181: Speaker L-101 (Escalated)
    c1 = create_complaint(
        classroom_id=cr_l101["id"],
        device_type="speaker",
        device_model="Wall Mounted PA",
        problem_description="No audio from ceiling speakers",
        urgency="High",
        reporter_user_id=prof_elena["id"],
    )
    with db_session() as conn:
        conn.execute("UPDATE complaints SET complaint_code = 'DEMO-AV-0181' WHERE id = ?", (c1["id"],))
    update_complaint_status(c1["id"], "escalated", "Alex Morgan", "technician", resolution_notes="Escalated for ceiling wiring repair.")

    # DEMO-AV-0182: Projector S-204 (In progress)
    c2 = create_complaint(
        classroom_id=cr_s204["id"],
        device_type="projector",
        device_model="Epson PowerLite",
        problem_description="The projector is on, but it says no signal...",
        urgency="Normal",
        reporter_user_id=prof_elena["id"],
    )
    with db_session() as conn:
        conn.execute("UPDATE complaints SET complaint_code = 'DEMO-AV-0182' WHERE id = ?", (c2["id"],))
    update_complaint_status(c2["id"], "in_progress", "Alex Morgan", "technician", resolution_notes="Testing HDMI splitter.")

    # DEMO-AV-0183: Microphone E-112 (Pending)
    c3 = create_complaint(
        classroom_id=cr_e112["id"],
        device_type="microphone",
        device_model="Shure BLX4",
        problem_description="Wireless microphone has intermittent audio",
        urgency="Normal",
        reporter_user_id=prof_elena["id"],
    )
    with db_session() as conn:
        conn.execute("UPDATE complaints SET complaint_code = 'DEMO-AV-0183' WHERE id = ?", (c3["id"],))

    print("[Seed] Successfully seeded campus infrastructure matching Figma Make.")


if __name__ == "__main__":
    init_database()
    seed_campus_infrastructure()
    seed_sample_manuals()
    print("[Seed] Database and Knowledge Base initialization complete.")
