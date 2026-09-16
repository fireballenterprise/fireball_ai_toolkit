"""Backlog tooling — track bugs / features / tasks as GitHub Issues, one tracker per family repo.

Thin `gh` wrappers, no local state. Repo targeting resolves a fuzzy `--repo` token against
`properties.yml`'s `repos:` map; each issue gets the org-native GitHub issue Type
(`Bug` / `Feature` / `Task`) plus a matching label.
"""
