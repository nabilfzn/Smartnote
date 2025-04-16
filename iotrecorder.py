
def microfon():
    import streamlit as st
    import requests
    import json
    import time
    import os
    import pandas as pd
    import datetime
    import base64
    from io import BytesIO
    from dotenv import load_dotenv
    import os
    load_dotenv()

    # Configuration variables
    FLASK_SERVER_URL = os.getenv("FLASK_SERVER")  # Change to your Flask server IP/port
    ESP32_URL = os.getenv("ESP32_URL")  # Change to your ESP32's IP address

    # Set page configuration
    # st.set_page_config(
    #     page_title="ESP32 Audio Recorder",
    #     page_icon="🎙️",
    #     layout="wide"
    # )

    # Helper function to make API calls to ESP32
    def call_esp32_api(endpoint, method="GET", data=None):
        try:
            url = f"{ESP32_URL}/{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=20)
            else:  # POST
                response = requests.post(url, json=data if data else {}, timeout=20)
            
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            st.error(f"Failed to connect to ESP32: {str(e)}")
            return None

    # Helper function to make API calls to Flask server
    def call_flask_api(endpoint, method="GET", data=None):
        try:
            url = f"{FLASK_SERVER_URL}/{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=5)
            else:  # POST
                response = requests.post(url, json=data if data else {}, timeout=5)
            
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            st.error(f"Failed to connect to Flask server: {str(e)}")
            return None

    # Function to create a download link for audio files
    def get_audio_download_link(file_path, file_name):
        try:
            with open(file_path, "rb") as file:
                audio_bytes = file.read()
            
            b64 = base64.b64encode(audio_bytes).decode()
            href = f'<a href="data:audio/wav;base64,{b64}" download="{file_name}">Download {file_name}</a>'
            return href
        except Exception as e:
            return f"Error creating download link: {str(e)}"

    # Function to add an audio player for a file
    def get_audio_player(file_path):
        try:
            with open(file_path, "rb") as file:
                audio_bytes = file.read()
            
            return st.audio(audio_bytes, format="audio/wav")
        except Exception as e:
            st.error(f"Error playing audio: {str(e)}")

    # Initialize session state variables
    if 'recording' not in st.session_state:
        st.session_state.recording = False
    if 'recording_start_time' not in st.session_state:
        st.session_state.recording_start_time = None
    if 'esp32_status' not in st.session_state:
        st.session_state.esp32_status = None
    if 'recording_duration' not in st.session_state:
        st.session_state.recording_duration = 0
    if 'last_file' not in st.session_state:
        st.session_state.last_file = None
    if 'last_status_check' not in st.session_state:
        st.session_state.last_status_check = 0
    if 'upload_status' not in st.session_state:
        st.session_state.upload_status = None  # None, "uploading", "success", "failed"
    if 'upload_file' not in st.session_state:
        st.session_state.upload_file = None

    # Create the app header
    st.title("🎙️ ESP32 Audio Recorder")
    st.markdown("Control your ESP32 microphone and manage recordings")

    # Create a layout with two columns
    col1, col2 = st.columns([1, 1])

    # ESP32 Control Panel (Left Column)
    with col1:
        st.header("Device Control")
        
        # Get ESP32 status
        if time.time() - st.session_state.last_status_check > 5:  # Check status every 5 seconds
            esp32_status = call_esp32_api("status")
            if esp32_status:
                st.session_state.esp32_status = esp32_status
                st.session_state.recording = esp32_status.get("isRecording", False)
                st.session_state.last_status_check = time.time()
        
        # Display device status
        esp_status = st.session_state.esp32_status
        
        if esp_status:
            st.subheader("Device Status")
            status_col1, status_col2 = st.columns(2)
            
            with status_col1:
                st.markdown(f"**SD Card:** {'✅ Connected' if esp_status.get('sdCardOK', False) else '❌ Not Connected'}")
                st.markdown(f"**Microphone:** {'✅ Working' if esp_status.get('microphoneOK', False) else '❌ Not Working'}")
            
            with status_col2:
                st.markdown(f"**WiFi:** {'✅ Connected' if esp_status.get('wifiConnected', False) else '❌ Not Connected'}")
                recording_state = "✅ Recording" if esp_status.get("isRecording", False) else "⏹️ Not Recording"
                st.markdown(f"**Recording Status:** {recording_state}")
            
            if esp_status.get("isRecording", False):
                # Show recording progress
                rec_time = esp_status.get("recordingTime", 0)
                st.write(f"Recording time: {rec_time} seconds")
                
                # Add a stop button
                if st.button("🛑 Stop Recording", key="stop_recording", type="primary"):
                    response = call_esp32_api("stop", method="POST")
                    if response and response.get("status") == "success":
                        st.session_state.recording = False
                        st.session_state.last_file = response.get("filename")
                        st.session_state.recording_duration = response.get("duration", 0)
                        st.success(f"Recording stopped: {response.get('filename')}")

                        # Otomatis upload setelah stop
                        st.info("⏫ Uploading recording to server...")
                        try:
                            upload_response = call_esp32_api("upload", method="POST")
                            if upload_response and upload_response.get("status") == "success":
                                st.success(f"✅ File uploaded successfully: {st.session_state.last_file}")
                                st.session_state.upload_status = "success"
                            else:
                                st.error("❌ Upload failed")
                                st.session_state.upload_status = "failed"
                        except Exception as e:
                            st.error(f"❌ Upload error: {str(e)}")
                            st.session_state.upload_status = "failed"
                        
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to stop recording")

            else:
                # Show start recording button
                start_disabled = not (esp_status.get("sdCardOK", False) and esp_status.get("microphoneOK", False))
                if st.button("🎙️ Start Recording", key="start_recording", disabled=start_disabled, type="primary"):
                    st.info("⏳ Sending start command to ESP32...")

                    response = call_esp32_api("start", method="POST")
                    if response and response.get("status") == "success":
                        # Langsung update status recording ke True
                        st.session_state.recording = True
                        st.session_state.recording_start_time = time.time()
                        st.success("🎙️ Recording started!")

                        # Optional: jalankan polling background kalau mau update status lengkap
                        for _ in range(3):
                            time.sleep(1)
                            updated_status = call_esp32_api("status")
                            if updated_status:
                                st.session_state.esp32_status = updated_status
                                break

                        st.rerun()
                    else:
                        st.error("Failed to send start command to ESP32")

            
            # Show last recording info
            if st.session_state.last_file:
                st.subheader("Last Recording")
                st.write(f"File: {st.session_state.last_file}")
                if st.session_state.recording_duration > 0:
                    st.write(f"Duration: {st.session_state.recording_duration} seconds")
                
                # Status upload
                upload_status_container = st.empty()
                
                # Jika sedang dalam proses upload, tampilkan spinner dan status
                if st.session_state.upload_status == "uploading":
                    with upload_status_container.container():
                        st.markdown("🔄 **File sedang diupload**: " + st.session_state.upload_file)
                        st.spinner("Menunggu upload selesai...")
                        
                        # Lakukan upload
                        try:
                            response = call_esp32_api("upload", method="POST")
                            
                            if response and response.get("status") == "success":
                                st.session_state.upload_status = "success"
                            else:
                                st.session_state.upload_status = "failed"
                            
                            # Rerun untuk menampilkan status baru
                            time.sleep(1)  # Tunggu sebentar untuk memastikan respons terproses
                            st.rerun()
                        
                        except Exception as e:
                            st.session_state.upload_status = "failed"
                            st.error(f"Error saat upload: {str(e)}")
                            time.sleep(1)
                            st.rerun()
                
                # Jika upload berhasil
                elif st.session_state.upload_status == "success":
                    upload_status_container.success(f"✅ **File berhasil diupload**: {st.session_state.upload_file}")
                    if st.button("🔄 Clear Status", key="clear_success"):
                        st.session_state.upload_status = None
                        st.session_state.upload_file = None
                        st.rerun()
                
                # Jika upload gagal
                elif st.session_state.upload_status == "failed":
                    upload_status_container.error(f"❌ **Upload gagal**: {st.session_state.upload_file}")
                    if st.button("🔄 Clear Status", key="clear_failed"):
                        st.session_state.upload_status = None
                        st.session_state.upload_file = None
                        st.rerun()
                
            
            # Add run diagnostics button
            st.subheader("Maintenance")
            if st.button("🔍 Run Diagnostics", key="run_diagnostics", disabled=esp_status.get("isRecording", False)):
                response = call_esp32_api("test", method="POST")
                if response and response.get("status") == "success":
                    st.success("Diagnostics completed!")
                    # Update status
                    st.session_state.esp32_status = response
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to run diagnostics")
        else:
            st.error("Unable to connect to ESP32. Check the device and make sure it's on the same network.")
            if st.button("🔄 Retry Connection"):
                st.rerun()

    # Recordings Library (Right Column)
    with col2:
        st.header("Recordings Library")
        
        # Refresh button for recordings
        if st.button("🔄 Refresh Recordings"):
            st.rerun()
        
        # Get list of recordings from Flask server
        files_data = call_flask_api("files")
        
        if files_data and "files" in files_data:
            files = files_data["files"]
            
            if not files:
                st.write("No recordings found.")
            else:
                # Create a dataframe for better display
                df = pd.DataFrame(files)
                
                # Format the size column to show in KB
                df["size_kb"] = df["size"].apply(lambda x: f"{x/1024:.1f} KB")
                
                # Display as a table
                st.dataframe(
                    df[["name", "size_kb", "modified"]],
                    column_config={
                        "name": "Filename",
                        "size_kb": "Size",
                        "modified": "Recorded On"
                    },
                    hide_index=True
                )
                
                # Select a file to play
                selected_file = st.selectbox("Select a recording to play:", 
                                            [file["name"] for file in files])
                
                if selected_file:
                    # Find the file in the list
                    selected_file_data = next((f for f in files if f["name"] == selected_file), None)
                    
                    if selected_file_data:
                        st.subheader("Play Recording")
                        
                        # Calculate the full path to the file
                        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                                "uploads", selected_file)
                        
                        # Try to play the file (if it exists locally)
                        try:
                            # Buat URL untuk audio
                            audio_url = f"{FLASK_SERVER_URL}/uploads/{selected_file}"
                            
                            # Tampilkan audio player
                            st.audio(audio_url)

                            # Tombol untuk download audio
                            st.download_button(
                                label="⬇️ Download Recording",
                                data=requests.get(audio_url).content,
                                file_name=selected_file
                            )

                            # 🔄 Tombol untuk pindah ke halaman audio_to_materi
                            if st.button("🔄 Summarize Audio"):
                                st.session_state.current_page = 'audio_to_materi'
                                st.session_state['selected_audio_file'] = selected_file  # bawa nama file ke halaman selanjutnya
                                st.session_state['from_recording'] = True
                                st.rerun()

                        except Exception as e:
                            st.error(f"Error accessing file: {str(e)}")

        else:
            st.error("Unable to connect to Flask server to retrieve recordings.")

    # Add a footer with information
    st.markdown("---")
    st.markdown("ESP32 Audio Recorder | Connected to: " + ESP32_URL)
