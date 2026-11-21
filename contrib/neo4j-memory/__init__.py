try:
    from .neo4j_memory import register
except ImportError:  # direct test collection loads this file without a package parent
    from neo4j_memory import register

__all__ = ["register"]
