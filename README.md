# Khamgaon AVM Hand Tracking

## Description

It identifies and tracks operator's hand across different regions of a video feed and records the time spent in each designated area. The primary script for execution is `main.py`.

## Features

- Real-time hand detection using computer vision
- Region-based tracking of hand movement
- Time tracking in each region
- Modular design with a core processing engine

## File Overview

- `main.py`: Main execution script; initializes the system and manages the workflow.
- `engine.py`: Contains the core logic for processing video frames and tracking.

## Folder Overview

- `static/`: Contains configurable static variables and constants. Be sure to edit `static/variables.py` and fill in the following:
  - `PLC_IP`: IP address for PLC connection
  - `RTSP_LINK`: RTSP stream URL for the video input

- `utils/`: Contains various utility modules

## Installation

1. Clone or extract the repository.
2. (Optional) Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
