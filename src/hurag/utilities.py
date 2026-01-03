def dict_to_namespace(data):
    """
    Recursively converts a dictionary (and nested dicts/lists of dicts)
    into a types.SimpleNamespace object.
    """
    from types import SimpleNamespace

    if isinstance(data, dict):
        # Convert dictionary items recursively
        return SimpleNamespace(
            **{key: dict_to_namespace(value) for key, value in data.items()}
        )

    elif isinstance(data, list):
        # Convert list items if they are dictionaries
        return [dict_to_namespace(item) for item in data]

    else:
        # Return all other types (strings, integers, etc.) unchanged
        return data

def generate_id() -> str:
    from uuid6 import uuid7

    return str(uuid7())

def merge_num_fields(fields: list[float]) -> float:
    return sum(fields)

def merge_set_fields(fields: list[str], sep: str) -> str:
    return sep.join(
        sorted(set([it for sl in [f.split(sep) for f in fields] for it in sl]))
    )

def split_string_by_markers(content: str, markers: list[str]) -> list[str]:
    """Split a string by multiple markers"""
    import re

    if not markers:
        return [content]
    content = content if content is not None else ""
    results = re.split("|".join(re.escape(mk) for mk in markers), content)
    return [r.strip() for r in results if r.strip()]

def is_float(s: str) -> bool:
    import re
    return bool(re.match(r"^[-+]?[0-9]*\.?[0-9]+$", s))

def clean_str(s: str) -> str:
    import re
    import html
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", "", html.unescape(s.strip()))
    
def normalize_extracted_info(name: str, is_entity=False) -> str:
    """
    Normalize entity/relation names and description with the following rules:
    1. Remove spaces between Chinese characters
    2. Remove spaces between Chinese characters and English letters/numbers
    3. Preserve spaces within English text and numbers
    4. Replace Chinese parentheses with English parentheses
    5. Replace Chinese dash with English dash
    6. Remove English quotation marks from the beginning and end of the text
    7. Remove English quotation marks in and around chinese
    8. Remove Chinese quotation marks

    Args:
        name: Entity name to normalize

    Returns:
        Normalized entity name
    """
    import re
    # Replace Chinese parentheses with English parentheses
    name = name.replace("（", "(").replace("）", ")")

    # Replace Chinese dash with English dash
    name = name.replace("—", "-").replace("－", "-")

    # Use regex to remove spaces between Chinese characters
    # Regex explanation:
    # (?<=[\u4e00-\u9fa5]): Positive lookbehind for Chinese character
    # \s+: One or more whitespace characters
    # (?=[\u4e00-\u9fa5]): Positive lookahead for Chinese character
    name = re.sub(r"(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])", "", name)

    # Remove spaces between Chinese and English/numbers/symbols
    name = re.sub(
        r"(?<=[\u4e00-\u9fa5])\s+(?=[a-zA-Z0-9\(\)\[\]@#$%!&\*\-=+_])",
        "",
        name
    )
    name = re.sub(
        r"(?<=[a-zA-Z0-9\(\)\[\]@#$%!&\*\-=+_])\s+(?=[\u4e00-\u9fa5])",
        "",
        name
    )

    # Remove English quotation marks from the beginning and end
    if len(name) >= 2 and name.startswith('"') and name.endswith('"'):
        name = name[1:-1]
    if len(name) >= 2 and name.startswith("'") and name.endswith("'"):
        name = name[1:-1]

    if is_entity:
        # remove Chinese quotes and English quotes
        name = (name.replace("“", "")
                    .replace("”", "")
                    .replace("‘", "")
                    .replace("’", "")
                    .replace('"', "")
                    .replace("'", ""))
        # remove English queotes in and around chinese
        # name = re.sub(r"['\"]+(?=[\u4e00-\u9fa5])", "", name)
        # name = re.sub(r"(?<=[\u4e00-\u9fa5])['\"]+", "", name)

    return name

def str2int(inp: str) -> list[int]:
    sp = inp.split("-")
    if len(sp) == 1:
        return [int(inp)]
    elif len(sp) == 2:
        st = int(sp[0])
        ed = int(sp[1]) + 1
        return list(range(st, ed))
    else:
        raise ValueError("invalid input")

