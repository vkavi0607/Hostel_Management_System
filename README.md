🏨 Hostel Management System
This is a web-based hostel management system built using Streamlit for the front-end and MongoDB as the database. It supports multiple user roles including admin, student, and staff, and allows for the management of rooms, maintenance, events, fees, visitors, and feedback.

🚀 Features:

👤 User Management:
Register/Login with role-based access (Admin/Student/Staff)
Password hashing using bcrypt
Single admin constraint

🛏️ Room Management:
Admin can create, assign, unassign, and delete rooms
Students can view their assigned room
Room requests with admin approval

🛠️ Maintenance Requests:
Students and staff can raise requests
Staff/Admin can update status
Admin can delete records

📅 Events:
Admin can add/edit/delete hostel events
All users can view events

💸 Fee Management:
Admin can assign fees to students
Students can view their fee status
Admin can mark fees as paid or pending

🧑‍🤝‍🧑 Visitor Management:
Students can register visitors
Staff/Admin can approve/reject

📝 Feedback:
Students can submit feedback
Admin can review all feedback

🧰 Tech Stack:
Frontend: Streamlit
Backend: Python
Database: MongoDB
Authentication: Passwords hashed using bcrypt

📁 Project Structure
bash
Copy
Edit
.
├── app.py                # Main Streamlit application
├── db.py                 # MongoDB connection & helper functions
├── .env                  # Environment variables (MONGO_URI)
├── requirements.txt      # Python dependencies
⚙️ Installation & Setup

1. Clone the Repository
git clone <repo_url>
cd <repo_folder>

2. Create a Virtual Environment
python -m venv venv
source venv/bin/activate

4. Install Dependencies
pip install -r requirements.txt

6. Set Up Environment Variables
Create a .env file in the root directory:
MONGO_URI=mongodb://localhost:27017/hostel_management
Ensure MongoDB is running locally and the database hostel_management_streamlit is created automatically on first access.

5. Run the Application
streamlit run app.py

🧪 MongoDB Index Setup (Optional)
To avoid duplicate entries, the system automatically sets up:
email and userId as unique in users collection
number as unique in rooms collection

You can verify indexes by running db.py directly:
python db.py

🛡️ Security Notes:
Passwords are securely hashed using bcrypt.
JWT is mentioned in requirements but not used — consider removing it or implementing token-based sessions.

✅ Future Enhancements
Email verification
Export reports (fees, visitors)
User notifications
Improved session/token handling

📬 Contact
For support or contributions, feel free to open issues or pull requests on the repository.
