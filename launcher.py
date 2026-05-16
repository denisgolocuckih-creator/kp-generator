import subprocess 
import sys 
import os 
 
project_dir = os.path.dirname(os.path.abspath(__file__)) 
 
subprocess.Popen( 
    ["streamlit", "run", "app.py", "--server.headless", "true"], 
    cwd=project_dir, 
    creationflags=subprocess.CREATE_NO_WINDOW, 
    stdout=subprocess.DEVNULL, 
    stderr=subprocess.DEVNULL 
) 
