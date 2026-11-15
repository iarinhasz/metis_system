"""Exemplo validado a partir do JSON Schema, compartilhado por prompts e fakes."""

from typing import Any

from pydantic import BaseModel


def schema_example[T: BaseModel](schema: type[T]) -> T:
    document = schema.model_json_schema()

    def generate(node: dict[str, Any], depth: int = 0) -> Any:
        if depth > 20:
            raise ValueError("Schema recursivo: forneça um exemplo explícito no campo.")
        if "examples" in node:
            return node["examples"][0]
        if "default" in node:
            return node["default"]
        if "const" in node:
            return node["const"]
        if "enum" in node:
            return node["enum"][0]
        if "$ref" in node:
            target: Any = document
            for part in node["$ref"].removeprefix("#/").split("/"):
                target = target[part]
            return generate(target, depth + 1)
        for alternatives in ("anyOf", "oneOf"):
            if alternatives in node:
                choice: dict[str, Any] = next(
                    (n for n in node[alternatives] if n.get("type") != "null"), {}
                )
                return generate(choice, depth + 1)
        kind = node.get("type")
        if kind == "object":
            return {
                key: generate(value, depth + 1)
                for key, value in node.get("properties", {}).items()
                if key in node.get("required", ())
            }
        if kind == "array":
            if "prefixItems" in node:
                return [generate(item, depth + 1) for item in node["prefixItems"]]
            minimum = max(1, node.get("minItems", 0))
            count = min(node.get("maxItems", minimum), minimum)
            return [generate(node.get("items", {}), depth + 1) for _ in range(count)]
        if kind == "string":
            value = "exemplo".ljust(node.get("minLength", 0), "x")
            return value[: node.get("maxLength", len(value))]
        if kind in {"number", "integer"}:
            value = max(node.get("minimum", 0), node.get("exclusiveMinimum", -1) + 1)
            return min(value, node.get("maximum", value))
        if kind == "boolean":
            return False
        return None

    try:
        return schema.model_validate(generate(document))
    except ValueError as exc:
        raise ValueError(
            f"Defina examples no schema {schema.__name__} para gerar um exemplo válido."
        ) from exc
