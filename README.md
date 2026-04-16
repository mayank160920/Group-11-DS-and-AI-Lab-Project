# Group 11 DSAI Lab Project

This repository contains the Group 11 DSAI lab project for document understanding and semantic validation. The main application lives under [`code/`](/Users/mayank/Desktop/dsai/repo/ml6/code), with supporting datasets and milestone documentation kept at the repository root.

## Project Overview

The application is a Configurable Multimodal Semantic Validation System (CMSVS) for extracting and validating structured information from PDFs and images.

It includes:

- a FastAPI backend for extraction, validation, and configuration management
- a Streamlit frontend for interactive upload and review
- pipeline code for local runs, testing, and experimentation

## Repository Structure

- [`code/`](/Users/mayank/Desktop/dsai/repo/ml6/code): main application source, API, frontend, configs, tests, and deployment instructions
- [`datasets/`](/Users/mayank/Desktop/dsai/repo/ml6/datasets): local datasets and ground-truth files used for experimentation and evaluation
- [`docs/`](/Users/mayank/Desktop/dsai/repo/ml6/docs): milestone reports, presentations, and supporting project documentation
- [`Problem-Statement.pdf`](/Users/mayank/Desktop/dsai/repo/ml6/Problem-Statement.pdf): project problem statement

## Getting Started

For local setup, application startup, and Hugging Face deployment notes, use the application README:

- [`code/README.md`](/Users/mayank/Desktop/dsai/repo/ml6/code/README.md)

That README includes:

- Python and dependency requirements
- local backend and frontend startup steps
- environment variable configuration
- verification and troubleshooting steps
- Hugging Face Spaces deployment notes using the `deploy/hf` branch

## Notes

- The repository root is primarily for project organization, datasets, and reports.
- The runnable application is maintained inside [`code/`](/Users/mayank/Desktop/dsai/repo/ml6/code).
- Hugging Face deployment should use the dedicated deployment branch described in [`code/README.md`](/Users/mayank/Desktop/dsai/repo/ml6/code/README.md), not `main`.
