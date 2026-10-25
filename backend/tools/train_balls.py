"""Compatibility entry point; see train_detector.py and MODEL-TRAINING.md."""
try:
    from .train_detector import main
except ImportError:
    from train_detector import main

if __name__ == '__main__':
    main()
