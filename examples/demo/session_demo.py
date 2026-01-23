"""Demo script for session continuity feature.

This script has multiple stages, ideal for demonstrating
that debug sessions persist across multiple LLM interactions.
"""


def stage_one():
    """First stage - initialization."""
    config = {"mode": "debug", "level": 1}
    print(f"Stage 1: Initialized with {config}")
    return config


def stage_two(config):
    """Second stage - processing."""
    config["level"] = 2
    config["processed"] = True
    print(f"Stage 2: Processing complete, {config}")
    return config


def stage_three(config):
    """Third stage - finalization."""
    config["level"] = 3
    config["finalized"] = True
    result = sum(config["level"] for _ in range(3))
    print(f"Stage 3: Finalized with result={result}")
    return result


def main():
    """Run through all stages - perfect for multi-turn debugging."""
    print("Starting multi-stage process...")

    # Stage 1 - first breakpoint here
    cfg = stage_one()

    # Stage 2 - continue to here in second interaction
    cfg = stage_two(cfg)

    # Stage 3 - continue to here in third interaction
    result = stage_three(cfg)

    print(f"All stages complete! Result: {result}")
    return result


if __name__ == "__main__":
    main()
