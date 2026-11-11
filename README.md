# MyRDB

### A Relational Database Management System Built from Scratch in Python

**MyRDB** is a custom, lightweight **Relational Database Management System (RDBMS)** built from scratch in Python.

The project aims to understand and implement the fundamental internal components of a real database system rather than simply using an existing database engine.

MyRDB is planned to provide a **MySQL-like command-line experience and a Unicode terminal Workbench (TUI)**, backed by its own custom storage engine, indexing system, SQL processing layer, transaction system, and database metadata. Both interfaces will use the same authenticated session and database engine.

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

- Multiple databases
- Database creation and deletion
- Database selection
- Database metadata
- Multiple tables per database

### Table & Schema Management

- `CREATE TABLE`
- `DROP TABLE`
- `ALTER TABLE`
- Column definitions
- Data types
- Primary Keys
- Foreign Keys
- `NOT NULL`
- `UNIQUE`
- `DEFAULT`
- `CHECK`
- Auto-increment support

### SQL Query Processing

- `INSERT`
- `SELECT`
- `UPDATE`
- `DELETE`
- `WHERE`
- Multiple conditions
- `AND` / `OR`
- `ORDER BY`
- `GROUP BY`
- `HAVING`
- `LIMIT`
- Aggregate functions
- `COUNT`
- `SUM`
- `MAX`
- `MIN`
- `AVG`

### Joins

- `INNER JOIN`
- `LEFT JOIN`
- Additional practical join support as the query engine evolves

### Indexing

- B+ Tree index
- Primary-key indexing
- Secondary indexes
- O(log N) index lookup
- Range scans
- Linked B+ Tree leaves

### Storage Engine

- Fixed-size 4096-byte pages (implemented and tested)
- Binary page read/write using Python `struct` (implemented and tested)
- Persistent slot-directory reconstruction after reload (implemented and tested)
- Record insert, read, update, and delete operations (implemented)
- Tombstone deletion and deleted-slot reuse (implemented)
- Multi-page allocation and record relocation (implemented and tested)
- Free-space tracking and reconstruction after reload (implemented and tested)
- Record compaction (implemented and tested)
- Empty-page reuse, including after reload (implemented and tested)
- Page structure and metadata validation (implemented and tested)
- `flush()` based file writing; `fsync()` durability is not implemented yet

### Transactions & Reliability

- `BEGIN`
- `COMMIT`
- `ROLLBACK`
- Savepoints
- Write-Ahead Logging (WAL)
- Crash recovery
- WAL replay
- Checkpointing
- Transaction-aware storage operations

### Concurrency

- Multiple client/session support
- Locking mechanisms
- Table/row-level locking where practical
- Basic transaction isolation
- Deadlock handling where practical

### Database Programmability

- Views
- Stored procedures
- Functions
- Triggers
- Events where practical

### Security

- User accounts
- Authentication
- Password hashing
- Roles
- Permissions
- `GRANT`
- `REVOKE`

### Maintenance & Administration

- `VACUUM`
- Storage compaction
- Checkpoints
- Database status
- Metadata inspection
- Error reporting

### Backup & Recovery

MyRDB will provide a simple command-based backup mechanism, for example:

```text
/BACKUP college backup_01
```

And restoration:

```text
/RESTORE backup_01
```

The project will also provide utilities for exporting database/schema information.

---

# 🧱 Architecture

MyRDB follows a modular database architecture.

```text
                 ┌──────────────────────┐
                 │   CLI / Terminal TUI │
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
                 │    Binary Pages      │
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

The storage engine currently supports:

- Page creation and binary persistence.
- Slot-directory reconstruction after loading pages.
- Multi-page record management.
- Tombstone deletion and deleted-slot reuse.
- Free-space tracking.
- Record relocation.
- Page compaction.
- Empty-page reuse.

---

# 🌳 B+ Tree Indexing

MyRDB is planned to use a B+ Tree to provide efficient indexed access.

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

MyRDB is planned to use a **Write-Ahead Log (WAL)** for durability and crash recovery.

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

MyRDB currently uses tombstones for deletion. `Page.compact()` reorganizes active records into contiguous storage while preserving active slot IDs.

`PageManager.compact_all_pages()` applies compaction across the loaded pages.

Compaction and page-reuse behavior have dedicated tests.

A higher-level `VACUUM` command and transaction-safe maintenance are still future work.

Example:

```text
Before:

[Record A] [Record B] [Record C]


DELETE B


After:

[Record A] [DELETED] [Record C]
```

---

# 🖥️ MySQL-Like CLI

The first interface is planned as a terminal-based SQL shell.

Example of the intended interaction:

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

- Python
- Python Standard Library

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

- SQLite
- MySQL Connector
- PostgreSQL
- SQLAlchemy
- ORM frameworks
- External database engines

---

# 🖥️ Future Terminal Workbench (TUI)

After the core engine is stable, MyRDB will receive a Unicode terminal-based Workbench (TUI).

The CLI and Workbench will share the same authenticated session and MyRDB engine. Database logic will not be duplicated in the interface.

The TUI will provide:

- SQL editor
- Query execution
- Result tables
- Database explorer
- Table explorer
- Index information
- Storage/page visualization
- Query execution information

Startup and interface flow:

```text
MyRDB
   ↓
Username + Password
   ↓
Authentication
   ↓
Select Interface
   ├── CLI
   └── Workbench (TUI)
          ↓
    Same MyRDB Engine
          ↓
Storage / Index / Transaction Layers
          ↓
Binary Database Files
```

---

# 🗺️ Development Roadmap

### Phase 0 — Foundation

- [x] Repository setup
- [x] Project structure
- [x] Configuration system
- [x] Error system foundation
- [ ] CLI foundation

### Phase 1 — Core RDBMS Engine

- [x] Binary page-storage foundation
- [x] 4096-byte page structure
- [x] Page header and validation
- [x] Record/slot CRUD foundation
- [x] Persistent slot-directory reconstruction
- [x] Free-space tracking and reconstruction
- [x] Record compaction and deleted-slot reuse
- [x] Multi-page storage engine and record relocation
- [x] Empty-page reuse
- [ ] Database manager and multiple-database metadata
- [ ] Table manager and schema metadata
- [ ] B+ Tree
- [ ] SQL parser
- [ ] Query executor
- [ ] Primary/foreign-key constraints
- [ ] Basic CLI

### Phase 1.5 — Reliability & Optimization

- [ ] WAL
- [ ] Crash recovery
- [ ] Checkpointing
- [ ] VACUUM
- [ ] Query optimization
- [ ] Aggregations
- [ ] Multi-condition queries
- [ ] Secondary indexes

### Phase 1.5+ — Advanced RDBMS Features

- [ ] Transactions
- [ ] Concurrency control
- [ ] Views
- [ ] Procedures
- [ ] Functions
- [ ] Triggers
- [ ] Users
- [ ] Roles
- [ ] Permissions
- [ ] Backup/restore

### Phase 2 — Terminal Workbench (TUI)

- [ ] Unicode terminal interface
- [ ] SQL editor/input area
- [ ] Result grid/table rendering
- [ ] Database explorer
- [ ] Storage/page visualizer
- [ ] B+ Tree visualizer
- [ ] Query execution information

---

# 🎓 Learning Objectives

This project is designed to provide hands-on understanding of:

- Database internals
- RDBMS architecture
- Data structures
- B+ Trees
- Disk-based storage
- Binary serialization
- File systems
- Query processing
- Query optimization
- Transactions
- Concurrency
- Crash recovery
- Database security
- SQL parsing
- Backend architecture
- Systems engineering

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
│
├── Storage/
│   ├── page_engine.py
│   └── page_manager.py
│
├── engine/
│   └── __init__.py
│
├── test_storage_engine.py
├── test_record_compaction.py
├── test_free_space_management.py
├── test_page_reuse.py
├── test_storage_stress.py
│
└── data/
    └── .gitkeep
```

This is a high-level view of the current repository structure. Additional configuration, test, and data files may exist.

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

## Current Implementation Limitations

Chapter 4's planned storage-engine scope has been implemented and tested, but MyRDB is still an educational RDBMS prototype rather than a production database.

Known limitations include:

- **Simple record format:** Records are currently encoded as UTF-8 values separated by `|`. The delimiter is not escaped, and deserialization returns values as strings. A typed SQL record format is still needed.
- **Durability:** `PageManager.save_page()` writes and flushes page data, but it does not currently call `os.fsync()`. WAL-based crash recovery and transaction atomicity are not implemented.
- **Update atomicity:** When an update requires relocation, the new record is written before the old record is deleted. This is not crash-atomic and will need transaction/WAL protection later.
- **Locator identity:** A `(page_id, slot_id)` locator can become stale when a deleted slot or empty page is reused. The future index layer must account for this, for example with record identifiers or slot generations.
- **Database and schema layer:** Multiple-database management, table management, schema metadata, SQL parsing, query execution, and constraints are not yet complete subsystems.
- **Indexing:** B+ Tree indexing, primary-key indexes, secondary indexes, and range scans remain planned work.
- **Reliability and concurrency:** WAL, crash recovery, checkpointing, transaction isolation, locking, and concurrent-session support remain future work.
- **Interfaces and security:** The MySQL-like CLI, Unicode TUI, authentication, roles, and permissions remain planned features.
- **Concurrency target:** The design goal of approximately 100 concurrent users has not been load-tested and must not be treated as verified support.

Features in the planned-feature sections describe project goals; they should not be interpreted as already implemented unless explicitly marked as implemented.

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
**Learning Progress:** Chapters 1–4 of 7 completed  
**Current Focus:** Chapter 5 — SQL Engine & Indexing  
**Latest Git checkpoint:** `4b606d7` — `Complete Chapter 4 storage engine improvements`  
**Interface Plan:** MySQL-style CLI and Unicode terminal Workbench (TUI), developed after the DBMS core  
**Storage:** 4096-byte binary pages, persistent slot reconstruction, multi-page storage, CRUD, relocation, compaction, free-space tracking, and empty-page reuse  
**Database Engine:** Custom Python implementation using the standard library; no external database engine

## Implemented So Far

### Chapter 1 — Foundation & Configuration

- Central configuration in `config.py`
- Page size, magic value, and storage format version
- Database, index, WAL, backup, and checkpoint path definitions

### Chapter 2 — Storage & Page Management

- Fixed-size 4096-byte page structure
- Binary page header using Python `struct`
- Explicit Little-Endian header format: `<4sHIHI`
- Page creation and binary read/write operations
- Page validation for size, magic, version, and page ID
- Invalid-page validation tests

### Chapter 3 — Record & Slot Management

- Record serialization and deserialization foundation
- Slot entries containing record offset and length
- Record insert, read, update, and delete operations
- Tombstone deletion and deleted-slot tracking
- Free-space calculations and deleted-slot reuse
- Slot-directory reconstruction after loading pages from disk

### Chapter 4 — Storage Engine & Page Management

- Multi-page storage with automatic page allocation
- Record relocation when an update cannot fit on its original page
- Free-space map maintained in memory and rebuilt from persisted pages on reload
- Empty-page detection and reuse, including after reload
- Page compaction and compaction across all pages
- Page metadata validation
- Persistence tests after reload
- Integration tests covering multi-page CRUD and relocation
- Stress test covering 500 inserted records, 20 larger updates, deletions, compaction, page reuse, and reload verification

**Chapter 4 verification:** 28 dedicated tests across the four focused test suites, the PageManager self-test, and 11 storage stress-test checks passed. The stress test recovered 424 remaining original records after updates and deletions. This describes the tests run for the current implementation; it is not a claim of production-grade reliability.