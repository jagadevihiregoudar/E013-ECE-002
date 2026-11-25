
# Cell-Tower Site Maintenance Ticketing and SLA Engine

**Team ID:** E013  
**Problem Statement:** ECE-002  
**Project Type:** Command-Line Based Application  
**Programming Language:** Python 3

---

## 1. Project Overview

The Cell-Tower Site Maintenance Ticketing and SLA Engine is a Python-based application designed to automate maintenance ticket management for cellular tower sites.

The system processes alarm data, identifies maintenance issues, assigns ticket priorities, manages ticket lifecycles, monitors Service Level Agreement (SLA) deadlines, calculates penalties for SLA violations, and generates monthly reports.

The application uses CSV files for input and output and processes commands through a command file.

---

## 2. Key Features

- Site and field engineer registration.
- Alarm feed processing using CSV files.
- Automatic ticket creation based on alarm conditions.
- Priority classification into P1, P2, and P3.
- Special handling for hub sites and dependent sites.
- Duplicate alarm detection within a 15-minute window.
- Combined MAINS_FAIL and DG_NOT_STARTED alarm detection.
- Ticket lifecycle management:
  - OPEN
  - ASSIGNED
  - RESOLVED
  - CLOSED
- Ticket assignment and resolution tracking.
- Response and resolution SLA monitoring.
- Automatic penalty calculation with a maximum cap per ticket.
- Ticket reopening within the permitted time window.
- Automatic closure of resolved tickets after 24 hours.
- Monthly SLA reports generated for each circle.
- Validation and error logging for invalid input and commands.

---

## 3. Technologies Used

| Component | Technology |
|---|---|
| Programming Language | Python 3 |
| Data Storage | CSV Files |
| Command Processing | Command File |
| Testing Framework | Python unittest |
| Development Environment | Visual Studio Code |

---

## 4. Project Structure

```text
E013-ECE-002/
│
├── docs/
│
├── output/
│   ├── tickets.csv
│   ├── ticket_events.csv
│   ├── sla_report.csv
│   └── errors.csv
│
├── sample_data/
│   ├── sites.csv
│   ├── engineers.csv
│   ├── alarms.csv
│   └── commands.txt
│
├── src/
│
├── tests/
│
├── config.py
├── main.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 5. Requirements

- Python 3.10 or later.
- Visual Studio Code or any Python-supported editor.
- Windows, Linux, or macOS.

Check your Python installation:

```bash
python --version
```

---

## 6. How to Run the Project

### Step 1: Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
```

### Step 2: Navigate to the Project Folder

```bash
cd E013-ECE-002
```

### Step 3: Run the Application

```bash
python main.py sample_data --output output
```

The application reads the input files from the `sample_data` directory and generates the results in the `output` directory.

---

## 7. Input Files

The application uses the following input files:

| File | Description |
|---|---|
| sites.csv | Contains tower site information, circles, hub details, and dependent sites. |
| engineers.csv | Contains field engineer information and assigned circles. |
| alarms.csv | Contains alarm IDs, site IDs, timestamps, alarm types, and measured values. |
| commands.txt | Contains ticket lifecycle commands and reporting instructions. |

---

## 8. Output Files

The application generates the following output files inside the `output` directory:

| File | Description |
|---|---|
| tickets.csv | Contains generated tickets and their details. |
| ticket_events.csv | Records ticket lifecycle events and updates. |
| sla_report.csv | Contains monthly ticket counts, SLA breaches, and penalty amounts by circle. |
| errors.csv | Records rejected rows and invalid commands with explanations. |

---

## 9. Ticket Priority Classification

The system classifies maintenance alarms into three priority levels:

| Priority | Description |
|---|---|
| P1 | Critical issues requiring immediate attention. |
| P2 | High-priority issues requiring timely action. |
| P3 | Normal-priority issues requiring standard maintenance. |

Priority classification is based on alarm conditions, measured values, combined alarm events, and hub-site rules.

---

## 10. SLA Management

The application monitors response and resolution deadlines.

### Response SLA

| Priority | Response Time |
|---|---|
| P1 | 2 Hours |
| P2 | 4 Hours |
| P3 | 24 Hours |

### Resolution SLA

| Priority | Resolution Time |
|---|---|
| P1 | 6 Hours |
| P2 | 24 Hours |
| P3 | 72 Hours |

### Penalty Calculation

| Priority | Penalty Per Full Hour |
|---|---:|
| P1 | ₹500 |
| P2 | ₹200 |
| P3 | ₹50 |

The maximum penalty is capped at ₹10,000 per ticket.

---

## 11. Running Unit Tests

The project includes automated unit tests to verify ticket creation, priority classification, duplicate detection, lifecycle management, SLA calculations, validation, and report generation.

Run all tests from the project root directory:

```bash
python -m unittest discover -s tests -t . -v
```

**Test Result:** 89 tests passed successfully.

---

## 12. Sample Execution

Run:

```bash
python main.py sample_data --output output
```

The sample execution processes the supplied October 2026 data.

Expected processing summary:

- Tickets generated: 1,092
- Events processed: 4,608
- Rejected records or commands: 5

The application also generates a monthly SLA report for the available circles.

---

## 13. Project Objective

The main objective of this project is to simplify and automate cellular tower maintenance operations by providing reliable ticket management, priority-based issue handling, SLA monitoring, penalty calculation, and monthly performance reporting.

---

## 14. Team Information

**Team ID:** E013  
**Problem Statement ID:** ECE-002

**Team Members:**
- J Justin Samuel
- Jagadevi

---

## 15. Conclusion

The Cell-Tower Site Maintenance Ticketing and SLA Engine provides an automated approach to managing cellular tower maintenance tickets.

It reduces manual tracking, improves maintenance workflow visibility, monitors SLA compliance, and generates structured reports to support maintenance operations.
