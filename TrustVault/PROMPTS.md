# TrustVault – AI Usage Log

## Entry 1 – 06 November 2026
**Task: Project planning and initial development**

**Prompt used:**  
"I selected TrustVault for my Snovasys hiring challenge. Can you prepare the complete project for me? I am a beginner, so please make the process simple."

**AI suggestion:**  
ChatGPT prepared a Flask-based document-sharing application with registration, login, document upload, document sharing, access permissions, revocation and audit logging.

**AI mistake or limitation:**  
The initial project ZIP had not been fully executed and verified before delivery. Some setup and testing were still required.

**My manual verification:**  
I extracted the project, opened it in Visual Studio Code, installed the dependencies and started the application. I tested login, document upload, sharing and access revocation locally.

---

## Entry 2 – 06 November 2026
**Task: Python installation and debugging**

**Prompt used:**  
"It is not working. Can you finish all this work?"

**AI suggestion:**  
ChatGPT guided me through installing Python, configuring VS Code, creating a virtual environment and installing project dependencies.

**AI mistake or limitation:**  
The initial instructions used the `py` command, but Windows did not recognize the Python launcher.

**My manual verification:**  
I checked Python using `python --version` and confirmed Python 3.14.10 was installed. I used the `python` command instead and successfully installed the required packages.

I executed:

`python -m pytest`

The result was:

`6 passed in 2.19s`

---

## Entry 3 – 06 November 2026
**Task: GitHub publishing**

**Prompt used:**  
"No projects are visible on my GitHub repository. Help me upload the project."

**AI suggestion:**  
ChatGPT provided Git commands to initialize the repository, add files, commit changes and push the project to GitHub.

**AI mistake or limitation:**  
The initial diagnosis focused too quickly on the possibility that the project had not been pushed. More verification was needed.

**My manual verification:**  
I executed:

- `git status`
- `git log -1 --oneline`
- `git ls-tree -r --name-only HEAD`
- `git ls-remote --heads origin`

I verified that the main branch contained the project commit and that all important application files were included.

**GitHub repository:**

https://github.com/hasmithyadav-cmd/Trustvault

---

## Entry 4 – 06 November 2026
**Task: Render deployment and build failure**

**Prompt used:**  
"Render build failed. Here are the deployment logs. Help me fix the error."

**AI suggestion:**  
ChatGPT analysed the deployment logs and helped identify the problem with the location of requirements.txt.

**AI mistake:**  
The initial deployment instructions incorrectly suggested leaving the Root Directory blank.

The actual error was:

`ERROR: Could not open requirements file: No such file or directory: 'requirements.txt'`

**My manual verification and correction:**  
I checked the GitHub repository structure and discovered that the application files were inside a nested folder named `TrustVault`.

I corrected the Render Root Directory to:

`TrustVault`

I kept the build command:

`pip install -r requirements.txt`

After correcting the setting, the Render deployment succeeded.

**Live website:**

https://trustvault-demo-ug7e.onrender.com

---

## Entry 5 – 07 November 2026
**Task: Live website testing and verification**

**Prompt used:**  
"The website is saying the password is incorrect. Help me fix the administrator login."

**AI suggestion:**  
ChatGPT explained that the Render application has a separate database from the local application and guided me through configuring the required environment variables.

**AI mistake or limitation:**  
The initial deployment instructions did not explain clearly enough that local administrator credentials would not automatically transfer to the hosted application.

**My manual verification and correction:**  
I configured the administrator environment variables in Render and redeployed the application.

I manually verified:

1. Successfully logged in to the live website.
2. Uploaded a sample document successfully.
3. Opened the Admin dashboard.
4. Confirmed that the audit status displayed `Audit chain valid`.

The application also passed all six automated tests locally.

Live document sharing and access revocation still need final end-to-end verification on the deployed website.

---

# Conclusion

I used ChatGPT as an AI development assistant for project planning, code preparation, debugging, documentation and deployment guidance.

I manually performed the important development and verification activities, including installing dependencies, running automated tests, checking GitHub commits, analysing Render deployment logs, correcting configuration settings, logging in to the live application and uploading sample documents.

This project helped me understand the practical process of developing, testing, publishing and deploying a web application.

The current Render Free deployment uses temporary storage. Persistent database and document storage remain unfinished, so the application is currently intended for demonstration purposes rather than storing confidential documents.