"""Pure analysis over a collected keyword dataset.

Nothing here touches the network, Django, or the request cycle, so it can be
unit-tested directly against the committed ``input_files/travel.csv`` sample.
"""

import csv

import pandas as pd

REQUIRED_COLUMNS = ("video_id", "category", "duration", "tags")


class EmptyDataset(ValueError):
    """Raised when a dataset has no usable rows."""


def load_dataset(path):
    """Read a collected CSV and validate its shape."""
    frame = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"Input file is missing columns: {', '.join(missing)}")
    if frame.empty:
        raise EmptyDataset("Input file contains no rows")
    return frame


def videos_per_category(frame):
    """Return ``{category: count}``, largest first."""
    return frame["category"].value_counts().to_dict()


def min_max_category_by_volume(counts):
    """Return the categories with the most and fewest videos."""
    if not counts:
        raise EmptyDataset("No categories to compare")
    return {
        "Category with Max Videos": max(counts, key=counts.get),
        "Category with Min Videos": min(counts, key=counts.get),
    }


def average_duration_per_category(frame):
    """Return ``{category: mean duration in seconds}`` rounded to 2dp.

    A single grouped aggregate replaces the original per-category boolean mask,
    which rescanned the whole frame once for every category.
    """
    means = frame.groupby("category")["duration"].mean().round(2)
    return means.to_dict()


def min_max_category_by_duration(frame):
    """Return the categories holding the longest and shortest single video."""
    durations = frame["duration"].dropna()
    if durations.empty:
        raise EmptyDataset("No durations to compare")
    return {
        "Category with Max Duration": frame["category"][durations.idxmax()],
        "Category with Min Duration": frame["category"][durations.idxmin()],
    }


def tags_per_category(frame):
    """Return ``{category: [unique tag strings]}``."""
    grouped = frame.dropna(subset=["tags"]).groupby("category")["tags"]
    return {category: sorted(set(values)) for category, values in grouped}


def analyse(frame):
    """Run every analysis and return ``{filename: (rows, header)}``."""
    counts = videos_per_category(frame)
    return {
        "number_of_videos.csv": (counts, ["Category", "# of Videos"]),
        "min_max_tag_videos.csv": (min_max_category_by_volume(counts), None),
        "average_durations.csv": (
            average_duration_per_category(frame),
            ["Category", "Time(Seconds)"],
        ),
        "min_max_tag_durations.csv": (min_max_category_by_duration(frame), None),
        "classified_tags.csv": (tags_per_category(frame), ["Category", "Tags"]),
    }


def write_csv(path, data, header=None):
    """Write a ``{key: value}`` mapping to ``path`` as two columns."""
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if header:
            writer.writerow(header)
        for key, value in data.items():
            writer.writerow([key, value])


def write_results(output_dir, results):
    """Write every analysis result into ``output_dir``. Returns the paths written."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, (data, header) in results.items():
        target = output_dir / filename
        write_csv(target, data, header)
        written.append(target)
    return written
