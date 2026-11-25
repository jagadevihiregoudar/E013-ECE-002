"""Entry point:  python main.py <data_dir> [--commands FILE] [--output DIR]

Reads commands.txt (and the CSV files it loads) from <data_dir> and writes
ticket_events.csv, tickets.csv, sla_report.csv and errors.csv to the output
directory.  Input files are never modified.
"""
import argparse
import os
import sys

import config
from src.commands import CommandProcessor
from src.writers import write_all


def run(data_dir, commands_file=None, output_dir="output"):
    """Process one data set and return the CommandProcessor (for tests)."""
    commands_path = commands_file or os.path.join(data_dir, "commands.txt")
    processor = CommandProcessor(base_dir=data_dir)
    processor.run_file(commands_path)
    write_all(output_dir, processor.store, processor.report_rows,
              processor.errors)
    return processor


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("data_dir", help="folder with commands.txt and CSVs")
    parser.add_argument("--commands", help="command file (default: "
                        "<data_dir>/commands.txt)")
    parser.add_argument("--output", default="output",
                        help="output folder (default: output)")
    args = parser.parse_args(argv)

    for note in config.UNCONFIRMED:
        print(f"WARNING (unconfirmed rule): {note}", file=sys.stderr)

    processor = run(args.data_dir, args.commands, args.output)
    for line in processor.messages:
        print(line)
    store = processor.store
    print(f"\nTickets: {len(store.tickets)}  Events: {len(store.events)}  "
          f"Errors: {len(processor.errors)}  Output: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
