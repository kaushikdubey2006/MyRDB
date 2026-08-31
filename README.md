# MyRDB

### A Relational Database Management System Built from Scratch in Python

**MyRDB** is a custom, lightweight **Relational Database Management System (RDBMS)** built from scratch in Python.

The project aims to understand and implement the fundamental internal components of a real database system rather than simply using an existing database engine.

MyRDB provides a **MySQL-like command-line experience and relational database functionality**, while using its own custom storage engine, indexing system, SQL processing layer, transaction system, and database metadata.

> **MyRDB is not a MySQL clone. It is an independently implemented RDBMS prototype with a MySQL-like interface and concepts found in modern relational database systems.**

---

## 🎯 Project Objective

The primary objective of MyRDB is to explore how a relational database works internally:

```text
SQL Query
    ↓
SQL Parser
    ↓
Query Processor
    ↓
Query Optimizer
    ↓
Index / Table Access
    ↓
Storage Engine
    ↓
Binary Pages
    ↓
Disk
```

Instead of relying on SQLite, MySQL, PostgreSQL, an ORM, or another external database engine, MyRDB implements its core database functionality from scratch.

---

## ✨ Planned Features

MyRDB is being developed incrementally, with the goal of supporting a practical set of RDBMS capabilities.

### Database Management

* Multiple databases
* Database creation and deletion
* Database selection
* Database metadata
* Multiple tables per database

### Table & Schema Management

* `CREATE TABLE`
* `DROP TABLE`
* `ALTER TABLE`
* Column definitions
* Data types
* Primary Keys
* Foreign Keys
* `NOT NULL`
* `UNIQUE`
* `DEFAULT`
* `CHECK`
* Auto-increment support

### SQL Query Processing

* `INSERT`
* `SELECT`
* `UPDATE`
* `DELETE`
* `WHERE`
* Multiple conditions
* `AND` / `OR`
* `ORDER BY`
* `GROUP BY`
* `HAVING`
* `LIMIT`
* Aggregate functions
* `COUNT`
* `SUM`
* `MAX`
* `MIN`
* `AVG`

### Joins

* `INNER JOIN`
* `LEFT JOIN`
* Additional practical join support as the query engine evolves

### Indexing

* B+ Tree index
* Primary-key indexing
* Secondary indexes
* O(log N) index lookup
* Range scans
* Linked B+ Tree leaves

### Storage Engine

* Fixed-size 4096-byte pages
* Binary disk storage
* Slotted-page record organization
* Binary serialization using Python `struct`
* Page headers
* Record slots
* Tombstone deletion
* Page allocation
* Disk persistence
* `fsync()` based durability

### Transactions & Reliability

* `BEGIN`
* `COMMIT`
* `ROLLBACK`
* Savepoints
* Write-Ahead Logging (WAL)
* Crash recovery
* WAL replay
* Checkpointing
* Transaction-aware storage operations

### Concurrency

* Multiple client/session support
* Locking mechanisms
* Table/row-level locking where practical
* Basic transaction isolation
* Deadlock handling where practical

### Database Programmability

* Views
* Stored procedures
* Functions
* Triggers
* Events where practical

### Security

* User accounts
* Authentication
* Password hashing
* Roles
* Permissions
* `GRANT`
* `REVOKE`

### Maintenance & Administration

* `VACUUM`
* Storage compaction
* Checkpoints
* Database status
* Metadata inspection
* Error reporting

### Backup & Recovery

MyRDB will provide a simple command-based backup mechanism, for example:

```text
/BACKUP college backup_01
```

and restoration:

```text
/RESTORE backup_01
```

The project will also provide utilities for exporting database/schema information.

---

# 🧱 Architecture

MyRDB follows a modular database architecture.

```text
                 ┌──────────────────────┐
                 │     CLI / Web UI     │
                 └──────────┬───────────┘
                            ↓
                 ┌──────────────────────┐
                 │     SQL Parser       │
                 └──────────┬───────────┘
                            ↓
                 ┌──────────────────────┐
                 │   Query Processor    │
                 └──────────┬───────────┘
                            ↓
                 ┌──────────────────────┐
                 │   Query Optimizer    │
                 └──────────┬───────────┘
                            ↓
              ┌─────────────┴─────────────┐
              ↓                           ↓
       ┌──────────────┐            ┌──────────────┐
       │   B+ Tree    │            │ Transactions │
       │    Index     │            │   & Locks    │
       └──────┬───────┘            └──────┬───────┘
              │                           │
              └─────────────┬─────────────┘
                            ↓
                 ┌──────────────────────┐
                 │   Storage Engine     │
                 └──────────┬───────────┘
                            ↓
                 ┌──────────────────────┐
                 │    Binary Pages     │
                 └──────────┬───────────┘
                            ↓
                         Disk
```

---

# 💾 Page-Based Storage

MyRDB uses a custom page-based storage engine.

Each database file is divided into fixed-size pages:

```text
4096 bytes
┌──────────────────────────────┐
│         Page Header          │
├──────────────────────────────┤
│                              │
│        Record Area           │
│                              │
├──────────────────────────────┤
│       Slot Directory         │
└──────────────────────────────┘
```

Records are stored in binary form rather than as plain text or JSON.

Python's `struct` module is used for controlled binary serialization and deserialization.

---

# 🌳 B+ Tree Indexing

MyRDB uses a B+ Tree to provide efficient indexed access.

Conceptually:

```text
Primary Key
     ↓
   B+ Tree
     ↓
(page_id, slot_id)
     ↓
Binary Page
     ↓
Record
```

This allows indexed primary-key lookups to avoid scanning every record in the table.

The B+ Tree will also maintain linked leaf nodes to support efficient range scans.

---

# 📝 Write-Ahead Logging

MyRDB uses a **Write-Ahead Log (WAL)** for durability and crash recovery.

The basic principle is:

```text
Transaction
     ↓
Write Log
     ↓
Persist Log
     ↓
Modify Database Page
     ↓
Commit
```

If the engine crashes during an operation, the WAL can be replayed during startup to recover the required state.

Checkpointing will later reduce the amount of WAL that must be replayed during startup.

---

# 🧹 Storage Compaction

Deleted records are initially marked using tombstones instead of immediately reorganizing the entire page.

Example:

```text
Before:

[Record A] [Record B] [Record C]


DELETE B


After:

[Record A] [DELETED] [Record C]
```

A future `VACUUM` operation can compact the storage and reclaim unused space.

---

# 🖥️ MySQL-Like CLI

The first interface is a terminal-based SQL shell.

Example:

```text
MyRDB Server
Type "HELP;" for help.

myrdb> SHOW DATABASES;

myrdb> CREATE DATABASE college;

myrdb> USE college;

myrdb> CREATE TABLE students (
           id INT PRIMARY KEY,
           name VARCHAR(50),
           age INT
       );

myrdb> INSERT INTO students VALUES
       (1, 'Kaushik', 20);

myrdb> SELECT * FROM students;

myrdb> SELECT * FROM students WHERE id = 1;
```

The interface is intentionally similar to familiar SQL database shells, while the underlying implementation is completely custom.

---

# 🛠️ Technology Stack

## Core Engine

* Python
* Python Standard Library

Important modules include:

```text
struct      → binary serialization
os          → low-level file operations
re          → SQL parsing
sys         → CLI/system interaction
pathlib     → filesystem management
threading   → concurrency mechanisms
hashlib     → password hashing
secrets     → secure random values
```

The core database engine does **not** use:

* SQLite
* MySQL Connector
* PostgreSQL
* SQLAlchemy
* ORM frameworks
* External database engines

---

# 🌐 Future Web Workbench

After the core engine is stable, MyRDB will receive a visual management interface.

Planned stack:

```text
HTML
CSS
JavaScript
Flask
```

The Workbench will provide:

* SQL editor
* Query execution
* Result tables
* Database explorer
* Table explorer
* Index information
* Storage/page visualization
* Query execution information

Architecture:

```text
Browser
   ↓
Flask API
   ↓
MyRDB SQL Engine
   ↓
Storage / Index / Transaction Layers
   ↓
Binary Database Files
```

---

# 🗺️ Development Roadmap

### Phase 0 — Foundation

* [ ] Repository setup
* [ ] Project structure
* [ ] Configuration system
* [ ] Error system
* [ ] CLI foundation

### Phase 1 — Core RDBMS Engine

* [ ] Binary storage engine
* [ ] 4096-byte pages
* [ ] Slotted pages
* [ ] Record manager
* [ ] Database manager
* [ ] Table manager
* [ ] Schema metadata
* [ ] B+ Tree
* [ ] SQL parser
* [ ] Query executor
* [ ] Primary/foreign-key constraints
* [ ] Basic CLI

### Phase 1.5 — Reliability & Optimization

* [ ] WAL
* [ ] Crash recovery
* [ ] Checkpointing
* [ ] VACUUM
* [ ] Query optimization
* [ ] Aggregations
* [ ] Multi-condition queries
* [ ] Secondary indexes

### Phase 1.5+ — Advanced RDBMS Features

* [ ] Transactions
* [ ] Concurrency control
* [ ] Views
* [ ] Procedures
* [ ] Functions
* [ ] Triggers
* [ ] Users
* [ ] Roles
* [ ] Permissions
* [ ] Backup/restore

### Phase 2 — Visual Workbench

* [ ] Flask API
* [ ] SQL editor
* [ ] Result grid
* [ ] Database explorer
* [ ] Storage visualizer
* [ ] B+ Tree visualizer
* [ ] Query execution information

---

# 🎓 Learning Objectives

This project is designed to provide hands-on understanding of:

* Database internals
* RDBMS architecture
* Data structures
* B+ Trees
* Disk-based storage
* Binary serialization
* File systems
* Query processing
* Query optimization
* Transactions
* Concurrency
* Crash recovery
* Database security
* SQL parsing
* Backend architecture
* Systems engineering

The project is intentionally developed incrementally so that every major component is understood before implementation.

---

# 📁 Project Structure

```text
MyRDB/
│
├── config.py
├── errors.py
├── main.py
├── README.md
├── NOTES.txt
│
├── storage/
│   ├── __init__.py
│   └── page_engine.py
│
├── engine/
│   └── __init__.py
│
└── data/
    └── .gitkeep
```

The structure will expand as additional database subsystems are implemented.

---

# ⚠️ Project Scope & Limitations

MyRDB is an educational and portfolio-oriented RDBMS prototype.

It is **not intended to replace production database systems** such as MySQL, PostgreSQL, or other mature database engines.

Some advanced features will be implemented in simplified but practical forms. The project prioritizes:

1. Correctness
2. Understandability
3. Modular architecture
4. Binary-storage fundamentals
5. Reliable persistence
6. Practical RDBMS functionality
7. Performance awareness

over attempting to reproduce the complete complexity of a production database.

---

# 🚀 Development Philosophy

MyRDB follows an incremental engineering approach:

```text
Concept
   ↓
What & Why
   ↓
Real RDBMS Usage
   ↓
MyRDB Design
   ↓
Implementation
   ↓
Testing
   ↓
Documentation
   ↓
Git Commit
```

Every major component is implemented and tested before moving to the next layer.

---

# 📌 Current Status

**Project:** MyRDB
**Type:** Custom RDBMS Prototype
**Language:** Python
**Current Phase:** Foundation / 0%
**Interface:** CLI first, Web Workbench later
**Storage:** Custom binary page storage
**Database Engine:** Built from scratch

