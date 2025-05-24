import streamlit as st
import bcrypt
from datetime import datetime, date
from bson import ObjectId  # For handling MongoDB's _id

# Import database connection and helper functions from db.py
from db import (
    MongoDBConnection, generate_unique_id,
    get_users_collection, get_rooms_collection, get_room_requests_collection,
    get_maintenance_collection, get_events_collection, get_fees_collection,
    get_visitors_collection, get_feedback_collection
)

# --- Initialize DB Connection ---
# This will create the connection if it doesn't exist or return the existing one
try:
    db_connection = MongoDBConnection()
except Exception as e:
    st.error(f"Failed to connect to database: {e}")
    st.stop()

# --- Password Hashing ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

# --- User Management Functions ---
def register_user(name, email, password, role):
    users_collection = get_users_collection()
    try:
        if users_collection.find_one({"email": email}):
            return False, "Email already exists."
        if role == "admin":
            if users_collection.find_one({"role": "admin"}):
                return False, "Admin already exists. Only one admin allowed."

        hashed_password = hash_password(password)
        user_id_val = ""
        while True:
            user_id_val = generate_unique_id()
            if not users_collection.find_one({"userId": user_id_val}):
                break

        user_data = {
            "userId": user_id_val,
            "name": name,
            "email": email,
            "password": hashed_password,
            "role": role,
            "createdAt": datetime.utcnow()
        }
        users_collection.insert_one(user_data)
        return True, "User registered successfully."
    except pymongo.errors.DuplicateKeyError:
        return False, "Registration failed: Email or UserID already exists (race condition or index issue)."
    except Exception as e:
        return False, f"Registration failed: {str(e)}"

def login_user(email, password):
    users_collection = get_users_collection()
    try:
        user = users_collection.find_one({"email": email})
        if user and check_password(password, user["password"]):
            # Convert ObjectId to string for session state
            user['_id'] = str(user['_id'])
            return user
        return None
    except Exception as e:
        st.error(f"Login failed: {str(e)}")
        return None

# --- Helper to get user by _id (string) ---
def get_user_by_id_str(user_id_str):
    users_collection = get_users_collection()
    try:
        return users_collection.find_one({"_id": ObjectId(user_id_str)})
    except:
        return None

def get_user_by_custom_id(custom_user_id):
    users_collection = get_users_collection()
    return users_collection.find_one({"userId": custom_user_id})

# --- Streamlit App State Initialization ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.page = "Login"  # Default page

# --- UI Functions ---

def display_login_page():
    st.title("Hostel Management Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")

        if submit_button:
            user = login_user(email, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.session_state.page = "Dashboard"
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid email or password.")

    if st.button("Go to Register"):
        st.session_state.page = "Register"
        st.rerun()

def display_register_page():
    st.title("Hostel Management Registration")
    with st.form("register_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["student", "staff", "admin"])
        submit_button = st.form_submit_button("Register")

        if submit_button:
            if not all([name, email, password, role]):
                st.error("Please fill all fields.")
            else:
                success, message = register_user(name, email, password, role)
                if success:
                    st.success(message + " Please login.")
                    st.session_state.page = "Login"
                    st.rerun()
                else:
                    st.error(message)

    if st.button("Go to Login"):
        st.session_state.page = "Login"
        st.rerun()

# --- Room Management UI & Logic ---
def display_room_management():
    st.subheader("Room Management")
    rooms_collection = get_rooms_collection()
    users_collection = get_users_collection()

    # Add Room Form (Admin only)
    if st.session_state.user['role'] == 'admin':
        with st.expander("Add New Room", expanded=False):
            with st.form("add_room_form", clear_on_submit=True):
                number = st.text_input("Room Number")
                room_type = st.selectbox("Room Type", ["single", "double", "triple"])
                hostel_block = st.selectbox("Hostel Block", ["Block A", "Block B", "Block C"])
                assign_user_id_str = st.text_input("Assign to User's Custom ID (Optional)")

                submitted = st.form_submit_button("Add Room")
                if submitted:
                    if not number or not room_type or not hostel_block:
                        st.error("Room number, type, and block are required.")
                    else:
                        try:
                            if rooms_collection.find_one({"number": number}):
                                st.error("Room number already exists.")
                            else:
                                user_to_assign = None
                                user_mongo_id = None
                                if assign_user_id_str:
                                    user_to_assign = users_collection.find_one({"userId": assign_user_id_str})
                                    if not user_to_assign:
                                        st.error(f"User with custom ID '{assign_user_id_str}' not found.")
                                    else:
                                        # Check if this user already has a room
                                        if rooms_collection.find_one({"userId": user_to_assign['_id']}):
                                            st.error(f"User {user_to_assign['name']} already has a room assigned.")
                                            user_to_assign = None
                                        else:
                                            user_mongo_id = user_to_assign['_id']

                                if assign_user_id_str and not user_to_assign:
                                    pass
                                else:
                                    room_data = {
                                        "number": number,
                                        "roomType": room_type,
                                        "hostelBlock": hostel_block,
                                        "userId": user_mongo_id,
                                        "status": "occupied" if user_mongo_id else "available",
                                        "createdAt": datetime.utcnow()
                                    }
                                    rooms_collection.insert_one(room_data)
                                    st.success(f"Room {number} added successfully.")
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Failed to add room: {str(e)}")

    # Display Rooms
    st.markdown("---")
    st.write("**Existing Rooms:**")

    query = {}
    if st.session_state.user['role'] == 'student':
        query = {"userId": ObjectId(st.session_state.user['_id'])}

    try:
        all_rooms = list(rooms_collection.find(query).sort("number"))
    except Exception as e:
        st.error(f"Failed to fetch rooms: {str(e)}")
        return

    if not all_rooms and st.session_state.user['role'] == 'student':
        st.info("You have not been assigned a room yet.")
    elif not all_rooms:
        st.info("No rooms found.")
    else:
        cols = st.columns([1,1,1,1,2,2] if st.session_state.user['role'] == 'admin' else [1,1,1,1])
        headers = ["Number", "Type", "Block", "Status"]
        if st.session_state.user['role'] == 'admin':
            headers.extend(["Assigned To", "Actions"])

        for col, header_text in zip(cols, headers):
            col.markdown(f"**{header_text}**")

        for room in all_rooms:
            cols = st.columns([1,1,1,1,2,2] if st.session_state.user['role'] == 'admin' else [1,1,1,1])
            cols[0].write(room['number'])
            cols[1].write(room['roomType'])
            cols[2].write(room['hostelBlock'])
            cols[3].write(room['status'])

            if st.session_state.user['role'] == 'admin':
                assigned_user_info = "N/A"
                if room.get('userId'):
                    user_assigned = users_collection.find_one({"_id": room['userId']})
                    if user_assigned:
                        assigned_user_info = f"{user_assigned['name']} ({user_assigned['userId']})"
                cols[4].write(assigned_user_info)

                action_placeholder = cols[5].empty()  # For buttons
                if action_placeholder.button("Edit", key=f"edit_room_{room['_id']}", type="secondary"):
                    st.session_state.editing_room_id = str(room['_id'])
                    st.rerun()

                if room['status'] == 'occupied':
                    if action_placeholder.button("Unassign", key=f"unassign_{room['_id']}", type="secondary"):
                        try:
                            rooms_collection.update_one(
                                {"_id": room['_id']},
                                {"$set": {"userId": None, "status": "available"}}
                            )
                            st.toast(f"Room {room['number']} unassigned.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to unassign room: {str(e)}")

                if action_placeholder.button("Delete", key=f"delete_room_{room['_id']}", type="primary"):
                    if room['status'] == 'occupied':
                        st.warning("Cannot delete occupied room. Unassign user first.")
                    else:
                        try:
                            rooms_collection.delete_one({"_id": room['_id']})
                            st.toast(f"Room {room['number']} deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete room: {str(e)}")

        # Edit form for Room
        if 'editing_room_id' in st.session_state and st.session_state.editing_room_id:
            try:
                room_to_edit = rooms_collection.find_one({"_id": ObjectId(st.session_state.editing_room_id)})
                if room_to_edit:
                    st.markdown("---")
                    st.subheader(f"Edit Room: {room_to_edit['number']}")
                    with st.form(f"edit_room_form_{room_to_edit['_id']}", clear_on_submit=True):
                        current_user_obj_id = room_to_edit.get('userId')
                        current_user_custom_id = ""
                        if current_user_obj_id:
                            user_doc = users_collection.find_one({"_id": current_user_obj_id})
                            if user_doc:
                                current_user_custom_id = user_doc['userId']

                        new_number = st.text_input("Room Number", value=room_to_edit['number'])
                        new_room_type = st.selectbox("Room Type", ["single", "double", "triple"], index=["single", "double", "triple"].index(room_to_edit['roomType']))
                        new_hostel_block = st.selectbox("Hostel Block", ["Block A", "Block B", "Block C"], index=["Block A", "Block B", "Block C"].index(room_to_edit['hostelBlock']))
                        new_assign_user_id_str = st.text_input("Assign to User's Custom ID (Optional)", value=current_user_custom_id)

                        save_changes = st.form_submit_button("Save Changes")
                        cancel_edit = st.form_submit_button("Cancel")

                        if save_changes:
                            try:
                                updated_user_mongo_id = None
                                new_status = "available"

                                if new_number != room_to_edit['number'] and rooms_collection.find_one({"number": new_number}):
                                    st.error(f"Room number '{new_number}' already exists.")
                                else:
                                    if new_assign_user_id_str:
                                        user_to_assign_new = users_collection.find_one({"userId": new_assign_user_id_str})
                                        if not user_to_assign_new:
                                            st.error(f"User with custom ID '{new_assign_user_id_str}' not found.")
                                        else:
                                            existing_room_for_new_user = rooms_collection.find_one({"userId": user_to_assign_new['_id'], "_id": {"$ne": room_to_edit['_id']}})
                                            if existing_room_for_new_user:
                                                st.error(f"User {user_to_assign_new['name']} is already assigned to room {existing_room_for_new_user['number']}.")
                                            else:
                                                updated_user_mongo_id = user_to_assign_new['_id']
                                                new_status = "occupied"

                                    if new_assign_user_id_str and not updated_user_mongo_id and (not current_user_obj_id or (current_user_obj_id and users_collection.find_one({"_id": current_user_obj_id, "userId": new_assign_user_id_str}) is None)):
                                        pass
                                    else:
                                        rooms_collection.update_one(
                                            {"_id": room_to_edit['_id']},
                                            {"$set": {
                                                "number": new_number,
                                                "roomType": new_room_type,
                                                "hostelBlock": new_hostel_block,
                                                "userId": updated_user_mongo_id,
                                                "status": new_status
                                            }}
                                        )
                                        st.success(f"Room {new_number} updated.")
                                        del st.session_state.editing_room_id
                                        st.rerun()
                            except Exception as e:
                                st.error(f"Failed to update room: {str(e)}")
                        if cancel_edit:
                            del st.session_state.editing_room_id
                            st.rerun()
            except Exception as e:
                st.error(f"Failed to fetch room for editing: {str(e)}")

# --- Room Request UI & Logic ---
def display_room_requests():
    st.subheader("Room Requests")
    req_collection = get_room_requests_collection()
    rooms_collection = get_rooms_collection()
    users_collection = get_users_collection()
    current_user_id = ObjectId(st.session_state.user['_id'])

    if st.session_state.user['role'] == 'student':
        # Check if student already has a room
        if rooms_collection.find_one({"userId": current_user_id}):
            st.info("You already have a room assigned.")
            return

        # Check for existing pending request
        existing_request = req_collection.find_one({"userId": current_user_id, "status": "pending"})
        if existing_request:
            st.info("You have a pending room request.")
        else:
            if st.button("Request a Room"):
                try:
                    req_collection.insert_one({
                        "userId": current_user_id,
                        "status": "pending",
                        "requestedAt": datetime.utcnow()
                    })
                    st.success("Room request submitted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to submit room request: {str(e)}")

        my_requests = list(req_collection.find({"userId": current_user_id}).sort("requestedAt", -1))
        if my_requests:
            st.write("My Room Requests:")
            for req in my_requests:
                st.write(f"- Status: {req['status'].capitalize()} (Requested: {req['requestedAt'].strftime('%Y-%m-%d %H:%M')})")

    elif st.session_state.user['role'] == 'admin':
        st.write("Pending Room Requests:")
        pending_requests = list(req_collection.find({"status": "pending"}))
        if not pending_requests:
            st.info("No pending room requests.")
            return

        # Track active request being processed
        if 'active_request_id' not in st.session_state:
            st.session_state.active_request_id = None

        for req in pending_requests:
            user_requesting = users_collection.find_one({"_id": req['userId']})
            if user_requesting:
                st.markdown(f"**Request from: {user_requesting['name']} ({user_requesting['userId']})**")

                # Check if user already assigned a room
                if rooms_collection.find_one({"userId": req['userId']}):
                    st.warning(f"User {user_requesting['name']} already has a room. This request should be rejected or investigated.")
                    if st.button("Reject Invalid Request", key=f"reject_invalid_{req['_id']}", type="primary"):
                        try:
                            req_collection.update_one({"_id": req['_id']}, {"$set": {"status": "rejected"}})
                            st.toast("Request rejected.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to reject request: {str(e)}")
                    continue

                if st.button("Process Request", key=f"process_{req['_id']}"):
                    st.session_state.active_request_id = str(req['_id'])
                    st.rerun()

                # Show form for the active request
                if st.session_state.active_request_id == str(req['_id']):
                    with st.expander(f"Assign Room for: {user_requesting['name']}", expanded=True):
                        available_rooms = list(rooms_collection.find({"status": "available"}))
                        if not available_rooms:
                            st.warning("No available rooms to assign.")
                            if st.button("Reject (No Rooms)", key=f"reject_no_room_{req['_id']}"):
                                try:
                                    req_collection.update_one({"_id": req['_id']}, {"$set": {"status": "rejected"}})
                                    st.session_state.active_request_id = None
                                    st.toast("Request rejected.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to reject request: {str(e)}")
                            if st.button("Cancel", key=f"cancel_approve_{req['_id']}"):
                                st.session_state.active_request_id = None
                                st.rerun()
                        else:
                            room_options = {f"{r['number']} ({r['roomType']}, {r['hostelBlock']})": str(r['_id']) for r in available_rooms}
                            selected_room_id_str = st.selectbox("Select Room to Assign", options=room_options.keys(), key=f"room_select_{req['_id']}")

                            if st.button("Approve and Assign", key=f"approve_{req['_id']}"):
                                try:
                                    room_id_to_assign = ObjectId(room_options[selected_room_id_str])
                                    rooms_collection.update_one(
                                        {"_id": room_id_to_assign},
                                        {"$set": {"userId": req['userId'], "status": "occupied"}}
                                    )
                                    req_collection.update_one(
                                        {"_id": req['_id']},
                                        {"$set": {"status": "approved", "assignedRoomId": room_id_to_assign}}
                                    )
                                    st.session_state.active_request_id = None
                                    st.success(f"Room assigned to {user_requesting['name']}.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to assign room: {str(e)}")

                            if st.button("Reject Request", key=f"reject_{req['_id']}", type="primary"):
                                try:
                                    req_collection.update_one({"_id": req['_id']}, {"$set": {"status": "rejected"}})
                                    st.session_state.active_request_id = None
                                    st.toast("Request rejected.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to reject request: {str(e)}")

                            if st.button("Cancel", key=f"cancel_dialog_{req['_id']}"):
                                st.session_state.active_request_id = None
                                st.rerun()
                st.markdown("---")

# --- Maintenance UI & Logic ---
def display_maintenance_requests():
    st.subheader("Maintenance Requests")
    maint_collection = get_maintenance_collection()
    users_collection = get_users_collection()
    current_user_id = ObjectId(st.session_state.user['_id'])
    user_role = st.session_state.user['role']

    # Submit new request form
    if user_role == 'student' or user_role == 'staff':
        with st.expander("Submit New Maintenance Request", expanded=False):
            with st.form("new_maint_req_form", clear_on_submit=True):
                description = st.text_area("Describe the issue")
                submit_req = st.form_submit_button("Submit Request")
                if submit_req and description:
                    try:
                        maint_collection.insert_one({
                            "userId": current_user_id,
                            "description": description,
                            "status": "Pending",
                            "assignedStaff": None,
                            "createdAt": datetime.utcnow()
                        })
                        st.success("Maintenance request submitted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to submit maintenance request: {str(e)}")
                elif submit_req and not description:
                    st.error("Description cannot be empty.")

    st.markdown("---")
    st.write("**Existing Maintenance Requests:**")

    query = {}
    if user_role == 'student':
        query = {"userId": current_user_id}

    try:
        all_requests = list(maint_collection.find(query).sort("createdAt", -1))
    except Exception as e:
        st.error(f"Failed to fetch maintenance requests: {str(e)}")
        return

    if not all_requests:
        st.info("No maintenance requests found.")
    else:
        for req in all_requests:
            user_who_requested = users_collection.find_one({"_id": req['userId']})
            requested_by_info = f"{user_who_requested['name']} ({user_who_requested['userId']})" if user_who_requested else "Unknown User"

            card_cols = st.columns([3,2,2])
            with card_cols[0]:
                st.markdown(f"**Description:** {req['description']}")
                st.caption(f"Requested on: {req['createdAt'].strftime('%Y-%m-%d %H:%M')}")
            with card_cols[1]:
                st.markdown(f"**Requested by:** {requested_by_info}")

            with card_cols[2]:
                current_status = req['status']
                st.markdown(f"**Status:** {current_status}")

                if user_role == 'admin' or user_role == 'staff':
                    new_status = st.selectbox(
                        "Update Status",
                        options=["Pending", "In Progress", "Completed"],
                        index=["Pending", "In Progress", "Completed"].index(current_status),
                        key=f"status_maint_{req['_id']}"
                    )
                    if new_status != current_status:
                        try:
                            maint_collection.update_one(
                                {"_id": req['_id']},
                                {"$set": {"status": new_status}}
                            )
                            st.toast(f"Request status updated to {new_status}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update request status: {str(e)}")

                    if user_role == 'admin':
                        if st.button("Delete Request", key=f"del_maint_{req['_id']}", type="primary"):
                            try:
                                maint_collection.delete_one({"_id": req['_id']})
                                st.toast("Maintenance request deleted.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to delete request: {str(e)}")
            st.markdown("---")

# --- Event Management (Admin Creates, All View) ---
def display_events():
    st.subheader("Hostel Events")
    events_collection = get_events_collection()
    user_role = st.session_state.user['role']

    if user_role == 'admin':
        with st.expander("Add New Event", expanded=False):
            with st.form("new_event_form", clear_on_submit=True):
                title = st.text_input("Event Title")
                event_date_input = st.date_input("Event Date", value=date.today())
                submit_event = st.form_submit_button("Add Event")

                if submit_event and title and event_date_input:
                    try:
                        event_datetime = datetime.combine(event_date_input, datetime.min.time())
                        events_collection.insert_one({
                            "title": title,
                            "date": event_datetime,
                            "createdAt": datetime.utcnow()
                        })
                        st.success(f"Event '{title}' added.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add event: {str(e)}")
                elif submit_event:
                    st.error("Title and Date are required.")

    st.markdown("---")
    st.write("**Upcoming & Past Events:**")
    try:
        all_events = list(events_collection.find().sort("date", -1))
    except Exception as e:
        st.error(f"Failed to fetch events: {str(e)}")
        return

    if not all_events:
        st.info("No events scheduled.")
    else:
        if 'active_event_id' not in st.session_state:
            st.session_state.active_event_id = None

        for event in all_events:
            st.markdown(f"#### {event['title']}")
            st.caption(f"Date: {event['date'].strftime('%Y-%m-%d')}")
            if user_role == 'admin':
                if st.button("Edit", key=f"edit_event_btn_{event['_id']}", type="secondary"):
                    st.session_state.active_event_id = str(event['_id'])
                    st.rerun()

                if st.session_state.active_event_id == str(event['_id']):
                    with st.expander(f"Edit Event: {event['title']}", expanded=True):
                        new_title = st.text_input("Event Title", value=event['title'], key=f"edit_title_{event['_id']}")
                        new_date_input = st.date_input("Event Date", value=event['date'].date(), key=f"edit_date_{event['_id']}")

                        if st.button("Save Changes", key=f"save_event_{event['_id']}"):
                            if new_title and new_date_input:
                                try:
                                    new_event_datetime = datetime.combine(new_date_input, datetime.min.time())
                                    events_collection.update_one(
                                        {"_id": event['_id']},
                                        {"$set": {"title": new_title, "date": new_event_datetime}}
                                    )
                                    st.session_state.active_event_id = None
                                    st.success("Event updated.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to update event: {str(e)}")
                            else:
                                st.error("Title and date are required.")

                        if st.button("Cancel", key=f"cancel_edit_event_{event['_id']}"):
                            st.session_state.active_event_id = None
                            st.rerun()

                if st.button("Delete Event", key=f"del_event_{event['_id']}", type="primary"):
                    try:
                        events_collection.delete_one({"_id": event['_id']})
                        st.toast(f"Event '{event['title']}' deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete event: {str(e)}")
            st.markdown("---")

# --- Fee Management (Admin Creates/Manages, Student Views) ---
def display_fees():
    st.subheader("Fee Management")
    fees_collection = get_fees_collection()
    users_collection = get_users_collection()
    user_role = st.session_state.user['role']
    current_user_id = ObjectId(st.session_state.user['_id'])

    if user_role == 'admin':
        with st.expander("Add New Fee Record", expanded=False):
            with st.form("new_fee_form", clear_on_submit=True):
                all_users = list(users_collection.find({"role": "student"}, {"userId": 1, "name": 1, "_id": 1}))
                user_options = {f"{u['name']} ({u['userId']})": str(u['_id']) for u in all_users}

                selected_user_display = st.selectbox("Select Student", options=user_options.keys())
                amount = st.number_input("Amount ($)", min_value=0.01, step=0.01)
                due_date_input = st.date_input("Due Date", value=date.today())
                initial_status = st.selectbox("Status", ["Pending", "Paid"])
                submit_fee = st.form_submit_button("Add Fee Record")

                if submit_fee and selected_user_display and amount and due_date_input:
                    try:
                        student_mongo_id = ObjectId(user_options[selected_user_display])
                        due_datetime = datetime.combine(due_date_input, datetime.min.time())
                        fees_collection.insert_one({
                            "userId": student_mongo_id,
                            "amount": amount,
                            "dueDate": due_datetime,
                            "status": initial_status,
                            "createdAt": datetime.utcnow()
                        })
                        st.success("Fee record added.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add fee record: {str(e)}")
                elif submit_fee:
                    st.error("All fields are required.")

    st.markdown("---")
    st.write("**Fee Records:**")

    query = {}
    if user_role == 'student':
        query = {"userId": current_user_id}

    try:
        all_fees = list(fees_collection.find(query).sort("dueDate", 1))
    except Exception as e:
        st.error(f"Failed to fetch fee records: {str(e)}")
        return

    if not all_fees:
        st.info("No fee records found.")
    else:
        for fee in all_fees:
            student_user = users_collection.find_one({"_id": fee['userId']})
            student_info = f"{student_user['name']} ({student_user['userId']})" if student_user else "N/A"

            fee_cols = st.columns([2,1,1,1,2] if user_role == 'admin' else [2,1,1,1])
            with fee_cols[0]:
                st.markdown(f"**Student:** {student_info}" if user_role == 'admin' else f"**Amount:** ${fee['amount']:.2f}")
            with fee_cols[1 if user_role == 'admin' else 0]:
                st.markdown(f"**Amount:** ${fee['amount']:.2f}" if user_role == 'admin' else f"**Due:** {fee['dueDate'].strftime('%Y-%m-%d')}")
            with fee_cols[2 if user_role == 'admin' else 1]:
                st.markdown(f"**Due:** {fee['dueDate'].strftime('%Y-%m-%d')}" if user_role == 'admin' else f"**Status:** {fee['status']}")
            with fee_cols[3 if user_role == 'admin' else 2]:
                current_fee_status = fee['status']
                st.markdown(f"**Status:** {current_fee_status}")

            if user_role == 'admin':
                with fee_cols[4]:
                    new_fee_status = st.selectbox(
                        "Update Status",
                        options=["Pending", "Paid"],
                        index=["Pending", "Paid"].index(current_fee_status),
                        key=f"status_fee_{fee['_id']}"
                    )
                    if new_fee_status != current_fee_status:
                        try:
                            fees_collection.update_one(
                                {"_id": fee['_id']},
                                {"$set": {"status": new_fee_status}}
                            )
                            st.toast(f"Fee status updated to {new_fee_status}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update fee status: {str(e)}")

                    if st.button("Delete Fee", key=f"del_fee_{fee['_id']}", type="primary"):
                        try:
                            fees_collection.delete_one({"_id": fee['_id']})
                            st.toast("Fee record deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete fee record: {str(e)}")
            st.markdown("---")

# --- Visitor Management (Student Registers, Staff Approves/Rejects, Admin can also view/manage) ---
def display_visitors():
    st.subheader("Visitor Management")
    visitors_collection = get_visitors_collection()
    user_role = st.session_state.user['role']

    if user_role == 'student':
        with st.expander("Register New Visitor", expanded=False):
            with st.form("new_visitor_form", clear_on_submit=True):
                name = st.text_input("Visitor Name")
                contact_number = st.text_input("Contact Number")
                visit_date_input = st.date_input("Proposed Visit Date", value=date.today())
                purpose = st.text_area("Purpose of Visit")
                submit_visitor = st.form_submit_button("Register Visitor")

                if submit_visitor and all([name, contact_number, visit_date_input, purpose]):
                    try:
                        visit_datetime = datetime.combine(visit_date_input, datetime.min.time())
                        visitors_collection.insert_one({
                            "registeredByStudentId": ObjectId(st.session_state.user['_id']),
                            "name": name,
                            "contactNumber": contact_number,
                            "visitDate": visit_datetime,
                            "purpose": purpose,
                            "status": "Pending",
                            "createdAt": datetime.utcnow()
                        })
                        st.success("Visitor registration submitted for approval.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to register visitor: {str(e)}")
                elif submit_visitor:
                    st.error("All fields are required.")

    st.markdown("---")
    st.write("**Visitor Log:**")

    query = {}
    if user_role == 'student':
        query = {"registeredByStudentId": ObjectId(st.session_state.user['_id'])}

    try:
        all_visitors = list(visitors_collection.find(query).sort("visitDate", -1))
    except Exception as e:
        st.error(f"Failed to fetch visitor records: {str(e)}")
        return

    if not all_visitors:
        st.info("No visitor records found.")
    else:
        for visitor in all_visitors:
            student_who_registered = get_user_by_id_str(str(visitor.get('registeredByStudentId')))
            registered_by_info = f"{student_who_registered['name']} ({student_who_registered['userId']})" if student_who_registered else "N/A"

            st.markdown(f"#### Visitor: {visitor['name']}")
            st.write(f"**Contact:** {visitor['contactNumber']}")
            st.write(f"**Proposed Visit Date:** {visitor['visitDate'].strftime('%Y-%m-%d')}")
            st.write(f"**Purpose:** {visitor['purpose']}")
            st.write(f"**Registered by:** {registered_by_info}")
            current_visitor_status = visitor['status']
            st.write(f"**Status:** {current_visitor_status}")

            if user_role == 'staff' or user_role == 'admin':
                if current_visitor_status == "Pending":
                    action_cols = st.columns(2)
                    if action_cols[0].button("Approve Visit", key=f"approve_visit_{visitor['_id']}", type="primary"):
                        try:
                            visitors_collection.update_one({"_id": visitor['_id']}, {"$set": {"status": "Approved"}})
                            st.toast(f"Visitor '{visitor['name']}' approved.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to approve visitor: {str(e)}")
                    if action_cols[1].button("Reject Visit", key=f"reject_visit_{visitor['_id']}", type="secondary"):
                        try:
                            visitors_collection.update_one({"_id": visitor['_id']}, {"$set": {"status": "Rejected"}})
                            st.toast(f"Visitor '{visitor['name']}' rejected.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to reject visitor: {str(e)}")

            if user_role == 'admin':
                if st.button("Delete Record", key=f"del_visitor_{visitor['_id']}", type="primary"):
                    try:
                        visitors_collection.delete_one({"_id": visitor['_id']})
                        st.toast(f"Visitor record for '{visitor['name']}' deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete visitor record: {str(e)}")
            st.markdown("---")

# --- Feedback (Student Submits, Admin Views) ---
def display_feedback():
    st.subheader("Feedback")
    feedback_collection = get_feedback_collection()
    user_role = st.session_state.user['role']

    if user_role == 'student':
        with st.form("new_feedback_form", clear_on_submit=True):
            feedback_text = st.text_area("Your Feedback")
            submit_feedback = st.form_submit_button("Submit Feedback")

            if submit_feedback and feedback_text:
                try:
                    feedback_collection.insert_one({
                        "userId": ObjectId(st.session_state.user['_id']),
                        "feedback": feedback_text,
                        "createdAt": datetime.utcnow()
                    })
                    st.success("Thank you for your feedback!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to submit feedback: {str(e)}")
            elif submit_feedback:
                st.error("Feedback cannot be empty.")

        st.markdown("---")
        st.write("**My Submitted Feedback:**")
        try:
            my_feedback = list(feedback_collection.find({"userId": ObjectId(st.session_state.user['_id'])}).sort("createdAt", -1))
        except Exception as e:
            st.error(f"Failed to fetch feedback: {str(e)}")
            return

        if not my_feedback:
            st.info("You have not submitted any feedback yet.")
        else:
            for fb in my_feedback:
                st.markdown(f"> {fb['feedback']}")
                st.caption(f"Submitted on: {fb['createdAt'].strftime('%Y-%m-%d %H:%M')}")
                st.markdown("---")

    elif user_role == 'admin':
        st.write("**All Submitted Feedback:**")
        try:
            all_feedback = list(feedback_collection.find().sort("createdAt", -1))
        except Exception as e:
            st.error(f"Failed to fetch feedback: {str(e)}")
            return

        if not all_feedback:
            st.info("No feedback submitted yet.")
        else:
            for fb in all_feedback:
                user_who_submitted = get_user_by_id_str(str(fb['userId']))
                submitted_by_info = f"{user_who_submitted['name']} ({user_who_submitted['userId']})" if user_who_submitted else "Unknown User"
                st.markdown(f"**From:** {submitted_by_info}")
                st.markdown(f"> {fb['feedback']}")
                st.caption(f"Submitted on: {fb['createdAt'].strftime('%Y-%m-%d %H:%M')}")
                st.markdown("---")

# --- Main Dashboard and Navigation ---
def display_dashboard():
    user = st.session_state.user
    st.sidebar.title(f"Welcome, {user['name']}")
    st.sidebar.write(f"Role: {user['role'].capitalize()}")
    st.sidebar.write(f"User ID: {user['userId']}")

    # Define navigation based on role
    menu_options = ["Profile"]
    if user['role'] == 'student':
        menu_options.extend(["My Room", "Room Requests", "Maintenance", "Events", "Fees", "Visitors", "Feedback"])
    elif user['role'] == 'staff':
        menu_options.extend(["Maintenance", "Visitors"])
    elif user['role'] == 'admin':
        menu_options.extend(["Room Management", "Room Requests", "Maintenance", "Events", "Fees", "Visitors", "Feedback", "User Management (View Only)"])

    if 'current_view' not in st.session_state:
        st.session_state.current_view = "Profile"

    st.session_state.current_view = st.sidebar.radio("Navigation", menu_options, index=menu_options.index(st.session_state.current_view))

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.page = "Login"
        keys_to_clear = ['current_view', 'editing_room_id', 'active_request_id', 'active_event_id']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    # Display content based on selection
    st.title(f"{st.session_state.current_view.replace('My ', '')} Dashboard")

    if st.session_state.current_view == "Profile":
        st.write(f"**Name:** {user['name']}")
        st.write(f"**Email:** {user['email']}")
        st.write(f"**Role:** {user['role'].capitalize()}")
        st.write(f"**Unique User ID:** {user['userId']}")

    elif st.session_state.current_view == "Room Management" and user['role'] == 'admin':
        display_room_management()
    elif st.session_state.current_view == "My Room" and user['role'] == 'student':
        display_room_management()

    elif st.session_state.current_view == "Room Requests":
        display_room_requests()

    elif st.session_state.current_view == "Maintenance":
        display_maintenance_requests()

    elif st.session_state.current_view == "Events":
        display_events()

    elif st.session_state.current_view == "Fees":
        display_fees()

    elif st.session_state.current_view == "Visitors":
        display_visitors()

    elif st.session_state.current_view == "Feedback":
        display_feedback()

    elif st.session_state.current_view == "User Management (View Only)" and user['role'] == 'admin':
        st.subheader("All Users")
        try:
            all_db_users = list(get_users_collection().find({}, {"password": 0}))
        except Exception as e:
            st.error(f"Failed to fetch users: {str(e)}")
            return
        if not all_db_users:
            st.info("No users found.")
        else:
            for u_db in all_db_users:
                st.write(f"**Name:** {u_db['name']}, **Email:** {u_db['email']}, **Role:** {u_db['role']}, **ID:** {u_db['userId']}")
                st.markdown("---")

# --- Main App Router ---
if not st.session_state.logged_in:
    if st.session_state.page == "Login":
        display_login_page()
    elif st.session_state.page == "Register":
        display_register_page()
else:
    display_dashboard()