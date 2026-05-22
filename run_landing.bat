@echo off 
cd /d %%~dp0 
call venv\Scripts\activate 
start http://localhost:8504 
streamlit run landing.py --server.port 8504 
