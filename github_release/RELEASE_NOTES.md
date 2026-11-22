# Indic AAC Studio — laptop demo

For the easiest demo, download Indic_AAC_Studio_Offline_Demo.zip, extract it and run `python serve_demo.py` from AAC_CPU_Portable. Open http://localhost:8080/ . Windows users can double-click start_demo.bat after installing Python 3.

For the full CPU application, download BOTH .part files and restore_full_zip.py into the same folder, then run `python restore_full_zip.py`. It verifies SHA-256 checksums and restores the original full ZIP. Extract it, then follow INSTALLATION_GUIDE.md. On Linux/Ubuntu use `bash install_cpu.sh` followed by `bash start_cpu.sh`. Initial dependency installation needs internet. Arbitrary CPU synthesis can be slow; included and cached sentences avoid inference. Windows full-backend use requires Ubuntu WSL2.

80 recorded sentences: 20 each in English, Hindi, Gujarati and Marathi. Includes cache clearing and original recordings. Static mode uses browser-local storage and recorded audio; Google sign-in, Redis sync, AI images and arbitrary neural speech require the backend. Personal voice cloning is not implemented.

Full backend accounts: /login and /signup. Default shared demo account: username `demo`, password `AACdemo@2026`. Create a separate local account or use Google sign-in to retain your own saved data. Accounts and password hashes persist in Redis; the static recorded demo does not authenticate users.
