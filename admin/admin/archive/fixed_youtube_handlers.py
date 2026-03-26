"""
Fixed YouTube Handlers
=====================
This file contains fixed implementations of the YouTube preview and download handlers
for the DrummersWidget. Replace the corresponding methods in drummers_widget.py with these:
implementations.
"""

# Play preview method - Fixed implementation
def _on_play_preview(self):
    """Play a preview of the selected YouTube video"""
    try:
        print("\n====== CONSOLE DEBUG: PLAY PREVIEW TRIGGERED ======")
        current_items = self.youtube_results_list.selectedItems()
        if not current_items:
            print("CONSOLE DEBUG: No items selected in YouTube results list")
            QMessageBox.warning(self, "Preview Error", "Please select a video to preview")
            return

        # Use Qt.UserRole directly
        video_data = current_items[0].data(Qt.UserRole)
        print(f"CONSOLE DEBUG: Selected video data type: {type(video_data)}")
        print(f"CONSOLE DEBUG: Selected video data: {video_data}")

        if not video_data or not isinstance(video_data, dict) or "url" not in video_data:
            print("CONSOLE DEBUG: Invalid video data or missing URL")
            QMessageBox.warning(self, "Preview Error", "Invalid video data or missing URL")
            return

        video_url = video_data.get("url")
        if not video_url:
            # Try to construct URL from video ID if available
            if "id" in video_data:
                video_url = f"https://www.youtube.com/watch?v={video_data['id']}"
                print(f"CONSOLE DEBUG: Constructed URL from ID: {video_url}")
            else:
                print("CONSOLE DEBUG: No URL or ID found in video data")
                QMessageBox.warning(self, "Preview Error", "No URL found for this video")
                return

        # Open the URL in the default browser
        print(f"CONSOLE DEBUG: Opening URL: {video_url}")
        QDesktopServices.openUrl(QUrl(video_url))
        print("CONSOLE DEBUG: URL opened in browser")

    except Exception as e:
        print(f"CONSOLE DEBUG: Error playing preview: {e}")
        logger.error(f"Error playing preview: {e}")
        traceback.print_exc()
        QMessageBox.critical(self, "Preview Error", f"Failed to play preview: {str(e)}")

    print("====== CONSOLE DEBUG: PLAY PREVIEW COMPLETE ======\n")

# Download video method - Fixed implementation
def _on_download_video(self):
    """Handle YouTube download button click"""
    try:
        print("\n====== CONSOLE DEBUG: DOWNLOAD VIDEO TRIGGERED ======")
        current_items = self.youtube_results_list.selectedItems()
        if not current_items:
            print("CONSOLE DEBUG: No items selected in YouTube results list")
            QMessageBox.warning(self, "Download Error", "Please select a video to download")
            return

        # Use Qt.UserRole directly
        video_data = current_items[0].data(Qt.UserRole)
        print(f"CONSOLE DEBUG: Selected video data type: {type(video_data)}")
        print(f"CONSOLE DEBUG: Selected video data: {video_data}")

        if not video_data or not isinstance(video_data, dict):
            print("CONSOLE DEBUG: Invalid video data")
            QMessageBox.warning(self, "Download Error", "Invalid video data")
            return

        # Get video URL
        video_url = video_data.get("url")
        if not video_url and "id" in video_data:
            video_url = f"https://www.youtube.com/watch?v={video_data['id']}"
            print(f"CONSOLE DEBUG: Constructed URL from ID: {video_url}")

        if not video_url:
            print("CONSOLE DEBUG: No URL or ID found in video data")
            QMessageBox.warning(self, "Download Error", "No URL found for this video")
            return

        # If we have a current song selected, use its title
        song_title = None
        if self.current_song:
            song_title = self.current_song.get("title")
            print(f"CONSOLE DEBUG: Using current song title: {song_title}")

        # Otherwise use the video title
        if not song_title:
            song_title = video_data.get("title", "Unknown")
            print(f"CONSOLE DEBUG: Using video title: {song_title}")

        # Create output filename
        filename = None
        if self.current_drummer:
            filename = f"{self.current_drummer['id']}_{self._sanitize_filename(song_title)}.mp3"
        else:
            # If no drummer context, use video ID
            video_id = video_data.get('id', 'unknown')
            filename = f"{video_id}_{self._sanitize_filename(song_title)}.mp3"

        output_path = os.path.join(self.download_path, filename)
        print(f"CONSOLE DEBUG: Output path: {output_path}")

        # Reset progress bar
        self.download_progress.setValue(0)
        self.download_progress.setMaximum(100)

        # Start download using YouTubeService
        print(f"CONSOLE DEBUG: Starting download from URL: {video_url}")
        try:
            download_thread, thread = self.youtube_service.download_audio()
                video_url,
                output_path,
                self._on_download_progress,
                self._on_download_complete,
                lambda error: self.thread_safe.run_in_main_thread()
                    lambda: QMessageBox.critical(self, "Download Error", f"Failed to download: {error}")
                )
            )

            # Store the download thread objects for potential cancellation later
            self.download_threads.append((download_thread, thread))

            # Disable download button during download
            self.download_btn.setEnabled(False)
            self.download_btn.setText("Downloading...")
            print("CONSOLE DEBUG: Download started successfully")

        except Exception as e:
            print(f"CONSOLE DEBUG: Error starting download: {e}")
            logger.error(f"Error starting download: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Download Error", f"Failed to start download: {str(e)}")

    except Exception as e:
        print(f"CONSOLE DEBUG: Error in download video handler: {e}")
        logger.error(f"Error downloading video: {e}")
        traceback.print_exc()
        QMessageBox.critical(self, "Download Error", f"Failed to download: {str(e)}")

    print("====== CONSOLE DEBUG: DOWNLOAD VIDEO HANDLER COMPLETE ======\n")
