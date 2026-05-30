#Requires AutoHotkey v2.0
#SingleInstance Force

; === Custom Video Editor Menu ===
; Hotkey: Win + V to open the menu

videoMenu := Menu()
videoMenu.Add("Run Audio Replacer", RunAudio)
videoMenu.Add("Run Short GUI v8", RunShortGUI)
videoMenu.Add("Run v17 Script", RunV17)
videoMenu.Add("Run Video Uploading v7", RunUploader)
videoMenu.Add("Exit", (*) => ExitApp())


#v:: videoMenu.Show()

RunAudio(*) {
    Run "pythonw.exe C:\Users\dhruv\Downloads\Interview_questions\Golang\video-editor\video_editor\shortcuts\audio_replacer.py"
}
RunShortGUI(*) {
    Run "pythonw.exe C:\Users\dhruv\Downloads\Interview_questions\Golang\video-editor\video_editor\shortcuts\short_gui_v8.py"
}
RunVideoEditing(*) {
    Run "pythonw.exe C:\Users\dhruv\Downloads\Interview_questions\Golang\video-editor\video_editor\shortcuts\v17.py"
}
RunUploader(*) {
    Run "pythonw.exe C:\Users\dhruv\Downloads\Interview_questions\Golang\video-editor\video_editor\shortcuts\video_uploading_v7.py"
}
