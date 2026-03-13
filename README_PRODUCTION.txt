PRODUCTION DEPLOYMENT GUIDE
===========================

1. Install Production Server
   -------------------------
   You are currently running the app using the Flask development server (python app.py), which is not suitable for production.
   We have added 'waitress' (a production WSGI server for Windows) to your setup.
   
   Ensure you have installed the requirements:
   pip install -r requirements.txt
   pip install waitress

2. Run the App in Production Mode
   ------------------------------
   Instead of running `python app.py`, use the new `wsgi.py` file created for you.
   
   Run this command in PowerShell/Terminal:
   python wsgi.py

   This will start a robust, multi-threaded server on http://0.0.0.0:8080 (creating a proper production environment).

3. Fix for "Branch Analysis" and "Student Analysis"
   -------------------------------------------------
   - Branch Analysis: We have added error handling to prevent the page from crashing if an uploaded Excel file has an unexpected format.
   - Student Analysis: Please ensure you have uploaded a valid result file in the "Overview" page first. These pages rely on the data loaded in the session.
   - If the pages are blank, try clearing your browser cache or opening in an Incognito window to reset the session.

4. UI Differences (CSS/Layout)
   ---------------------------
   - The app uses custom CSS in the `assets/` folder.
   - Ensure the `assets/` folder is in the same directory as `app.py`.
   - Running with `python wsgi.py` ensures static files are served correctly.

5. Troubleshooting
   ---------------
   - If you see "Internal Server Error", check the terminal output for error details.
   - If the "Branch Analysis" page shows an alert about invalid data, check your Excel column headers (e.g., they must contain "Result", "Total", etc.).
