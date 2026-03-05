"""Command-line interface for Pangloss."""

import sys
from pathlib import Path
from typing import Dict

import click

from pangloss.algo.convergence import find_convergence_points
from pangloss.algo.generator import generate_word
from pangloss.algo.selector import select_synonyms
from pangloss.data.asjp import load_asjp
from pangloss.data.matrix import build_matrix
from pangloss.data.speakers import load_speaker_counts
from pangloss.graph.trie import build_prefix_trie, build_suffix_trie
from pangloss.output.dictionary import (
    format_dictionary,
    format_summary,
    save_dictionary,
)
from pangloss.output.graph_export import export_bowtie_graph


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Pangloss: Phonetic convergence-based language synthesis."""
    pass


@cli.command()
def version():
    """Show version information."""
    click.echo("Pangloss 0.1.0")


@cli.command()
@click.option(
    "--data-dir",
    default="data/asjp",
    type=click.Path(exists=True),
    help="Path to ASJP data directory",
)
@click.option(
    "--output-dir",
    default="output",
    type=click.Path(),
    help="Output directory for results",
)
@click.option(
    "--coverage-threshold",
    default=0.9,
    type=float,
    help="Target coverage threshold (0.0-1.0)",
)
@click.option(
    "--concept",
    default=None,
    type=str,
    help='Process single concept (e.g., "water") instead of all',
)
@click.option(
    "--format",
    "format_choice",
    default="json",
    type=click.Choice(["json", "yaml"]),
    help="Output format",
)
@click.option("--verbose", is_flag=True, help="Print per-concept progress")
def generate(data_dir, output_dir, coverage_threshold, concept, format_choice, verbose):
    """Generate synthetic vocabulary from ASJP data."""
    # Validate coverage threshold
    if not 0.0 <= coverage_threshold <= 1.0:
        click.echo(
            f"Error: Coverage threshold must be between 0.0 and 1.0 (got {coverage_threshold})",
            err=True,
        )
        sys.exit(1)

    # Create output directories
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    graphs_path = output_path / "graphs"
    graphs_path.mkdir(exist_ok=True)

    if verbose:
        click.echo("=" * 60)
        click.echo("Pangloss Pipeline: Phonetic Convergence-Based Synthesis")
        click.echo("=" * 60)
        click.echo(f"Data directory: {data_dir}")
        click.echo(f"Output directory: {output_dir}")
        click.echo(f"Coverage threshold: {coverage_threshold:.1%}")
        click.echo(f"Output format: {format_choice}")
        if concept:
            click.echo(f"Single concept mode: {concept}")
        click.echo("=" * 60)

    # Step 1: Load ASJP data
    try:
        if verbose:
            click.echo("\n[1/3] Loading ASJP data...")
        asjp_data = load_asjp(data_dir)
        if verbose:
            click.echo(f"  ✓ Loaded {len(asjp_data)} concepts")
    except Exception as e:
        click.echo(f"Error loading ASJP data: {str(e)}", err=True)
        sys.exit(1)

    # Step 2: Load speaker counts
    try:
        if verbose:
            click.echo("\n[2/3] Loading speaker counts...")
        speaker_counts = load_speaker_counts()
        if verbose:
            click.echo(f"  ✓ Loaded {len(speaker_counts)} language population entries")
    except Exception as e:
        click.echo(f"Error loading speaker counts: {str(e)}", err=True)
        sys.exit(1)

    # Step 3: Build matrix
    try:
        if verbose:
            click.echo("\n[3/3] Building language-concept matrix...")
        matrix = build_matrix(asjp_data, speaker_counts)
        if verbose:
            click.echo(f"  ✓ Matrix built with {len(matrix)} concepts")
    except Exception as e:
        click.echo(f"Error building matrix: {str(e)}", err=True)
        sys.exit(1)

    # Filter to single concept if specified
    if concept:
        if concept not in matrix:
            click.echo(f"Error: Concept '{concept}' not found in ASJP data", err=True)
            click.echo(
                f"Available concepts: {', '.join(sorted(matrix.keys()))}", err=True
            )
            sys.exit(1)
        matrix = {concept: matrix[concept]}

    # Step 4: Process each concept
    if verbose:
        click.echo("\n" + "=" * 60)
        click.echo("Processing concepts...")
        click.echo("=" * 60)

    results: Dict[str, list] = {}
    failed_concepts = []

    for concept_name, concept_entry in matrix.items():
        try:
            # Build tries
            prefix_trie = build_prefix_trie(concept_entry.entries)
            suffix_trie = build_suffix_trie(concept_entry.entries)

            # Find convergence points (top 20)
            points = find_convergence_points(
                prefix_trie, suffix_trie, concept_entry.entries, k=20
            )

            # Generate candidate words from convergence points
            candidates = [
                generate_word(p, prefix_trie, suffix_trie, concept_entry.entries)
                for p in points
            ]

            # Select synonyms based on coverage threshold
            selected = select_synonyms(candidates, coverage_threshold)

            # Export graph JSON
            graph_path = graphs_path / f"{concept_name}.json"
            export_bowtie_graph(
                prefix_trie, suffix_trie, points, concept_name, graph_path
            )

            # Store results
            results[concept_name] = selected

            # Print progress if verbose
            if verbose:
                coverage = (
                    max([word.coverage_pct for word in selected]) if selected else 0.0
                )
                click.echo(
                    f"✓ {concept_name}: {len(selected)} synonyms, {coverage:.1f}% coverage"
                )

        except Exception as e:
            # Log error and continue with remaining concepts
            failed_concepts.append(concept_name)
            click.echo(f"✗ {concept_name}: FAILED - {str(e)}", err=True)
            continue

    # Check if all concepts failed
    if not results:
        click.echo("\nError: All concepts failed to process", err=True)
        sys.exit(1)

    # Step 5: Format and save dictionary
    if verbose:
        click.echo("\n" + "=" * 60)
        click.echo("Saving outputs...")
        click.echo("=" * 60)

    try:
        # Build matrix_entries for format_dictionary
        matrix_entries = {c: matrix[c].entries for c in results}

        dictionary = format_dictionary(results, matrix_entries=matrix_entries)
        dictionary_path = str(output_path / "dictionary.json")
        save_dictionary(dictionary, dictionary_path, format=format_choice)

        if verbose:
            click.echo(f"  ✓ Dictionary saved to {dictionary_path}")

    except Exception as e:
        click.echo(f"Error saving dictionary: {str(e)}", err=True)
        sys.exit(1)

    # Step 6: Format and save summary
    try:
        summary = format_summary(dictionary)
        summary_path = str(output_path / "summary.json")
        save_dictionary(summary, summary_path, format="json")

        if verbose:
            click.echo(f"  ✓ Summary saved to {summary_path}")
            click.echo(f"  ✓ {len(results)} graph files saved to {graphs_path}/")

    except Exception as e:
        click.echo(f"Error saving summary: {str(e)}", err=True)
        sys.exit(1)

    # Step 7: Print final stats
    click.echo(f"\n{'=' * 60}")
    click.echo(f"Pipeline complete: {len(results)}/{len(matrix)} concepts processed")
    if failed_concepts:
        click.echo(
            f"Failed concepts: {len(failed_concepts)} ({', '.join(failed_concepts[:5])}...)"
        )
    click.echo(f"Average coverage: {summary['avg_coverage_pct']:.1f}%")
    click.echo(f"Average synonyms per concept: {summary['avg_synonym_count']:.1f}")
    click.echo(f"Total unique languages: {summary['total_unique_languages']}")
    click.echo(f"Total unique families: {summary['total_unique_families']}")
    click.echo(f"Output written to: {output_path}/")
    click.echo(f"{'=' * 60}")


if __name__ == "__main__":
    cli()
