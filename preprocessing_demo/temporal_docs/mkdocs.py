from pathlib import Path

docs = [
    """# Project report 2022

This year we we decided to go to the moon""",
    """# Project report 2023

This year we built a rocket""",
    """# Project report 2024

This year we went to the moon""",
]

base_path = Path(__file__).parent
for i, doc in enumerate(docs):
    doc_path = base_path / f"doc_{i}.md"
    with open(doc_path, "w") as f:
        f.write(doc)
