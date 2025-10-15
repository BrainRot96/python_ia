#!/usr/bin/env python3
"""
convert_format.py — Convertisseur JSON <-> YAML
-------------------------------------------------
Usage :
    python convert_format.py input.json
    python convert_format.py input.yaml

Le script détecte automatiquement le format
et crée le fichier converti dans le même dossier.
"""

import sys
import json
import yaml
from pathlib import Path


def convert_json_to_yaml(input_path: Path):
    """Convertit un fichier JSON vers YAML."""
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    output_path = input_path.with_suffix(".yaml")
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)

    print(f"✅ Converti en YAML : {output_path}")


def convert_yaml_to_json(input_path: Path):
    """Convertit un fichier YAML vers JSON."""
    with open(input_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    output_path = input_path.with_suffix(".json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Converti en JSON : {output_path}")


def main():
    if len(sys.argv) != 2:
        print("Usage : python convert_format.py <fichier.json|fichier.yaml>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print("❌ Fichier introuvable.")
        sys.exit(1)

    if input_path.suffix.lower() == ".json":
        convert_json_to_yaml(input_path)
    elif input_path.suffix.lower() in [".yaml", ".yml"]:
        convert_yaml_to_json(input_path)
    else:
        print("❌ Format non reconnu (attendu : .json ou .yaml).")


if __name__ == "__main__":
    main()