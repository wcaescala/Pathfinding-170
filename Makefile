.PHONY: fast full test clean help gui

# Default target
help:
	@echo "Available targets:"
	@echo "  make gui       - Launch native desktop pathfinding visualizer GUI (Tkinter)"
	@echo "  make fast      - Run fast benchmark (k=2, 54 scenarios) and generate report"
	@echo "  make full      - Run full benchmark (k=5, 135 scenarios) with single worker"
	@echo "  make test      - Run all tests"
	@echo "  make clean     - Clean results directories"

gui:
	python3 gui.py

fast:
	python3 -m evaluation.runner --preset fast
	python3 -m evaluation.report $$(ls -d results/*_fast | tail -1)

full:
	python3 -m evaluation.runner --preset full --workers 1
	python3 -m evaluation.report $$(ls -d results/*_full | tail -1)

test:
	python3 -m pytest tests/

clean:
	rm -rf results/
