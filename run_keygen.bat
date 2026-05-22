@echo off 
cd /d %%~dp0 
call venv\Scripts\activate 
start http://localhost:8503 
streamlit run keygen.py --server.port 8503 
