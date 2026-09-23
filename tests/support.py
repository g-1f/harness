"""Small fixtures shared by contract and adapter tests."""

from harness import NodeRequest, Resource, Skill


def skill(name, *, links=(), instructions=None):
    body = instructions or f"# {name}"
    body += "\n" + " ".join(f"[[{link}]]" for link in links)
    return Skill(name, f"Test {name}", body)


def code_skill(name, source):
    return Skill(
        name, f"Test {name}", f"# {name}", resources=(Resource("run.js", source.encode()),)
    )


def draft(value=1, **kwargs):
    return {"summary": "Test result", "content": {"value": value}, **kwargs}


def call(name="work", task="Do work", key="one", inputs=None, refs=()):
    return NodeRequest(name, task, inputs if inputs is not None else {"region": "US"}, key, refs)
