---
node_id: "infrastructure-index"
title: "Infrastructure Index"
type: "index"
parent: "[[00-system/System Hub|System Hub]]"
status: "active"
version: "1.0.0"
revision: 1
created: "2026-11-20"
updated: "2026-11-20"
change_type: "minor"
change_summary: "Created the infrastructure domain index for the blank starter."
review_status: "needs_review"
tags:
  - "infrastructure"
  - "index"
aliases: []
previous: "[[20-cognitive/Cognitive Index|Cognitive Index]]"
next: "[[40-technical/Technical Index|Technical Index]]"
---
# Infrastructure Index

## Purpose

The infrastructure domain documents the machines, environments and services your work runs on: computers, operating systems, containers, local model servers, automation hosts and the way they connect.

## What belongs here

- Setup and recovery procedures for a machine or environment.
- Inventories of hardware and services, with what each one is for.
- Network and access maps, without secrets.

## What does not

- Passwords, tokens, keys or private addresses: keep them in a password manager, never in the vault.
- Source code (that lives under `code/` or in its own repository).
- General technical knowledge not tied to your setup (that is `40-technical`).

## Naming

Name a note after the thing it documents and the job: `Workstation - Setup.md`, `Automation Host - Recovery.md`. Keep one machine or service per hub.

## Example

`30-infrastructure/Workstation - Setup.md`, type `operations`: the operating system, drivers and tools installed, in order, with the check that proves each step worked.

## Navigation

- Parent: [[00-system/System Hub|System Hub]]
- Previous: [[20-cognitive/Cognitive Index|Cognitive Index]]
- Next: [[40-technical/Technical Index|Technical Index]]
