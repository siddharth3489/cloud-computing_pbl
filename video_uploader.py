import streamlit as st
from google.cloud import storage
from firebase_admin import credentials, firestore, initialize_app
import firebase_admin
import uuid
import os

# ----------------------------
# FIREBASE SETUP
# ----------------------------

# Service account key (place in same folder)
KEY_PATH = "serviceAccountKey_cloud.json"

if not firebase_admin._apps:
    cred = credentials.Certificate(KEY_PATH)
    firebase_admin.initialize_app(cred, {
        "storageBucket": "cloudcomputingproject-2cee3.firebasestorage.app"
    })

db = firestore.client()
bucket = storage.Client.from_service_account_json(KEY_PATH).bucket("cloudcomputingproject-2cee3.firebasestorage.app")

st.title("🎬 EduStream — Video Creator & Editor")

st.markdown("Upload videos + metadata to Firebase Storage & Firestore.")

# ----------------------------
# FUNCTIONS
# ----------------------------

def upload_video_to_storage(file):
    """Upload file to Firebase Storage and return public URL."""
    file_id = str(uuid.uuid4())
    blob = bucket.blob(f"videos/{file_id}.mp4")
    blob.upload_from_file(file, content_type="video/mp4")

    # Make public
    blob.make_public()

    return blob.public_url, file_id


def save_video_metadata(doc_id, subject, topic, subtopic, title, url):
    """Save metadata in Firestore."""
    db.collection("videos").document(doc_id).set({
        "subject": subject,
        "topic": topic,
        "subtopic": subtopic,
        "title": title,
        "url": url
    })


def get_all_videos():
    docs = db.collection("videos").stream()
    collection = []
    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        collection.append(data)
    return collection


def delete_video(doc_id):
    db.collection("videos").document(doc_id).delete()


# ----------------------------
# VIDEO CREATOR (UPLOAD)
# ----------------------------

st.header("📤 Upload New Video")

with st.form("upload_form"):
    subject = st.text_input("Subject")
    topic = st.text_input("Topic")
    subtopic = st.text_input("Subtopic")
    title = st.text_input("Lecture Title")
    file = st.file_uploader("Select video file (.mp4)", type=["mp4"])

    uploaded = st.form_submit_button("Upload Video")

if uploaded:
    if not (subject and topic and subtopic and title and file):
        st.error("Please fill all fields and select a video.")
    else:
        with st.spinner("Uploading to Firebase..."):
            file_url, file_id = upload_video_to_storage(file)

            save_video_metadata(
                doc_id=file_id,
                subject=subject,
                topic=topic,
                subtopic=subtopic,
                title=title,
                url=file_url
            )

        st.success("Video uploaded successfully!")
        st.video(file_url)
        st.json({
            "subject": subject,
            "topic": topic,
            "subtopic": subtopic,
            "title": title,
            "url": file_url
        })

st.divider()

# ----------------------------
# VIDEO EDITOR (LIST + EDIT)
# ----------------------------

st.header("📝 Edit Existing Videos")

videos = get_all_videos()

if not videos:
    st.info("No videos uploaded yet.")
else:
    selected = st.selectbox(
        "Select video to edit",
        options=[v["title"] for v in videos]
    )

    selected_video = next(v for v in videos if v["title"] == selected)

    st.video(selected_video["url"])
    st.write("**Current Metadata:**")
    st.json(selected_video)

    # Editing fields
    with st.form("edit_form"):
        new_subject = st.text_input("Subject", selected_video["subject"])
        new_topic = st.text_input("Topic", selected_video["topic"])
        new_subtopic = st.text_input("Subtopic", selected_video["subtopic"])
        new_title = st.text_input("Lecture Title", selected_video["title"])

        save_changes = st.form_submit_button("Save Changes")
        delete_this = st.form_submit_button("❌ Delete Video", type="primary")

    if save_changes:
        save_video_metadata(
            doc_id=selected_video["id"],
            subject=new_subject,
            topic=new_topic,
            subtopic=new_subtopic,
            title=new_title,
            url=selected_video["url"]
        )
        st.success("Metadata updated successfully!")

    if delete_this:
        delete_video(selected_video["id"])
        st.warning("Video deleted!")
        st.rerun()
