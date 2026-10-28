@echo off
echo Starting Python script execution... > debug_output.txt
python scripts/generate_postman_collection.py >> debug_output.txt 2>&1
echo Script execution finished. >> debug_output.txt
dir >> debug_output.txt
