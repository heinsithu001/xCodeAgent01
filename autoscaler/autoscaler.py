#!/usr/bin/env python3
"""
Simple autoscaler for CodeAgent services
"""
import time
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Autoscaler started - monitoring mode")
    
    while True:
        try:
            # Simple monitoring loop
            logger.info("Monitoring system resources...")
            time.sleep(60)
        except Exception as e:
            logger.error(f"Autoscaler error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()