#  Find My Item

A lightweight campus Lost & Found web application that helps students report, search, and manage lost or found items within their college campus.

##  Problem Statement

Students frequently lose personal belongings on campus, while found items often have no centralized place to be reported.

**Find My Item** provides a simple platform where students can:

* Report lost or found items
* Search for reported items
* View the current status of an item
* Contact the person who reported an item
* Allow administrators to manage and resolve reports

---

##  Project Objectives

* Provide a centralized Lost & Found platform for students
* Make searching for lost items quick and simple
* Demonstrate secure web application deployment on AWS
* Demonstrate public and private access control
* Use GitHub for source-code management and deployment

---

##  Architecture

```text
                         INTERNET
                            │
                         HTTPS :443
                            │
                            ▼
                    ┌─────────────────┐
                    │     AWS EC2     │
                    │  Ubuntu Server  │
                    │                 │
                    │     Nginx       │
                    │       │         │
                    │       ▼         │
                    │   Flask App     │
                    │       │         │
                    │       ▼         │
                    │    SQLite       │
                    └────────┬────────┘
                             │
                          SSH :22
                             │
                             ▼
                       Developer PC

                    ┌─────────────────┐
                    │     GitHub      │
                    │ Source Code     │
                    └────────┬────────┘
                             │
                         git pull
                             ▼
                          AWS EC2
```

---

##  Main Modules

### 1. Authentication

* Student login
* Admin login
* Role-based access to the admin dashboard

### 2. Report Item

Users can report:

* Item name
* Lost/Found type
* Location
* Date
* Contact information

### 3. Search

Users can search reported items using:

* Item name
* Location
* Lost/Found type

### 4. Admin Dashboard

Administrators can:

* View reported items
* Update item status
* Mark items as resolved
* Remove inappropriate reports

### 5. Deployment

The application is version-controlled using GitHub and deployed to an AWS EC2 Ubuntu server.

---

##  Dataset

The project uses a small structured dataset containing sample campus Lost & Found records.

Example fields:

```text
id
item_name
type
location
date
contact
status
```

Example:

```text
1 | Black Wallet | Lost  | Library   | 2026-09-15 | Open
2 | Water Bottle | Found | CSE Block | 2026-09-16 | Open
3 | Calculator   | Lost  | Lab 3     | 2026-09-14 | Open
```

The prototype uses SQLite for storing and managing these records.

---

##  Technology Stack

| Layer                | Technology          |
| -------------------- | ------------------- |
| Frontend             | HTML, CSS           |
| Backend              | Python Flask        |
| Database             | SQLite              |
| Version Control      | Git, GitHub         |
| Development          | VS Code             |
| Production Server    | AWS EC2             |
| Operating System     | Ubuntu              |
| Web Server           | Nginx               |
| Network Security     | AWS Security Groups |
| Secure Server Access | SSH                 |

---

##  AWS Integration

### Amazon EC2

The Flask application is hosted on an Ubuntu EC2 virtual machine.

```text
User
  ↓
Domain
  ↓
EC2
  ↓
Nginx
  ↓
Flask
  ↓
SQLite
```

### Security Groups

The EC2 instance uses a Security Group to control inbound traffic.

| Port | Purpose | Access                         |
| ---- | ------- | ------------------------------ |
| 22   | SSH     | Restricted to administrator IP |
| 80   | HTTP    | Public                         |
| 443  | HTTPS   | Public                         |

Port 22 is restricted because it provides administrative access to the server, while ports 80/443 are publicly accessible for the web application.

---

##  Security

The project implements security at multiple levels:

* **AWS Security Group** controls network access
* **SSH key authentication** is used to access the EC2 server
* **SSH access is restricted** to the administrator's IP
* **HTTPS** protects communication between users and the application
* **Authentication** protects user/admin functionality
* The database is stored on the server and is **not directly exposed to the Internet**
* Sensitive files such as SSH keys and environment variables are excluded using `.gitignore`

---

##  Public vs Private Access

### Public Access

Students access the application through the domain:

```text
https://<domain>
```

Web traffic is allowed through ports **80 and 443**.

### Private Access

Developers access the EC2 server using SSH:

```text
ssh -i <key.pem> ubuntu@<EC2-IP>
```

Port **22 is restricted to authorized IP addresses**.

---

##  Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/<username>/find-my-item.git
cd find-my-item
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate it

**Windows PowerShell:**

```powershell
venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
python app.py
```

The application will be available locally at:

```text
http://127.0.0.1:5000
```

---

##  AWS Deployment

The production deployment follows:

```text
Developer
    ↓
Git
    ↓
GitHub
    ↓
SSH
    ↓
AWS EC2 Ubuntu
    ↓
git pull
    ↓
Nginx
    ↓
Flask Application
    ↓
Public Domain
```

### Basic deployment steps

```bash
git clone <repository-url>

cd find-my-item

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

python3 app.py
```

Nginx is configured to receive public web traffic and forward requests to the Flask application.

---

##  Future Improvements

The current application is intentionally small for the AWS workshop. A production-scale version could use:

* **Amazon DynamoDB / RDS** instead of SQLite
* **Amazon S3** for item images
* **Amazon Cognito** for user authentication
* **AWS CloudWatch** for monitoring and logs
* **AWS Certificate Manager** for SSL/TLS certificates
* Email/SMS notifications when a matching item is found

---

##  Team

**Project:** Find My Item
**Domain:** Campus Lost & Found
**Purpose:** AWS Workshop Mini Project

---

##  License

This project is created for educational and workshop purposes.
