from nicegui import Event
from nicegui.events import ClickEventArguments

# --- Common Events ---
User_logged_in = Event[str]()

# --- Session Viewer Events ---
History_session_clicked = Event[str]()
Delete_session_clicked = Event[str]()
Pin_session_clicked = Event[str]()
Edit_session_title_clicked = Event[str]()

# --- Chat Viewer Events ---
Copy_response_clicked = Event[str]()
Regenerate_response_clicked = Event[str]()
Like_response_clicked = Event[ClickEventArguments, str]()
Dislike_response_clicked = Event[ClickEventArguments, str]()
Download_response_clicked = Event[str]()
Show_message_citations_clicked = Event[str]()
